"""Isolated standard-library HTTPS downloads with a local manifest trust anchor."""

import errno
import hashlib
import json
import os
import re
import shutil
import ssl
import stat
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any, cast

HOSTS = frozenset({"github.com", "release-assets.githubusercontent.com"})
CHUNK = 64 * 1024


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


@contextmanager
def download_lock(path: Path):
    """OS-released lock survives cancellation without a stale PID lock protocol."""
    if linked(path):
        raise FetchError(Exit.IO)
    with path.open("a+b") as handle:
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
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            CheckedRedirect(self.policy),
            urllib.request.HTTPSHandler(context=context or ssl.create_default_context()),
        )

    def verify(self, asset: Asset, destination: Path) -> None:
        if not matches(destination / asset.file_name, asset):
            raise FetchError(Exit.MISMATCH)

    def download(
        self,
        asset: Asset,
        destination: Path,
        emit: Callable[[dict[str, Any]], None],
        cancelled: Callable[[], bool] = lambda: False,
    ) -> None:
        self.policy.validate(asset.url)
        if linked(destination):
            raise FetchError(Exit.IO)
        destination.mkdir(parents=True, exist_ok=True)
        final = destination / asset.file_name
        part = destination / (asset.file_name + ".part")
        if linked(final) or linked(part):
            raise FetchError(Exit.IO)
        with download_lock(destination / (asset.file_name + ".lock")):
            try:
                if matches(final, asset):
                    emit(
                        {
                            "event": "complete",
                            "bytes": asset.size,
                            "total": asset.size,
                            "cached": True,
                        }
                    )
                    return
                offset = part.stat().st_size if part.exists() else 0
                if offset > asset.size:
                    part.unlink()
                    raise FetchError(Exit.MISMATCH)
                if offset < asset.size:
                    self._transfer(asset, part, offset, emit, cancelled)
                if cancelled():
                    raise FetchError(Exit.CANCELLED)
                emit({"event": "verifying", "bytes": asset.size, "total": asset.size})
                if not matches(part, asset):
                    part.unlink(missing_ok=True)
                    raise FetchError(Exit.MISMATCH)
                if cancelled():
                    raise FetchError(Exit.CANCELLED)
                os.replace(part, final)
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
        headers = {"Accept-Encoding": "identity", "User-Agent": "dusty-fetch/0.0.1"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        request = urllib.request.Request(self.policy.validate(asset.url), headers=headers)
        with self.opener.open(request, timeout=30) as response:
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
            with part.open("r+b" if part.exists() else "x+b") as stream:
                stream.seek(offset)
                stream.truncate()
                while True:
                    if cancelled():
                        raise FetchError(Exit.CANCELLED)
                    chunk = response.read(CHUNK)
                    if not chunk:
                        break
                    if stream.tell() + len(chunk) > asset.size:
                        stream.close()
                        part.unlink(missing_ok=True)
                        raise FetchError(Exit.MISMATCH)
                    stream.write(chunk)
                    emit({"event": "downloading", "bytes": stream.tell(), "total": asset.size})
                stream.flush()
                os.fsync(stream.fileno())
                if stream.tell() != asset.size:
                    raise FetchError(Exit.NETWORK)


def io_error(exc: OSError) -> Exit:
    return (
        Exit.DISK_FULL
        if exc.errno == errno.ENOSPC or getattr(exc, "winerror", None) == 112
        else Exit.IO
    )
