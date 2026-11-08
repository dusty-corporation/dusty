"""Discover local cloud roots without reading cloud-file contents or remote APIs."""

import json
import os
import re
import stat
import sys
from collections.abc import Callable, Mapping
from pathlib import Path


def _read_mount(scope: str, key: str) -> str | None:
    if sys.platform != "win32":
        return None
    import winreg

    hive = winreg.HKEY_LOCAL_MACHINE if scope == "machine" else winreg.HKEY_CURRENT_USER
    try:
        with winreg.OpenKey(hive, key, 0, winreg.KEY_READ) as handle:
            value, kind = winreg.QueryValueEx(handle, "DefaultMountPoint")
            if isinstance(value, str) and kind in {winreg.REG_SZ, winreg.REG_EXPAND_SZ}:
                return value
    except OSError:
        pass
    return None


def google_drive_roots(
    environment: Mapping[str, str], *, reader: Callable[[str, str], str | None] | None = None
) -> tuple[Path, ...]:
    """Honor policy/user/host precedence, then the documented default streaming drive."""
    read = _read_mount if reader is None else reader
    if os.name != "nt" and reader is None:
        return ()
    variables = {key.upper(): value for key, value in environment.items()}
    for scope, key in (
        ("machine", r"Software\Policies\Google\DriveFS"),
        ("user", r"Software\Google\DriveFS"),
        ("machine", r"Software\Google\DriveFS"),
    ):
        value = read(scope, key)
        if value and value.strip():
            value = re.sub(
                r"%([^%]+)%", lambda match: variables.get(match[1].upper(), match[0]), value.strip()
            )
            if len(value.rstrip(":/\\")) == 1 and value[0].isalpha():
                value = value[0].upper() + ":\\"
            path = Path(value)
            if path.is_absolute() and len(path.drive) == 2 and path.drive[1] == ":":
                return (path,)
    local = environment.get("LOCALAPPDATA")
    if local and (Path(local) / "Google/DriveFS").is_dir():
        return (Path("G:/"),)
    return ()


def _absolute_local_path(value: str) -> Path | None:
    if not value or value.startswith("//") or any(ord(char) < 32 for char in value):
        return None
    path = Path(value)
    return path if path.is_absolute() else None


def _local_directory(path: Path) -> bool:
    try:
        return stat.S_ISDIR(path.lstat().st_mode)
    except (OSError, ValueError):
        return False


def _mac_dropbox_roots(home: Path) -> tuple[Path, ...]:
    """Read only the vendor's small local JSON configuration, never symlink content."""
    directory = home / ".dropbox"
    if not _local_directory(directory):
        return ()
    directory_flag = getattr(os, "O_DIRECTORY", None)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    nonblock = getattr(os, "O_NONBLOCK", None)
    if directory_flag is None or nofollow is None or nonblock is None:
        return ()
    directory_fd = None
    config_fd = None
    try:
        directory_fd = os.open(directory, os.O_RDONLY | directory_flag | nofollow)
        info = os.stat("info.json", dir_fd=directory_fd, follow_symlinks=False)
        # Reject placeholders before open so discovery does not hydrate configuration.
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_size > 1024 * 1024
            or getattr(info, "st_flags", 0) & 0x40000000  # Darwin SF_DATALESS
        ):
            return ()
        config_fd = os.open("info.json", os.O_RDONLY | nonblock | nofollow, dir_fd=directory_fd)
        opened = os.fstat(config_fd)
        if (
            (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)
            or not stat.S_ISREG(opened.st_mode)
            or opened.st_size > 1024 * 1024
            or getattr(opened, "st_flags", 0) & 0x40000000
        ):
            return ()
        content = os.read(config_fd, 1024 * 1024 + 1)
        if len(content) > 1024 * 1024:
            return ()
        data = json.loads(content)
        roots = []
        if isinstance(data, dict):
            for item in data.values():
                if isinstance(item, dict) and isinstance(value := item.get("path"), str):
                    path = _absolute_local_path(value)
                    if path is not None:
                        roots.append(path)
        return tuple(roots)
    except (OSError, ValueError, TypeError, RecursionError):
        return ()
    finally:
        for descriptor in (config_fd, directory_fd):
            if descriptor is not None:
                os.close(descriptor)


def _known_mac_provider(name: str) -> bool:
    """Recognize supported domain name forms, not arbitrary CloudStorage children."""
    if any(ord(char) < 32 for char in name):
        return False
    if name == "Dropbox":
        return True
    if name.startswith("Dropbox (") and name.endswith(")"):
        account = name[len("Dropbox (") : -1]
    else:
        for prefix in (
            "Dropbox-",
            "Dropbox - ",
            "Dropbox \u2013 ",
            "OneDrive-",
            "OneDrive - ",
            "GoogleDrive-",
        ):
            if name.startswith(prefix):
                account = name[len(prefix) :]
                break
        else:
            return False
    return bool(account) and account == account.strip()


def mac_sync_roots(environment: Mapping[str, str]) -> tuple[Path, ...]:
    """Inspect only fixed candidate roots and immediate File Provider directory names."""
    home = _absolute_local_path(environment.get("HOME", ""))
    if home is None:
        return ()
    roots = list(_mac_dropbox_roots(home))
    # This conventional iCloud path is an existence-based heuristic, not an API contract.
    icloud = home / "Library/Mobile Documents/com~apple~CloudDocs"
    if _local_directory(icloud):
        roots.append(icloud)
    providers = home / "Library/CloudStorage"
    if _local_directory(providers):
        try:
            for candidate in providers.iterdir():
                if _known_mac_provider(candidate.name) and _local_directory(candidate):
                    roots.append(candidate)
        except OSError:
            pass
    return tuple(roots)
