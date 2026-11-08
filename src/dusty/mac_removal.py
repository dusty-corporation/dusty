"""macOS: remove Dusty's own data from inside the app (D-MAC-025).

Windows removes this data in its uninstaller. A Mac app is removed by dragging
it to the Trash, which leaves the data folder behind, so the Tools menu has
Remove Dusty data. The window asks first and closes; once the event loop has
ended, __main__ calls remove_data while this process still holds the
single-instance lease. A launch during removal therefore finds a running Dusty
and only asks it to come forward.

The removal itself is the Windows uninstaller's (installer_cleanup.cleanup):
only files Dusty recognizes are deleted, nothing inside a recording, transcript
or output folder is touched, unfinished work is removed only when its ownership
marker proves it is Dusty's, and anything uncertain is kept. Two things exist
only on the Mac and are handled here:

- the single-instance control files in .gui-instance, removed last, and only
  when they are this user's private regular files;
- Finder's .DS_Store view settings in Dusty's own folders.

Nothing here logs: the log is closed first so it can be removed.
"""

import logging
import os
import stat
import sys
from pathlib import Path

from dusty.installer_cleanup import cleanup
from dusty.runtime_paths import RuntimePaths
from dusty.work_area import linked

INSTANCE_FOLDER = ".gui-instance"
INSTANCE_FILES = ("owner", "activation")
FINDER_FILE = ".DS_Store"
OWN_FOLDERS = ("", "logs", "state", "models", "work")


def _private_file(path: Path) -> bool:
    """A regular file of this user with one name, not a link."""
    info = os.lstat(path)
    if sys.platform == "win32":
        raise NotImplementedError("macOS only")
    return stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1


def stop_logging() -> None:
    """Close Dusty's log file so it can be removed and is not written again."""
    logger = logging.getLogger("dusty")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    logger.addHandler(logging.NullHandler())


def _remove_finder_files(root: Path) -> None:
    for folder in OWN_FOLDERS:
        path = root / folder / FINDER_FILE
        if not linked(path.parent) and path.exists() and _private_file(path):
            path.unlink()


def _remove_instance_files(root: Path) -> bool:
    folder = root / INSTANCE_FOLDER
    if not folder.exists() and not folder.is_symlink():
        return True
    if linked(folder) or not folder.is_dir():
        return False
    for name in INSTANCE_FILES:
        path = folder / name
        if path.exists() or path.is_symlink():
            if not _private_file(path):
                return False
            path.unlink()
    try:
        folder.rmdir()  # Fails, and keeps the folder, if anything else is inside.
    except OSError:
        return False
    return True


def finished(root: Path, *, remove_models: bool) -> bool:
    """True when nothing is left, or only the models folder when models are kept."""
    if not root.exists():
        return True
    remaining = list(root.iterdir())
    return not remove_models and all(path == root / "models" for path in remaining)


def remove_data(paths: RuntimePaths, *, remove_models: bool) -> bool:
    """Remove Dusty's data folder contents; False means something was kept."""
    stop_logging()
    root = paths.user_dir
    try:
        if not root.exists():
            return True
        if linked(root):
            return False
        _remove_finder_files(root)
        cleanup(paths, remove_models=remove_models)
        instance_removed = _remove_instance_files(root)
        try:
            root.rmdir()
        except OSError:
            pass
        return instance_removed and finished(root, remove_models=remove_models)
    except (OSError, ValueError):
        return False
