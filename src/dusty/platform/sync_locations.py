"""Read documented Windows Google Drive mount settings without changing them."""

import os
import re
from collections.abc import Callable, Mapping
from pathlib import Path


def _read_mount(scope: str, key: str) -> str | None:
    if os.name != "nt":
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
