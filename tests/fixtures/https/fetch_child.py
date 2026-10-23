"""Test-only TLS injection in a separate downloader process, never in the GUI."""

import ssl
import sys

from dusty_fetch.__main__ import main
from dusty_fetch.downloader import Downloader, HostPolicy

client = Downloader(
    policy=HostPolicy(frozenset({"localhost"}), int(sys.argv[1])),
    context=ssl.create_default_context(cafile=sys.argv[2]),
)
raise SystemExit(main(sys.argv[3:], client=client))
