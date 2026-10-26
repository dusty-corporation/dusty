"""Losslessly encode the review app's own client-area bitmaps as PNG files."""

import argparse
from pathlib import Path

from PySide6.QtGui import QImage


def convert(folder: Path) -> None:
    files = sorted(folder.glob("*.bmp"))
    if not files:
        raise ValueError("No native review bitmaps found")
    for path in files:
        image = QImage(str(path))
        if image.isNull() or not image.save(str(path.with_suffix(".png"))):
            raise ValueError("Native review PNG conversion failed")
    (folder / "README.md").write_text(
        "# Native installer page review\n\n"
        "Review-only executable, same controls as Setup, no installation or network.\n"
        "Client areas captured by the review app itself; native title bars excluded.\n"
        "PNG encoding is lossless, without resizing or simulated DPI.\n"
        "Per-page DPI metadata is retained in the CI audit, outside the screenshot zip.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    convert(parser.parse_args().folder)
