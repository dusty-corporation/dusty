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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

from dusty_fetch.__main__ import main
from dusty_fetch.downloader import (
    CHUNK,
    Downloader,
    Exit,
    FetchError,
    HostPolicy,
    download_lock,
    load_asset,
)

CERTS = Path(__file__).resolve().parents[1] / "fixtures/https"
DATA = bytes(range(256)) * 2048


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
    )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            state.requests.append(self.headers.get("Range"))
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
            if state.mode == "interrupt" and not state.interrupted:
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
    tls.mode = "interrupt"
    assert main(args(tls), client=tls.client) == Exit.NETWORK
    part = tls.dest / (tls.asset.file_name + ".part")
    offset = part.stat().st_size
    assert 0 < offset < len(DATA)
    assert not (tls.dest / tls.asset.file_name).exists()
    assert main(args(tls), client=tls.client) == Exit.OK
    assert tls.requests == [None, f"bytes={offset}-"]
    assert (tls.dest / tls.asset.file_name).read_bytes() == DATA


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
