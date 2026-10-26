"""OS-held work ownership; a crash releases the lock without a stale PID."""

import sys
from pathlib import Path
from typing import BinaryIO


def acquire(path: Path) -> BinaryIO:
    handle = path.open("r+b")
    try:
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return handle
    except BaseException:
        handle.close()
        raise


def available(path: Path) -> bool:
    try:
        acquire(path).close()
        return True
    except OSError:
        return False
