"""Test-only TLS injection in a separate downloader process, never in the GUI.

Usage: fetch_child.py PORT CA_FILE [--test-checkpoint=PATH] DUSTY_FETCH_ARGS...
The checkpoint arrives as an argument because the macOS runner gives the
downloader an exact minimal environment. The DUSTY_TEST_FETCH_CHECKPOINT
variable remains a fallback, which a Windows child still inherits.
"""

import atexit
import json
import os
import ssl
import sys
from pathlib import Path

from dusty_fetch import __main__ as cli
from dusty_fetch.downloader import Downloader, HostPolicy

client = Downloader(
    policy=HostPolicy(frozenset({"localhost"}), int(sys.argv[1])),
    context=ssl.create_default_context(cafile=sys.argv[2]),
)
CHECKPOINT_FLAG = "--test-checkpoint="
if len(sys.argv) > 3 and sys.argv[3].startswith(CHECKPOINT_FLAG):
    checkpoint = sys.argv.pop(3).removeprefix(CHECKPOINT_FLAG)
else:
    checkpoint = os.environ.get("DUSTY_TEST_FETCH_CHECKPOINT")
if checkpoint:
    target = Path(checkpoint)
    original_emit = cli.emit
    atexit.register(lambda: target.with_name("fetch-cleanup-ran").touch())

    def observe(event):
        original_emit(event)
        if event["event"] == "downloading" and event["bytes"] == 2 * 65536:
            temporary = target.with_suffix(".tmp")
            temporary.write_text(
                json.dumps({"pid": os.getpid(), "bytes": event["bytes"]}), encoding="utf-8"
            )
            temporary.replace(target)

    cli.emit = observe
raise SystemExit(cli.main(sys.argv[3:], client=client))
