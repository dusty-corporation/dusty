"""Explicit downloader CLI; never imported by the offline application."""

import argparse
import http.client
import json
import signal
import ssl
import urllib.error
from pathlib import Path
from typing import Never

from .downloader import Downloader, Exit, FetchError, io_error, load_asset


def emit(event: dict) -> None:
    print(json.dumps(event, separators=(",", ":")), flush=True)


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise FetchError(Exit.INVALID)


def main(argv: list[str] | None = None, *, client: Downloader | None = None) -> int:
    try:
        parser = Parser(prog="dusty-fetch")
        sub = parser.add_subparsers(dest="command", required=True, parser_class=Parser)
        for name in ("download", "verify"):
            command = sub.add_parser(name)
            command.add_argument("--id", required=True)
            command.add_argument("--dest", required=True, type=Path)
            command.add_argument("--manifest", required=True, type=Path)
        args = parser.parse_args(argv)
        client = client or Downloader()
        asset = load_asset(args.manifest, args.id, client.policy)
        if args.command == "verify":
            client.verify(asset, args.dest)
            emit({"event": "verified", "bytes": asset.size, "total": asset.size})
        else:
            client.download(asset, args.dest, emit)
        return int(Exit.OK)
    except KeyboardInterrupt:
        code = Exit.CANCELLED
    except FetchError as exc:
        code = exc.code
    except BrokenPipeError:
        return int(Exit.CANCELLED)
    except (
        urllib.error.URLError,
        http.client.HTTPException,
        TimeoutError,
        ssl.SSLError,
        ConnectionError,
    ):
        code = Exit.NETWORK
    except OSError as exc:
        code = io_error(exc)
    emit({"event": "cancelled" if code == Exit.CANCELLED else "error", "code": code.name})
    return int(code)


def _terminate(signum, frame) -> None:
    raise KeyboardInterrupt


def cli_entry() -> int:
    signal.signal(signal.SIGTERM, _terminate)
    return main()


if __name__ == "__main__":
    raise SystemExit(cli_entry())
