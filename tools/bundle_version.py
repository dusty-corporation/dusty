"""Prepare Windows executable version resources from the project metadata."""

from pathlib import Path

from dusty import __version__
from tools.release_version import versions


def write_version(path: Path) -> None:
    tag = "v" + __version__
    if ".dev" in __version__:
        tag = "v0.5.0-m5." + __version__.split(".dev", 1)[1]
    _, display, numeric = versions(tag)
    numbers = tuple(int(value) for value in numeric.split("."))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "VSVersionInfo(ffi=FixedFileInfo("
        f"filevers={numbers!r}, prodvers={numbers!r}, "
        "mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0,0)), "
        "kids=[StringFileInfo([StringTable('040904B0', ["
        f"StringStruct('FileVersion', {display!r}), "
        f"StringStruct('ProductVersion', {display!r}), "
        "StringStruct('ProductName', 'Dusty')])]), "
        "VarFileInfo([VarStruct('Translation', [1033,1200])])])\n",
        encoding="utf-8",
    )
