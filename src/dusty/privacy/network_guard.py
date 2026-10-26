"""Block Python socket audit events without importing networking modules."""

import logging
import os
import sys
from pathlib import Path

BLOCKED_EVENTS = frozenset(
    {
        "socket.__new__",
        "socket.connect",
        "socket.bind",
        "socket.sendto",
        "socket.sendmsg",
        "socket.getaddrinfo",
        "socket.gethostbyname",
        "socket.gethostbyaddr",
        "socket.getnameinfo",
    }
)
_installed = False
_logger = logging.getLogger("dusty.privacy.network_guard")


class NetworkBlockedError(RuntimeError):
    """The offline main app attempted a Python network operation."""


def _audit(event: str, _arguments: tuple[object, ...]) -> None:
    blocked = event in BLOCKED_EVENTS or event in {
        "webbrowser.open",
        "subprocess.Popen",
        "os.system",
        "os.posix_spawn",
        "os.spawn",
        "os.fork",
        "os.forkpty",
        "os.exec",
    }
    if event in {"os.startfile", "os.startfile/2"}:
        try:
            argument = _arguments[0]
            if not isinstance(argument, (str, bytes, os.PathLike)):
                raise TypeError("Shell target must be a filesystem path")
            target = os.fsdecode(argument)
            # Do not even stat a UNC/URL path while deciding whether to delegate.
            blocked = target.startswith(("\\\\", "//")) or "://" in target
            if not blocked:
                blocked = not Path(target).is_dir()
        except (OSError, ValueError, TypeError, IndexError):
            blocked = True
    if event == "ctypes.dlopen" and _arguments:
        name = os.fsdecode(_arguments[0]) if isinstance(_arguments[0], (str, bytes)) else ""
        name = name.replace("\\", "/").rsplit("/", 1)[-1].rstrip(" .").casefold()
        blocked = name.removesuffix(".dll") in {
            "ws2_32",
            "wsock32",
            "winhttp",
            "wininet",
            "urlmon",
            "dnsapi",
            "mswsock",
            "iphlpapi",
        }
    if blocked:
        _logger.warning("network_blocked event=%s", event)
        raise NetworkBlockedError(f"Network operation blocked: {event}")


def install_guard() -> None:
    """Install the irreversible guard once per interpreter."""
    global _installed
    if not _installed:
        sys.addaudithook(_audit)
        _installed = True


def is_installed() -> bool:
    return _installed
