"""Stage exact corresponding FFmpeg source alongside every draft release."""

import argparse
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = json.loads((ROOT / "packaging/licenses/ffmpeg-source.json").read_text(encoding="utf-8"))


def verify(source: Path) -> None:
    archive = source / PIN["name"]
    with archive.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != PIN["sha256"]:
            raise ValueError("FFmpeg corresponding source hash differs from pin")
    if (source / "build_ffmpeg.sh").read_bytes() != (ROOT / "native/build_ffmpeg.sh").read_bytes():
        raise ValueError("FFmpeg build script differs from the reviewed source tree")


def stage(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    archive = output / PIN["name"]
    if not archive.exists():
        with (
            urllib.request.urlopen(PIN["url"], timeout=60) as response,
            archive.open("xb") as target,
        ):
            shutil.copyfileobj(response, target)
    shutil.copyfile(ROOT / "native/build_ffmpeg.sh", output / "build_ffmpeg.sh")
    verify(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    stage(parser.parse_args().output)
