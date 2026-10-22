"""Block Python socket audit events without importing networking modules."""

import logging
import sys

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
    if event in BLOCKED_EVENTS:
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
