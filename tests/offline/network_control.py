"""Runner-only positive control for WFP auditing; never imports Dusty."""

import os
import socket

print(os.getpid(), flush=True)
try:
    with socket.create_connection(("192.0.2.1", 9), timeout=3):
        raise SystemExit("Firewall control unexpectedly connected")
except OSError:
    pass
