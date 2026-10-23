"""Reject Python test access to the real app-data folder for the entire session."""

import os
import sys
from pathlib import Path

_INSTALLED = False


def install_guard(root: Path) -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    protected = os.path.normcase(os.path.abspath(root))
    events = {
        "open": (0,),
        "os.listdir": (0,),
        "os.scandir": (0,),
        "os.mkdir": (0,),
        "os.remove": (0,),
        "os.rmdir": (0,),
        "os.rename": (0, 1),
        "os.chmod": (0,),
        "os.utime": (0,),
        "os.link": (0, 1),
        "os.symlink": (0, 1),
        "shutil.copyfile": (0, 1),
        "shutil.rmtree": (0,),
    }

    def audit(event: str, args: tuple[object, ...]) -> None:
        for index in events.get(event, ()):
            if index >= len(args):
                continue
            value = args[index]
            if not isinstance(value, (str, bytes, os.PathLike)):
                continue
            candidate = os.path.normcase(os.path.abspath(os.fsdecode(value)))
            if candidate == protected or candidate.startswith(protected + os.sep):
                raise PermissionError("Test access to real Dusty app data is forbidden")

    sys.addaudithook(audit)
    _INSTALLED = True
