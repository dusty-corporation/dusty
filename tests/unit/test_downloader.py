"""Local TLS regression tests; no external network and no system trust changes."""

import hashlib
import json
import os
import socket
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

from dusty_fetch.__main__ import main
from dusty_fetch.downloader import (
    CHUNK,
    MAX_ATTEMPTS,
    SOCKET_TIMEOUT,
    Downloader,
    Exit,
    FetchError,
    HostPolicy,
    LocalRetryBudget,
    download_lock,
    load_asset,
    matches,
    retry_local_file,
    transient_connection_error,
)

CERTS = Path(__file__).resolve().parents[1] / "fixtures/https"
DATA = bytes(range(256)) * 2048


def test_local_access_retry_is_bounded_and_rejects_other_errors(monkeypatch):
    from dusty_fetch import downloader

    clock = [0.0]
    monkeypatch.setattr(downloader.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        downloader.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds)
    )
    attempts = []

    def busy():
        attempts.append(clock[0])
        error = PermissionError(13, "redacted test message")
        error.winerror = 32
        raise error

    with pytest.raises(PermissionError):
        retry_local_file(busy)
    assert clock[0] == 30.0
    assert len(attempts) > 1
    clock[0] = 0
    attempts.clear()

    def disk_full():
        attempts.append(clock[0])
        raise OSError(28, "redacted test message")

    with pytest.raises(OSError):
        retry_local_file(disk_full)
    assert attempts == [0]


def test_local_retry_window_is_shared_across_operations(monkeypatch):
    from dusty_fetch import downloader

    clock = [0.0]
    monkeypatch.setattr(downloader.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        downloader.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds)
    )
    budget = LocalRetryBudget()

    def access_error():
        error = PermissionError(13, "redacted test message")
        error.winerror = 32
        return error

    def first_operation():
        if clock[0] < 10:
            raise access_error()
        return "complete"

    assert retry_local_file(first_operation, budget=budget) == "complete"

    def second_operation():
        raise access_error()

    with pytest.raises(PermissionError):
        retry_local_file(second_operation, budget=budget)
    assert clock[0] == 30.0


