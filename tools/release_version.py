"""Apply the PM-approved M5 test-tag version mapping in a disposable checkout."""

import argparse
import re
from pathlib import Path


def versions(tag: str) -> tuple[str, str, str]:
    public = re.fullmatch(r"v1\.0\.(0|[1-9][0-9]*)", tag)
    if public and int(public[1]) <= 65535:
        version = tag[1:]
        return version, version, version + ".0"
    match = re.fullmatch(r"v0\.5\.0-m5\.([1-9][0-9]*)", tag)
    if not match or int(match[1]) > 65535:
        raise ValueError("Only v1.0.x and approved v0.5.0-m5.N test versions are supported")
    number = match[1]
    return f"0.5.0.dev{number}", tag[1:], f"0.5.0.{number}"


def apply(root: Path, tag: str) -> None:
    package, _, _ = versions(tag)
    for name, pattern in (
        ("pyproject.toml", r'(?m)^version = "[^"]+"'),
        ("src/dusty/__init__.py", r'(?m)^__version__ = "[^"]+"'),
        ("uv.lock", r'(?m)(?<=name = "dusty"\n)version = "[^"]+"'),
    ):
        path = root / name
        text = path.read_text(encoding="utf-8")
        prefix = "__version__" if name.endswith("__init__.py") else "version"
        text, count = re.subn(pattern, f'{prefix} = "{package}"', text)
        if count != 1:
            raise ValueError(f"Expected one project version in {name}")
        path.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("--apply", action="store_true", help="Modify metadata in this checkout")
    args = parser.parse_args()
    versions(args.tag)
    if args.apply:
        apply(Path(__file__).resolve().parents[1], args.tag)
