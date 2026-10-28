"""Explicit downloader CLI; never imported by the offline application."""

import argparse
import http.client
import json
import os
import re
import signal
import ssl
import urllib.error
from pathlib import Path
from typing import Never

from .downloader import Downloader, Exit, FetchError, io_error, linked, load_asset


def emit(event: dict) -> None:
    event["pid"] = os.getpid()
    print(json.dumps(event, separators=(",", ":")), flush=True)


def failure_detail(client: Downloader | None, error: BaseException, code: Exit) -> dict:
    """Only fixed step names, exception classes and numeric codes leave the child."""
    step = client.step if client is not None else "next_file"
    if step not in {"connect", "transfer", "finalize", "verify", "rename", "next_file"}:
        step = "next_file"
    name = type(error).__name__
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", name):
        name = "Error"
    winerror = getattr(error, "winerror", None)
    if type(winerror) is not int or not 0 <= winerror <= 65535:
        winerror = 0
    return {
        "step": step,
        "class": name,
        "winerror": winerror,
        "code": code.name,
        "exit_code": int(code),
    }


def write_failure_log(path: Path, detail: dict) -> bool:
    """Append one redacted line to the same fixed local log Setup and GUI use."""
    try:
        if (
            path.name != "dusty.log"
            or path.parent.name != "logs"
            or path.parent.parent.name != "Dusty"
            or linked(path)
        ):
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        if linked(path):
            return False
        line = (
            f"download_failure step={detail['step']} class={detail['class']} "
            f"winerror={detail['winerror']} code={detail['code']} "
            f"exit_code={detail['exit_code']}\n"
        )
        with path.open("a", encoding="utf-8") as stream:
            stream.write(line)
        return True
    except OSError:
        # Diagnostics must never replace the original download result.
        return False


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise FetchError(Exit.INVALID)


def main(argv: list[str] | None = None, *, client: Downloader | None = None) -> int:
    failure_log: Path | None = None
    failure_marker: Path | None = None
    error: BaseException | None = None
    try:
        parser = Parser(prog="dusty-fetch")
        sub = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
        for name in ("download", "verify"):
            command = sub.add_parser(name)
            command.add_argument("--id", required=True)
            command.add_argument("--dest", required=True, type=Path)
            command.add_argument("--manifest", required=True, type=Path)
            command.add_argument("--failure-log", type=Path)
            command.add_argument("--failure-marker", type=Path)
            if name == "download":
                command.add_argument("--retry-status", type=Path)
        args = parser.parse_args(argv)
        failure_log = args.failure_log
        failure_marker = args.failure_marker
        client = client or Downloader()
        asset = load_asset(args.manifest, args.id, client.policy)
        if args.command == "verify":
            client.verify(asset, args.dest)
            emit({"event": "verified", "bytes": asset.size, "total": asset.size})
        else:
            status = args.retry_status
            if status is not None and (linked(status) or not status.parent.is_dir()):
                raise FetchError(Exit.IO)

            def retry_state(active: bool) -> None:
                if status is None:
                    return
                if active:
                    with status.open("xb") as stream:
                        stream.write(b"1")
                else:
                    status.unlink(missing_ok=True)

            client.download(asset, args.dest, emit, retry_state=retry_state)
        return int(Exit.OK)
    except KeyboardInterrupt:
        code = Exit.CANCELLED
    except FetchError as exc:
        code = exc.code
        error = exc
    except BrokenPipeError:
        return int(Exit.CANCELLED)
    except (
        urllib.error.URLError,
        http.client.HTTPException,
        TimeoutError,
        ssl.SSLError,
        ConnectionError,
    ) as exc:
        code = Exit.NETWORK
        error = exc
    except OSError as exc:
        code = io_error(exc)
        error = exc
    if code == Exit.CANCELLED:
        emit({"event": "cancelled", "code": code.name})
    else:
        detail = failure_detail(client, error or FetchError(code), code)
        logged = False
        if failure_log is not None:
            logged = write_failure_log(failure_log, detail)
        if logged and failure_marker is not None:
            try:
                if not linked(failure_marker):
                    with failure_marker.open("xb") as stream:
                        stream.write(b"1")
            except OSError:
                pass
        emit({"event": "error", **detail, "logged": logged})
    return int(code)


def _terminate(signum, frame) -> None:
    raise KeyboardInterrupt


def cli_entry() -> int:
    signal.signal(signal.SIGTERM, _terminate)
    return main()


if __name__ == "__main__":
    from .crash_policy import install_crash_policy

    install_crash_policy()
    raise SystemExit(cli_entry())
