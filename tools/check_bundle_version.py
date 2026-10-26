"""Check both shipped executables carry the actual project version."""

import argparse
from pathlib import Path

import pefile  # type: ignore[import-untyped]

from dusty import __version__
from tools.release_version import versions


def check(bundle: Path) -> None:
    tag = "v" + __version__
    if ".dev" in __version__:
        tag = "v0.5.0-m5." + __version__.split(".dev", 1)[1]
    _, display, numeric = versions(tag)
    major, minor, patch, build = (int(value) for value in numeric.split("."))
    for name in ("dusty/dusty.exe", "dusty-fetch/dusty-fetch.exe"):
        with pefile.PE(str(bundle / name)) as image:
            info = image.VS_FIXEDFILEINFO[0]
            if info.FileVersionMS != (major << 16 | minor) or info.FileVersionLS != (
                patch << 16 | build
            ):
                raise ValueError("Executable numeric version does not match metadata")
            strings = {
                key: value
                for group in image.FileInfo
                for entry in group
                for table in getattr(entry, "StringTable", [])
                for key, value in table.entries.items()
            }
            if any(
                strings.get(key) != display.encode() for key in (b"FileVersion", b"ProductVersion")
            ):
                raise ValueError("Executable displayed version does not match metadata")
        print(f"{name}: {display} ({numeric})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    check(parser.parse_args().bundle)
