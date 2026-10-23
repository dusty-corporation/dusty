"""Build the packaging spike from pinned dev assets; never copy model weights."""

import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tomllib
import zipfile
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
        png = QByteArray()
        buffer = QBuffer(png)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not icon.pixmap(size, size).save(buffer, "PNG"):
            raise RuntimeError("Icon export failed")
        images.append((size, bytes(png.data())))
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
    pins = tomllib.loads((ROOT / "native/versions.toml").read_text(encoding="utf-8"))
    archive_pins = {
        "cpu": ("whisper-cpu.zip", "whisper_cpu_zip_sha256"),
        "vulkan": ("whisper-vulkan.zip", "whisper_vulkan_zip_sha256"),
        "ffmpeg": ("minimal-ffmpeg.zip", "minimal_ffmpeg_zip_sha256"),
    }
    for folder in ("cpu", "vulkan", "ffmpeg"):
        archive_name, pin_key = archive_pins[folder]
        archive_path = ROOT / "build/downloads" / archive_name
        with archive_path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != pins["engine_release"][pin_key]:
                raise ValueError("Native archive differs from engine-v2 pin")
        target = bundle / "bin" / folder
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path) as archive:
            for source in sorted((ROOT / "build/bin" / folder).iterdir()):
                if source.suffix.lower() == ".dll" or source.name in {
                    "whisper-cli.exe",
                    "ffmpeg.exe",
                    "ffprobe.exe",
                    "LICENSE.txt",
                    "buildconf.txt",
                }:
                    if source.read_bytes() != archive.read(source.name):
                        raise ValueError("Native staging file differs from verified archive")
                    shutil.copy2(source, target / source.name)
    shutil.copytree(ROOT / "resources", bundle / "resources", dirs_exist_ok=True)
    manifest = json.loads((bundle / "resources/models.json").read_text(encoding="utf-8"))
    forbidden = {item["file_name"] for group in ("models", "vad") for item in manifest[group]}
    if any(path.name in forbidden or path.suffix == ".bin" for path in bundle.rglob("*")):
        raise RuntimeError("Model weights must not be bundled")


def main() -> None:
    if not (ROOT / "resources/icons/dusty.ico").is_file():
        make_icon()
    destination = (ROOT / "dist/Dusty").resolve()
    if destination.parent != (ROOT / "dist").resolve() or not destination.is_relative_to(ROOT.resolve()):
        raise ValueError("Bundle output must stay inside the repository dist folder")
    if destination.exists():
        shutil.rmtree(destination)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--workpath",
            "build/pyinstaller",
            "--distpath",
            "dist/Dusty",
            "packaging/dusty.spec",
        ],
        cwd=ROOT,
        check=True,
    )
    stage(ROOT / "dist/Dusty")


if __name__ == "__main__":
    main()
