"""Isolated standard-library HTTPS downloads with a local manifest trust anchor."""

import errno
import hashlib
import http.client
import json
import os
import re
import shutil
import socket
import ssl
import stat
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any, cast

from .tls import create_context

HOSTS = frozenset({"github.com", "release-assets.githubusercontent.com"})
CHUNK = 64 * 1024
SOCKET_TIMEOUT = 30
MAX_ATTEMPTS = 2
RETRY_DELAY = 1.0
LOCAL_RETRY_SECONDS = 30.0
LOCAL_RETRY_DELAY = 0.25


class Exit(IntEnum):
    OK = 0
    INVALID = 2
    BLOCKED = 3
    MISMATCH = 4
    DISK_FULL = 5
    NETWORK = 6
    IO = 7
    BUSY = 8
    CANCELLED = 130


class FetchError(Exception):
    def __init__(self, code: Exit):
        self.code = code
        super().__init__(code.name)


class TransientTransferError(ConnectionError):
    """A response ended early, leaving a resumable partial file."""


def transient_connection_error(exc: BaseException) -> bool:
    """Retry transport interruption only, never trust or policy failures."""
    if isinstance(exc, TransientTransferError):
        return True
    if isinstance(exc, ssl.SSLError | urllib.error.HTTPError):
        return False
    if isinstance(exc, urllib.error.URLError):
        return isinstance(exc.reason, BaseException) and transient_connection_error(exc.reason)
    if isinstance(exc, socket.gaierror):
        code = exc.errno if exc.errno is not None else exc.args[0] if exc.args else None
        return code == socket.EAI_AGAIN
    if isinstance(exc, TimeoutError | ConnectionResetError | ConnectionAbortedError):
        return True
    if isinstance(exc, http.client.IncompleteRead):
        return True
    return isinstance(exc, OSError) and exc.errno in {
        errno.ETIMEDOUT,
        errno.ECONNRESET,
        errno.ECONNABORTED,
    }


def temporary_file_access(exc: OSError) -> bool:
    """Windows scanners can expose sharing failures as EACCES without winerror."""
    winerror = getattr(exc, "winerror", None)
    return winerror in {5, 32, 33} or (
        os.name == "nt" and winerror is None and exc.errno == errno.EACCES
    )


@dataclass
class LocalRetryBudget:
    deadline: float | None = None


def retry_local_file[T](
    operation: Callable[[], T],
    cancelled: Callable[[], bool] = lambda: False,
    budget: LocalRetryBudget | None = None,
) -> T:
    """Share one 30-second window starting at the first local access failure."""
    budget = budget if budget is not None else LocalRetryBudget()
    while True:
        if cancelled():
            raise FetchError(Exit.CANCELLED)
        try:
            return operation()
        except OSError as exc:
            if not temporary_file_access(exc):
                raise
            now = time.monotonic()
            if budget.deadline is None:
                budget.deadline = now + LOCAL_RETRY_SECONDS
            if now >= budget.deadline:
                raise
            time.sleep(min(LOCAL_RETRY_DELAY, budget.deadline - now))


@dataclass(frozen=True)
class HostPolicy:
    hosts: frozenset[str] = HOSTS
    port: int = 443

    def validate(self, url: str) -> str:
        try:
            if any(ord(char) <= 32 or ord(char) == 127 for char in url):
                raise ValueError
            parsed = urllib.parse.urlsplit(url)
            if (
                parsed.scheme != "https"
                or parsed.hostname not in self.hosts
                or parsed.username is not None
                or parsed.password is not None
                or parsed.fragment
                or (parsed.port if parsed.port is not None else 443) != self.port
            ):
                raise ValueError
        except ValueError as exc:
            raise FetchError(Exit.BLOCKED) from exc
        return url


class CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, policy: HostPolicy):
        self.policy = policy

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.policy.validate(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@dataclass(frozen=True)
class Asset:
    id: str
    file_name: str
    url: str
    size: int
    sha256: str


def load_asset(manifest: Path, model_id: str, policy: HostPolicy) -> Asset:
    """Read the caller-supplied bundled manifest; never fetch a remote manifest."""
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if data["schema_version"] != 1:
            raise ValueError
        entries = data["models"] + data.get("vad", [])
        found = [entry for entry in entries if entry["id"] == model_id]
        if len(found) != 1:
            raise ValueError
        entry = found[0]
        name, size, digest, url = (
            entry[key] for key in ("file_name", "size_bytes", "sha256", "url")
        )
        if (
            not re.fullmatch(r"[a-z0-9][a-z0-9._+-]{0,63}", model_id)
            or not isinstance(name, str)
            or not re.fullmatch(r"ggml-[A-Za-z0-9._-]+\.bin", name)
            or type(size) is not int
            or not 0 < size < 2**31
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or not isinstance(url, str)
        ):
            raise ValueError
        policy.validate(url)
        return Asset(model_id, name, url, size, digest)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise FetchError(Exit.INVALID) from exc


def linked(path: Path) -> bool:
    """Reject all reparse-point ancestors before reading, writing or removing."""
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            return True
    return False


def matches(path: Path, asset: Asset) -> bool:
    if linked(path):
        raise FetchError(Exit.IO)
    if not path.is_file() or path.stat().st_size != asset.size:
        return False
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest() == asset.sha256


def record_partial(path: Path) -> None:
    """Retain a hash receipt for age-based cleanup of a completed transfer attempt."""
    if linked(path) or not path.is_file():
        return
    lock = path.with_name(path.name.removesuffix(".part") + ".lock")
    if linked(lock):
        return
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    receipt = {"schema": 1, "purpose": "model-download", "file": path.name, "sha256": digest}
    # Byte zero remains the OS locking byte. Updating the receipt does not unlock.
    with lock.open("r+b" if lock.exists() else "w+b") as stream:
        stream.seek(1)
        stream.write(json.dumps(receipt).encode("ascii"))
        stream.truncate()


@contextmanager
def download_lock(
    path: Path,
    cancelled: Callable[[], bool] = lambda: False,
    budget: LocalRetryBudget | None = None,
):
    """OS-released lock survives cancellation without a stale PID lock protocol."""
    if linked(path):
        raise FetchError(Exit.IO)
    with retry_local_file(lambda: path.open("a+b"), cancelled, budget) as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                cast(Any, fcntl).flock(
                    handle.fileno(), cast(Any, fcntl).LOCK_EX | cast(Any, fcntl).LOCK_NB
                )
        except OSError as exc:
            raise FetchError(Exit.BUSY) from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                cast(Any, fcntl).flock(handle.fileno(), cast(Any, fcntl).LOCK_UN)


class Downloader:
    def __init__(self, *, policy: HostPolicy | None = None, context: ssl.SSLContext | None = None):
        # Injection is for library tests only; the CLI has no host/TLS override.
        self.policy = policy or HostPolicy()
        self.context = context or create_context()
        self.step = "next_file"
        self.local_retry_budget = LocalRetryBudget()

    def _local[T](self, step: str, operation: Callable[[], T], cancelled: Callable[[], bool]) -> T:
        self.step = step
        return retry_local_file(operation, cancelled, self.local_retry_budget)

    @contextmanager
    def _part_stream(self, part: Path, cancelled: Callable[[], bool]):
        stream = self._local(
            "transfer", lambda: part.open("r+b" if part.exists() else "x+b"), cancelled
        )
        try:
            yield stream
        finally:
            preceding_step = self.step
            self._local("finalize", stream.close, lambda: False)
            self.step = preceding_step

    def _opener(self):
        # New opener, connection and original GitHub URL for every attempt/file.
        return urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            CheckedRedirect(self.policy),
            urllib.request.HTTPSHandler(context=self.context),
        )

    def verify(self, asset: Asset, destination: Path) -> None:
        self.local_retry_budget = LocalRetryBudget()
        if not self._local(
            "verify", lambda: matches(destination / asset.file_name, asset), lambda: False
        ):
            raise FetchError(Exit.MISMATCH)

    def download(
        self,
        asset: Asset,
        destination: Path,
        emit: Callable[[dict[str, Any]], None],
        cancelled: Callable[[], bool] = lambda: False,
        retry_state: Callable[[bool], None] = lambda _: None,
    ) -> None:
        self.step = "next_file"
        self.local_retry_budget = LocalRetryBudget()
        self.policy.validate(asset.url)
        if self._local("next_file", lambda: linked(destination), cancelled):
            raise FetchError(Exit.IO)
        self._local("next_file", lambda: destination.mkdir(parents=True, exist_ok=True), cancelled)
        final = destination / asset.file_name
        part = destination / (asset.file_name + ".part")
        if self._local("next_file", lambda: linked(final) or linked(part), cancelled):
            raise FetchError(Exit.IO)
        with download_lock(
            destination / (asset.file_name + ".lock"), cancelled, self.local_retry_budget
        ):
            try:
                if self._local("next_file", lambda: matches(final, asset), cancelled):
                    emit(
                        {
                            "event": "complete",
                            "bytes": asset.size,
                            "total": asset.size,
                            "cached": True,
                        }
                    )
                    return
                offset = self._local(
                    "next_file", lambda: part.stat().st_size if part.exists() else 0, cancelled
                )
                if offset > asset.size:
                    part.unlink()
                    raise FetchError(Exit.MISMATCH)
                if offset < asset.size:
                    for attempt in range(1, MAX_ATTEMPTS + 1):
                        offset = self._local(
                            "finalize",
                            lambda: part.stat().st_size if part.exists() else 0,
                            cancelled,
                        )
                        if offset == asset.size:
                            break
                        try:
                            self._transfer(asset, part, offset, emit, cancelled)
                            break
                        except (OSError, http.client.HTTPException) as exc:
                            if attempt == MAX_ATTEMPTS or not transient_connection_error(exc):
                                raise
                            emit({"event": "retrying", "attempt": attempt + 1})
                            retry_state(True)
                            try:
                                until = time.monotonic() + RETRY_DELAY
                                while time.monotonic() < until:
                                    if cancelled():
                                        raise FetchError(Exit.CANCELLED) from exc
                                    time.sleep(min(0.05, until - time.monotonic()))
                            finally:
                                retry_state(False)
                        finally:
                            previous_step = self.step
                            self._local("finalize", lambda: record_partial(part), cancelled)
                            self.step = previous_step
                if cancelled():
                    raise FetchError(Exit.CANCELLED)
                emit({"event": "verifying", "bytes": asset.size, "total": asset.size})
                if not self._local("verify", lambda: matches(part, asset), cancelled):
                    part.unlink(missing_ok=True)
                    raise FetchError(Exit.MISMATCH)
                if cancelled():
                    raise FetchError(Exit.CANCELLED)
                self._local("rename", lambda: os.replace(part, final), cancelled)
                emit(
                    {"event": "complete", "bytes": asset.size, "total": asset.size, "cached": False}
                )
            except (KeyboardInterrupt, BrokenPipeError):
                part.unlink(missing_ok=True)
                raise
            except FetchError as exc:
                if exc.code == Exit.CANCELLED:
                    part.unlink(missing_ok=True)
                raise

    def _space(self, destination: Path, required: int) -> None:
        if shutil.disk_usage(destination).free < required + 1024 * 1024:
            raise FetchError(Exit.DISK_FULL)

    def _transfer(
        self,
        asset: Asset,
        part: Path,
        offset: int,
        emit: Callable[[dict[str, Any]], None],
        cancelled: Callable[[], bool],
    ) -> None:
        self._space(part.parent, asset.size - offset)
        if cancelled():
            raise FetchError(Exit.CANCELLED)
        headers = {"Accept-Encoding": "identity", "User-Agent": "dusty-fetch"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        request = urllib.request.Request(self.policy.validate(asset.url), headers=headers)
        self.step = "connect"
        with self._opener().open(request, timeout=SOCKET_TIMEOUT) as response:
            self.policy.validate(response.url)
            if response.status == 200:
                if offset:
                    self._space(part.parent, asset.size)
                offset = 0  # A server may ignore Range. Restart; never append a full response.
            elif response.status == 206:
                expected = f"bytes {offset}-{asset.size - 1}/{asset.size}"
                if response.headers.get("Content-Range") != expected:
                    raise FetchError(Exit.NETWORK)
            else:
                raise FetchError(Exit.NETWORK)
            length = response.headers.get("Content-Length")
            if length is not None and length != str(asset.size - offset):
                raise FetchError(Exit.NETWORK)
            emit({"event": "downloading", "bytes": offset, "total": asset.size})
            self.step = "transfer"
            with self._part_stream(part, cancelled) as stream:
                stream.seek(offset)
                stream.truncate()
                while True:
                    if cancelled():
                        raise FetchError(Exit.CANCELLED)
                    chunk = response.read(CHUNK)
                    if not chunk:
                        break
                    if stream.tell() + len(chunk) > asset.size:
                        self._local("finalize", stream.close, cancelled)
                        part.unlink(missing_ok=True)
                        raise FetchError(Exit.MISMATCH)
                    stream.write(chunk)
                    emit({"event": "downloading", "bytes": stream.tell(), "total": asset.size})
                self.step = "finalize"
                self._local("finalize", stream.flush, cancelled)
                self._local("finalize", lambda: os.fsync(stream.fileno()), cancelled)
                if stream.tell() != asset.size:
                    self.step = "transfer"
                    raise TransientTransferError("Incomplete response")


def io_error(exc: OSError) -> Exit:
    return (
        Exit.DISK_FULL
        if exc.errno == errno.ENOSPC or getattr(exc, "winerror", None) == 112
        else Exit.IO
    )
