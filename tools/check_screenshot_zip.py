"""Review archives contain only PNG captures and their root README.md."""

import argparse
import zipfile
from pathlib import Path, PurePosixPath


def check(path: Path) -> bool:
    with zipfile.ZipFile(path) as archive:
        files = [item for item in archive.infolist() if not item.is_dir()]
        if not files or len({item.filename for item in files}) != len(files):
            return False
        for item in files:
            name = PurePosixPath(item.filename)
            if name.is_absolute() or ".." in name.parts or "\\" in item.filename:
                return False
            if name == PurePosixPath("README.md"):
                continue
            if name.suffix.lower() != ".png":
                return False
            if not archive.read(item).startswith(b"\x89PNG\r\n\x1a\n"):
                return False
        return any(item.filename == "README.md" for item in files)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    raise SystemExit(0 if check(parser.parse_args().path) else 1)