def hold_exclusive(path: Path, seconds: float = 1.5) -> subprocess.Popen[str]:
    """A separate Windows process denies file sharing until its timer expires."""
    program = """
import ctypes, sys, time
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                               ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                               ctypes.c_void_p]
kernel.CreateFileW.restype = ctypes.c_void_p
handle = kernel.CreateFileW(sys.argv[1], 0x80000000, 0, None, 3, 0, None)
if handle == ctypes.c_void_p(-1).value:
    raise OSError(ctypes.get_last_error())
print('locked', flush=True)
time.sleep(float(sys.argv[2]))
kernel.CloseHandle(ctypes.c_void_p(handle))
"""
    child = subprocess.Popen(
        [sys.executable, "-c", program, str(path), str(seconds)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert child.stdout is not None
    assert child.stdout.readline().strip() == "locked"
    return child


@pytest.mark.skipif(os.name != "nt", reason="Windows sharing semantics")
def test_completed_part_recovers_when_antivirus_holds_hash_open(tls):
    tls.dest.mkdir()
    part = tls.dest / (tls.asset.file_name + ".part")
    part.write_bytes(DATA)
    holder = hold_exclusive(part)
    try:
        tls.client.download(tls.asset, tls.dest, lambda event: None)
    finally:
        assert holder.wait(timeout=5) == 0
    assert (tls.dest / tls.asset.file_name).read_bytes() == DATA
    assert tls.requests == []


@pytest.mark.skipif(os.name != "nt", reason="Windows sharing semantics")
def test_completed_part_recovers_when_antivirus_holds_rename(tls, monkeypatch):
    tls.dest.mkdir()
    part = tls.dest / (tls.asset.file_name + ".part")
    part.write_bytes(DATA)
    original = os.replace
    holder = None

    def blocked_rename(source, target):
        nonlocal holder
        if Path(source) == part and holder is None:
            holder = hold_exclusive(part)
        return original(source, target)

    monkeypatch.setattr("dusty_fetch.downloader.os.replace", blocked_rename)
    try:
        tls.client.download(tls.asset, tls.dest, lambda event: None)
    finally:
        if holder is not None:
            assert holder.wait(timeout=5) == 0
    assert holder is not None
    assert (tls.dest / tls.asset.file_name).read_bytes() == DATA
    assert tls.requests == []


@pytest.mark.skipif(os.name != "nt", reason="Windows sharing semantics")
def test_next_file_start_waits_for_exclusive_lock_file(tls):
    tls.dest.mkdir()
    lock = tls.dest / (tls.asset.file_name + ".lock")
    lock.write_bytes(b"0")
    holder = hold_exclusive(lock)
    try:
        tls.client.download(tls.asset, tls.dest, lambda event: None)
    finally:
        assert holder.wait(timeout=5) == 0
    assert (tls.dest / tls.asset.file_name).read_bytes() == DATA


@pytest.mark.skipif(os.name != "nt", reason="Windows sharing semantics")
def test_receipt_hash_waits_for_exclusive_completed_part(tls, monkeypatch):
    from dusty_fetch import downloader

    original = downloader.record_partial
    holder = None

    def held_receipt(part):
        nonlocal holder
        if holder is None:
            holder = hold_exclusive(part)
        return original(part)

    monkeypatch.setattr(downloader, "record_partial", held_receipt)
    try:
        tls.client.download(tls.asset, tls.dest, lambda event: None)
    finally:
        if holder is not None:
            assert holder.wait(timeout=5) == 0
    assert holder is not None
    assert (tls.dest / tls.asset.file_name).read_bytes() == DATA


def test_part_close_retries_a_temporary_sharing_error(tls, monkeypatch):
    original = Path.open
    errors = []

    class BusyClose:
        def __init__(self, stream):
            self.stream = stream
            self.first = True

        def __getattr__(self, name):
            return getattr(self.stream, name)

        def close(self):
            if self.first:
                self.first = False
                errors.append("sharing")
                raise PermissionError(13, "Synthetic sharing violation", None, 32)
            self.stream.close()

    def open_part(path, mode="r", *args, **kwargs):
        stream = original(path, mode, *args, **kwargs)
        if path.name.endswith(".part") and mode in {"x+b", "r+b"}:
            return BusyClose(stream)
        return stream

    monkeypatch.setattr(Path, "open", open_part)
    tls.client.download(tls.asset, tls.dest, lambda event: None)
    assert errors == ["sharing"]
    assert (tls.dest / tls.asset.file_name).read_bytes() == DATA


def test_tls_identity_is_temporary_and_regenerated(tmp_path, tls_certificate):
    assert tls_certificate.cert.is_relative_to(tmp_path.parent)
    assert tls_certificate.key.is_relative_to(tmp_path.parent)
    assert not (CERTS / tls_certificate.cert.name).exists()
    assert not (CERTS / tls_certificate.key.name).exists()
    subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(CERTS / "generate.ps1"),
            "-Destination",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    assert (tmp_path / tls_certificate.cert.name).read_bytes() != tls_certificate.cert.read_bytes()
    assert (tmp_path / tls_certificate.key.name).read_bytes() != tls_certificate.key.read_bytes()
    context = ssl.create_default_context(cafile=str(tls_certificate.cert))
    identity = context.get_ca_certs()[0]
    assert ("DNS", "localhost") in identity["subjectAltName"]
    assert ("IP Address", "127.0.0.1") in identity["subjectAltName"]


@pytest.fixture
def tls(tmp_path, monkeypatch, tls_certificate):
    real_dns = socket.getaddrinfo

    def loopback_only(host, *args, **kwargs):
        assert host in {"localhost", "127.0.0.1", "::1"}, "Unit test attempted external DNS"
        return real_dns(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", loopback_only)
    state = SimpleNamespace(
        mode="normal",
        requests=[],
        interrupted=False,
        release=threading.Event(),
        waiting=threading.Event(),
        finished=threading.Event(),
        certificate=tls_certificate.cert,
        paths=[],
        tokens=0,
    )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            state.requests.append(self.headers.get("Range"))
            state.paths.append(self.path)
            if state.mode == "fresh_redirect" and self.path == "/asset":
                state.tokens += 1
                self.send_response(302)
                self.send_header("Location", f"/signed?token={state.tokens}")
                self.end_headers()
                return
            if state.mode == "fresh_redirect" and self.path.startswith("/signed"):
                if self.path != f"/signed?token={state.tokens}":
                    self.send_error(403)
                    return
            if state.mode == "redirect":
                self.send_response(302)
                self.send_header("Location", "https://not-allowed.invalid/file")
                self.end_headers()
                return
            if state.mode == "local_redirect" and self.path == "/asset":
                self.send_response(302)
                self.send_header("Location", "/actual")
                self.end_headers()
                return
            offset = int(self.headers.get("Range", "bytes=0-")[6:-1])
            partial = bool(self.headers.get("Range")) and state.mode != "ignore_range"
            if not partial:
                offset = 0
            self.send_response(206 if partial else 200)
            self.send_header("Content-Length", str(len(DATA) - offset))
            if partial:
                start = offset + 1 if state.mode == "bad_range" else offset
                self.send_header("Content-Range", f"bytes {start}-{len(DATA) - 1}/{len(DATA)}")
            self.end_headers()
            content = DATA[offset:]
            if state.mode == "interrupt_always" or (
                state.mode in {"interrupt", "drop_once"} and not state.interrupted
            ):
                state.interrupted = True
                content = content[: len(content) // 2]
            try:
                for start in range(0, len(content), CHUNK):
                    if state.mode == "hold" and start == 2 * CHUNK:
                        state.waiting.set()
                        state.release.wait(timeout=30)
                    self.wfile.write(content[start : start + CHUNK])
                    self.wfile.flush()
                    if state.mode == "slow":
                        time.sleep(0.08)
            except (BrokenPipeError, ConnectionResetError, ssl.SSLError):
                pass
            finally:
                state.finished.set()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(tls_certificate.cert, tls_certificate.key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    state.port = server.server_port
    state.url = f"https://localhost:{state.port}/asset"
    state.client = Downloader(
        policy=HostPolicy(frozenset({"localhost"}), state.port),
        context=ssl.create_default_context(cafile=str(tls_certificate.cert)),
    )
    entry = {
        "id": "tiny",
        "file_name": "ggml-test.bin",
        "url": state.url,
        "size_bytes": len(DATA),
        "sha256": hashlib.sha256(DATA).hexdigest(),
    }
    state.manifest = tmp_path / "manifest.json"
    state.manifest.write_text(
        json.dumps({"schema_version": 1, "models": [entry]}), encoding="utf-8"
    )
    state.asset = load_asset(state.manifest, "tiny", state.client.policy)
    state.dest = tmp_path / "downloads"
    yield state
    state.release.set()
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def args(tls, command="download"):
    return [command, "--id", "tiny", "--dest", str(tls.dest), "--manifest", str(tls.manifest)]


def test_success_verify_json_and_cached_reuse(tls, capsys):
    assert main(args(tls), client=tls.client) == Exit.OK
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert events[-1]["event"] == "complete"
    assert [event["bytes"] for event in events] == sorted(event["bytes"] for event in events)
    assert (tls.dest / tls.asset.file_name).read_bytes() == DATA
    assert not list(tls.dest.glob("*.part"))
    assert main(args(tls, "verify"), client=tls.client) == Exit.OK
    assert main(args(tls), client=tls.client) == Exit.OK
    assert len(tls.requests) == 1
    assert str(tls.dest) not in capsys.readouterr().out


def test_resume_after_interrupted_connection(tls):
    tls.mode = "interrupt_always"
    assert main(args(tls), client=tls.client) == Exit.NETWORK
    part = tls.dest / (tls.asset.file_name + ".part")
    offset = part.stat().st_size
    assert 0 < offset < len(DATA)
    assert not (tls.dest / tls.asset.file_name).exists()
    assert len(tls.requests) == 2
    tls.mode = "normal"
    assert main(args(tls), client=tls.client) == Exit.OK
    assert tls.requests == [None, f"bytes={len(DATA) // 2}-", f"bytes={offset}-"]
    assert (tls.dest / tls.asset.file_name).read_bytes() == DATA


def test_one_transient_drop_retries_with_range_and_validates_hash(tls, capsys):
    tls.mode = "drop_once"
    assert main(args(tls), client=tls.client) == Exit.OK
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [event["event"] for event in events].count("retrying") == 1
    assert tls.requests[0] is None
    assert tls.requests[1].startswith("bytes=")
    assert (tls.dest / tls.asset.file_name).read_bytes() == DATA


def test_retry_status_file_exists_only_during_backoff(tls, monkeypatch):
    from dusty_fetch import downloader

    tls.mode = "drop_once"
    marker = tls.dest.parent / "retry-status"
    states = []
    real_sleep = time.sleep

    def observe_sleep(seconds):
        states.append(marker.read_bytes())
        real_sleep(seconds)

    monkeypatch.setattr(downloader.time, "sleep", observe_sleep)
    argv = args(tls) + ["--retry-status", str(marker)]
    assert main(argv, client=tls.client) == Exit.OK
    assert states and all(state == b"1" for state in states)
    assert not marker.exists()


def test_transient_classifier_and_socket_timeout():
    assert transient_connection_error(TimeoutError())
    assert transient_connection_error(ConnectionResetError())
    assert transient_connection_error(urllib.error.URLError(socket.gaierror(socket.EAI_AGAIN)))
    assert not transient_connection_error(urllib.error.URLError(socket.gaierror(socket.EAI_NONAME)))
    assert not transient_connection_error(ssl.SSLError())
    assert not transient_connection_error(urllib.error.HTTPError("", 403, "", {}, None))
    assert SOCKET_TIMEOUT == 30
    assert MAX_ATTEMPTS == 2


@pytest.mark.parametrize("mode", ["normal", "drop_once"])
def test_steady_transfer_past_old_wall_clock_cap_completes(tls, monkeypatch, mode):
    from dusty_fetch import downloader

    tls.mode = mode
    clock = [0.0]
    events = []
    monkeypatch.setattr(downloader.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        downloader.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds)
    )

    def progress(event):
        events.append(event)
        if event["event"] == "downloading" and event["bytes"]:
            clock[0] += 3600

    tls.client.download(tls.asset, tls.dest, progress)
    assert clock[0] > 7200
    assert (tls.dest / tls.asset.file_name).read_bytes() == DATA
    assert len(tls.requests) == (2 if mode == "drop_once" else 1)
    assert sum(event["event"] == "retrying" for event in events) == (mode == "drop_once")


def test_matches_propagates_oserror_without_removing_part(tls, monkeypatch):
    tls.dest.mkdir()
    part = tls.dest / (tls.asset.file_name + ".part")
    part.write_bytes(DATA)
    original = Path.open

    def held(path, *args, **kwargs):
        if path == part:
            raise PermissionError(13, "Synthetic access failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", held)
    with pytest.raises(PermissionError):
        matches(part, tls.asset)
    assert part.exists()


def test_new_file_uses_fresh_connection_after_idle_close(tls):
    from dataclasses import replace

    events = []
    tls.client.download(tls.asset, tls.dest, events.append)
    time.sleep(0.05)
    second = replace(tls.asset, id="second", file_name="ggml-second.bin")
    tls.client.download(second, tls.dest, events.append)
    assert tls.requests == [None, None]
    assert (tls.dest / second.file_name).read_bytes() == DATA


def test_second_file_resolves_a_fresh_signed_redirect(tls):
    from dataclasses import replace

    tls.mode = "fresh_redirect"
    tls.client.download(tls.asset, tls.dest, lambda event: None)
    second = replace(tls.asset, id="second", file_name="ggml-second.bin")
    tls.client.download(second, tls.dest, lambda event: None)
    assert tls.tokens == 2
    assert tls.paths == ["/asset", "/signed?token=1", "/asset", "/signed?token=2"]
    assert (tls.dest / second.file_name).read_bytes() == DATA


def test_hash_mismatch_does_not_retry(tls, capsys):
    from dataclasses import replace

    wrong = replace(tls.asset, sha256="0" * 64)
    with pytest.raises(FetchError) as caught:
        tls.client.download(wrong, tls.dest, lambda event: None)
    assert caught.value.code == Exit.MISMATCH
    assert tls.requests == [None]
    assert not (tls.dest / (wrong.file_name + ".part")).exists()


def test_tls_and_disallowed_redirect_do_not_retry(tls, capsys):
    untrusted = Downloader(policy=tls.client.policy)
    assert main(args(tls), client=untrusted) == Exit.NETWORK
    assert tls.requests == []
    tls.mode = "redirect"
    assert main(args(tls), client=tls.client) == Exit.BLOCKED
    assert tls.requests == [None]
    assert "retrying" not in capsys.readouterr().out


def test_failed_download_writes_one_redacted_local_log_line(tls, capsys):
    manifest = json.loads(tls.manifest.read_text(encoding="utf-8"))
    manifest["models"][0]["sha256"] = "0" * 64
    tls.manifest.write_text(json.dumps(manifest), encoding="utf-8")
    log = tls.dest.parent / "LocalAppData" / "Dusty" / "logs" / "dusty.log"
    marker = tls.dest.parent / "failure-logged"
    assert (
        main(
            args(tls) + ["--failure-log", str(log), "--failure-marker", str(marker)],
            client=tls.client,
        )
        == Exit.MISMATCH
    )
    assert marker.read_bytes() == b"1"
    lines = log.read_text(encoding="utf-8").splitlines()
    assert lines == [
        "download_failure step=verify class=FetchError winerror=0 code=MISMATCH exit_code=4"
    ]
    assert str(tls.dest) not in lines[0]
    assert "https://" not in lines[0]
    assert "ggml-test.bin" not in lines[0]
    assert "step" in capsys.readouterr().out


def test_local_sharing_failure_log_names_rename_and_winerror(tls, monkeypatch):
    tls.dest.mkdir()
    (tls.dest / (tls.asset.file_name + ".part")).write_bytes(DATA)
    log = tls.dest.parent / "LocalAppData" / "Dusty" / "logs" / "dusty.log"
    monkeypatch.setattr("dusty_fetch.downloader.LOCAL_RETRY_SECONDS", 0)

    def fail_rename(source, target):
        raise PermissionError(13, "Synthetic sharing violation", str(source), 32)

    monkeypatch.setattr("dusty_fetch.downloader.os.replace", fail_rename)
    assert main(args(tls) + ["--failure-log", str(log)], client=tls.client) == Exit.IO
    assert log.read_text(encoding="utf-8").splitlines() == [
        "download_failure step=rename class=PermissionError winerror=32 code=IO exit_code=7"
    ]


def test_setup_style_child_failure_reaches_localappdata_log(tls):
    manifest = json.loads(tls.manifest.read_text(encoding="utf-8"))
    manifest["models"][0]["sha256"] = "0" * 64
    tls.manifest.write_text(json.dumps(manifest), encoding="utf-8")
    local = tls.dest.parent / "LocalAppData"
    log = local / "Dusty" / "logs" / "dusty.log"
    marker = tls.dest.parent / "fetch-failure-logged"
    command = [
        sys.executable,
        str(CERTS / "fetch_child.py"),
        str(tls.port),
        str(tls.certificate),
        *args(tls),
        "--failure-log",
        str(log),
        "--failure-marker",
        str(marker),
    ]
    result = subprocess.run(
        command,
        env={**os.environ, "LOCALAPPDATA": str(local)},
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == Exit.MISMATCH
    assert log.read_text(encoding="utf-8").splitlines() == [
        "download_failure step=verify class=FetchError winerror=0 code=MISMATCH exit_code=4"
    ]
    assert marker.read_bytes() == b"1"
    assert json.loads(result.stdout.splitlines()[-1])["logged"] is True


@pytest.mark.parametrize("mode", ["ignore_range", "bad_range"])
def test_range_validation_and_restart(tls, mode):
    tls.dest.mkdir()
    part = tls.dest / (tls.asset.file_name + ".part")
    part.write_bytes(DATA[:CHUNK])
    tls.mode = mode
    code = main(args(tls), client=tls.client)
    if mode == "bad_range":
        assert code == Exit.NETWORK
        assert part.read_bytes() == DATA[:CHUNK]
    else:
        assert code == Exit.OK
        assert (tls.dest / tls.asset.file_name).read_bytes() == DATA


def test_hash_mismatch_deletes_part_and_preserves_existing_final(tls):
    from dataclasses import replace

    tls.dest.mkdir()
    final = tls.dest / tls.asset.file_name
    final.write_bytes(b"existing file")
    with pytest.raises(FetchError) as caught:
        tls.client.download(replace(tls.asset, sha256="0" * 64), tls.dest, lambda event: None)
    assert caught.value.code == Exit.MISMATCH
    assert final.read_bytes() == b"existing file"
    assert not list(tls.dest.glob("*.part"))


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/x",
        "https://github.com.evil.invalid/x",
        "https://user:password@github.com/x",
        "https://github.com:444/x",
        "https://github.com:0/x",
        "file:///anything",
        "https://github.com./x",
        "https://github.com/x#fragment",
        "https://git\nhub.com/x",
    ],
)
def test_disallowed_initial_hosts_never_connect(tls, url):
    from dataclasses import replace

    with pytest.raises(FetchError) as caught:
        Downloader().download(replace(tls.asset, url=url), tls.dest, lambda event: None)
    assert caught.value.code == Exit.BLOCKED
    assert not tls.requests


def test_disallowed_redirect_rejected_before_dns(tls):
    tls.mode = "redirect"
    assert main(args(tls), client=tls.client) == Exit.BLOCKED
    assert len(tls.requests) == 1
    assert not (tls.dest / tls.asset.file_name).exists()


def test_allowed_relative_redirect_is_followed(tls):
    tls.mode = "local_redirect"
    assert main(args(tls), client=tls.client) == Exit.OK
    assert len(tls.requests) == 2


def test_disk_full_before_request_and_during_write(tls, monkeypatch):
    monkeypatch.setattr(
        "dusty_fetch.downloader.shutil.disk_usage", lambda path: SimpleNamespace(free=0)
    )
    assert main(args(tls), client=tls.client) == Exit.DISK_FULL
    assert not tls.requests
    monkeypatch.undo()
    real_open = Path.open

    def no_space(path, mode="r", *a, **kw):
        if str(path).endswith(".part") and "x" in mode:
            raise OSError(28, "No space")
        return real_open(path, mode, *a, **kw)

    monkeypatch.setattr(Path, "open", no_space)
    assert main(args(tls), client=tls.client) == Exit.DISK_FULL
    assert not (tls.dest / tls.asset.file_name).exists()


def test_ctrl_c_emits_redacted_cancel_and_removes_part(tls, monkeypatch, capsys):
    from dusty_fetch import __main__ as cli

    original = cli.emit

    def interrupt(event):
        if event["event"] == "downloading" and event["bytes"] > 0:
            raise KeyboardInterrupt
        original(event)

    monkeypatch.setattr(cli, "emit", interrupt)
    assert main(args(tls), client=tls.client) == Exit.CANCELLED
    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert events[-1] == {"event": "cancelled", "code": "CANCELLED", "pid": os.getpid()}
    assert not (tls.dest / tls.asset.file_name).exists()
    assert not list(tls.dest.glob("*.part"))
    monkeypatch.setattr(cli, "emit", original)
    assert main(args(tls), client=tls.client) == Exit.OK


def test_terminate_process_leaves_no_final_and_os_lock_releases(tls):
    tls.mode = "slow"
    bootstrap = """
import ssl, sys
from dusty_fetch.downloader import Downloader, HostPolicy
from dusty_fetch.__main__ import main
client = Downloader(policy=HostPolicy(frozenset({'localhost'}), int(sys.argv[4])),
                    context=ssl.create_default_context(cafile=sys.argv[3]))
arguments = ['download','--id','tiny','--manifest',sys.argv[1],'--dest',sys.argv[2]]
raise SystemExit(main(arguments, client=client))
"""
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            bootstrap,
            str(tls.manifest),
            str(tls.dest),
            str(tls.certificate),
            str(tls.port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout
        for line in process.stdout:
            event = json.loads(line)
            if event.get("event") == "downloading" and event["bytes"] >= CHUNK:
                break
        else:
            pytest.fail("Child failed before a resumable write")
        process.terminate()
        process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        process.communicate(timeout=10)
    assert not (tls.dest / tls.asset.file_name).exists()
    assert main(args(tls), client=tls.client) == Exit.OK
    assert (tls.dest / tls.asset.file_name).read_bytes() == DATA


def test_untrusted_tls_certificate_is_rejected(tls):
    untrusted = Downloader(policy=tls.client.policy)
    assert main(args(tls), client=untrusted) == Exit.NETWORK
    assert not tls.requests


def test_busy_download_and_invalid_manifest_are_explicit(tls):
    tls.dest.mkdir()
    with download_lock(tls.dest / (tls.asset.file_name + ".lock")):
        assert main(args(tls), client=tls.client) == Exit.BUSY
    tls.manifest.write_text("{}", encoding="utf-8")
    assert main(args(tls), client=tls.client) == Exit.INVALID
    assert main(["download"]) == Exit.INVALID
    assert not tls.requests


def test_manifest_traversal_and_oversized_partial_never_publish(tls):
    payload = json.loads(tls.manifest.read_text(encoding="utf-8"))
    payload["models"][0]["file_name"] = "../recording.wav"
    tls.manifest.write_text(json.dumps(payload), encoding="utf-8")
    assert main(args(tls), client=tls.client) == Exit.INVALID
    assert not tls.requests
    tls.dest.mkdir()
    part = tls.dest / (tls.asset.file_name + ".part")
    part.write_bytes(DATA + b"extra")
    with pytest.raises(FetchError) as caught:
        tls.client.download(tls.asset, tls.dest, lambda event: None)
    assert caught.value.code == Exit.MISMATCH
    assert not part.exists()
