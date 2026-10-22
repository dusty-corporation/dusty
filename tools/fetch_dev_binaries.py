"""Fetch hash-pinned development binaries and models; never ship this module."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tomllib
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

REPO = "dusty-corporation/dusty"
ROOT = Path(__file__).resolve().parents[1]
ENGINE_ASSETS = {
    "whisper-cpu.zip": ("whisper_cpu_zip_sha256", "cpu"),
    "whisper-vulkan.zip": ("whisper_vulkan_zip_sha256", "vulkan"),
    "minimal-ffmpeg.zip": ("minimal_ffmpeg_zip_sha256", "ffmpeg"),
}
DEV_MODEL_IDS = ("tiny-f16", "small.en-f16", "small-f16")
VAD_ID = "silero-vad"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_verified(url: str, target: Path, expected_sha256: str) -> None:
    """Reuse only matching files and atomically install a verified download."""
    if target.exists() and sha256_file(target) == expected_sha256:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".part")
    try:
        with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as stream:
            shutil.copyfileobj(response, stream)
        if sha256_file(temporary) != expected_sha256:
            raise ValueError(f"SHA-256 mismatch for {target.name}")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def extract_flat_zip(archive_path: Path, destination: Path) -> None:
    """Unpack a verified flat runtime archive, rejecting paths and other files."""
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if not names or archive.testzip() is not None:
            raise ValueError(f"Invalid archive: {archive_path.name}")
        for name in names:
            if Path(name).name != name or Path(name).suffix.lower() not in {
                ".exe",
                ".dll",
                ".txt",
            }:
                raise ValueError(f"Unexpected archive member: {name}")
            if name.endswith(".txt") and name not in {"buildconf.txt", "LICENSE.txt"}:
                raise ValueError(f"Unexpected archive member: {name}")
        for name in names:
            temporary = destination / (name + ".part")
            with archive.open(name) as source, temporary.open("wb") as output:
                shutil.copyfileobj(source, output)
            temporary.replace(destination / name)


def selected_models(manifest: dict[str, Any], release_tag: str) -> list[dict[str, Any]]:
    """Select the exact PM-approved dev set from a pinned release manifest."""
    if manifest.get("release_tag") != release_tag:
        raise ValueError("Model release tag mismatch")
    models = {entry["id"]: entry for entry in manifest["models"]}
    vad = {entry["id"]: entry for entry in manifest["vad"]}
    entries = [models[model_id] for model_id in DEV_MODEL_IDS] + [vad[VAD_ID]]
    prefix = f"https://github.com/{REPO}/releases/download/{release_tag}/"
    for entry in entries:
        if entry["url"] != prefix + entry["file_name"]:
            raise ValueError("Model URL does not match pinned release")
        if len(entry["sha256"]) != 64 or entry["size_bytes"] <= 0:
            raise ValueError("Invalid model hash or size")
    return entries


def fetch(root: Path = ROOT) -> None:
    pins = tomllib.loads((root / "native/versions.toml").read_text(encoding="utf-8"))
    engine = pins["engine_release"]
    models = pins["models_release"]
    downloads = root / "build/downloads"
    for asset_name, (hash_key, folder) in ENGINE_ASSETS.items():
        url = f"https://github.com/{REPO}/releases/download/{engine['tag']}/{asset_name}"
        archive_path = downloads / asset_name
        download_verified(url, archive_path, engine[hash_key])
        extract_flat_zip(archive_path, root / "build/bin" / folder)
        print(f"Verified {asset_name}")

    manifest_path = downloads / "models-v1.json"
    manifest_url = f"https://github.com/{REPO}/releases/download/{models['tag']}/models.json"
    download_verified(manifest_url, manifest_path, models["manifest_sha256"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in selected_models(manifest, models["tag"]):
        destination = root / "build/models" / entry["file_name"]
        download_verified(entry["url"], destination, entry["sha256"])
        if destination.stat().st_size != entry["size_bytes"]:
            raise ValueError(f"Size mismatch for {entry['file_name']}")
        print(f"Verified {entry['file_name']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    arguments = parser.parse_args()
    fetch(arguments.root.resolve())


if __name__ == "__main__":
    main()
