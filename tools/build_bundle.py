"""Build the packaging spike from pinned dev assets; never copy model weights."""

import json
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def make_icon() -> None:
    """Export the existing original Qt waveform drawing as a PNG-backed ICO."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtWidgets import QApplication

    from dusty.app.theme import application_icon

    app = QApplication.instance() or QApplication([])
    icon = application_icon()
    images = []
    for size in (16, 32, 64):
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not icon.pixmap(size, size).save(buffer, "PNG"):
            raise RuntimeError("Icon export failed")
        images.append((size, data.data()))
    offset = 6 + 16 * len(images)
    header = struct.pack("<HHH", 0, 1, len(images))
    for size, data in images:
        header += struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    target = ROOT / "resources/icons/dusty.ico"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(header + b"".join(data for _, data in images))
    del app


def stage(bundle: Path) -> None:
    for folder in ("cpu", "vulkan", "ffmpeg"):
        target = bundle / "bin" / folder
        target.mkdir(parents=True, exist_ok=True)
        for source in sorted((ROOT / "build/bin" / folder).iterdir()):
            if source.suffix.lower() == ".dll" or source.name in {
                "whisper-cli.exe",
                "ffmpeg.exe",
                "ffprobe.exe",
                "LICENSE.txt",
                "buildconf.txt",
            }:
                shutil.copy2(source, target / source.name)
    shutil.copytree(ROOT / "resources", bundle / "resources", dirs_exist_ok=True)
    manifest = json.loads((bundle / "resources/models.json").read_text(encoding="utf-8"))
    forbidden = {item["file_name"] for group in ("models", "vad") for item in manifest[group]}
    if any(path.name in forbidden or path.suffix == ".bin" for path in bundle.rglob("*")):
        raise RuntimeError("Model weights must not be bundled")


def main() -> None:
    if not (ROOT / "resources/icons/dusty.ico").is_file():
        make_icon()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--workpath",
            "build/pyinstaller",
            "packaging/dusty.spec",
        ],
        cwd=ROOT,
        check=True,
    )
    stage(ROOT / "dist/Dusty")


if __name__ == "__main__":
    main()
