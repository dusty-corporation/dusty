"""Fetch hash-pinned development binaries and models; never ship this module."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
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
# The Mac engine: native/macos/build_*.sh output, packaged by native-macos.yml.
MAC_ENGINE_ASSETS = {
    "whisper-cpu-macos-arm64.zip": ("cpu_archive_sha256", "whisper-cpu"),
    "whisper-metal-macos-arm64.zip": ("metal_archive_sha256", "whisper-metal"),
    "ffmpeg-macos-arm64.zip": ("ffmpeg_archive_sha256", "ffmpeg"),
}
MAC_METADATA = {
    "SHA256SUMS.txt",
    "architecture.txt",
    "architectures.txt",
    "buildconf.txt",
    "dependencies.txt",
    "minimum-os.txt",
    "provenance.txt",
}
MAC_FETCHED_NATIVE = Path("build/engine-macos/macos-arm64/native-v3")
MAC_PACKAGE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+-]*")
DEV_MODEL_IDS = ("tiny-f16", "small.en-f16", "medium-f16")
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
    descriptor, name = tempfile.mkstemp(suffix=".part", dir=target.parent)
    import os

    os.close(descriptor)
    temporary = Path(name)
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


def extract_mac_component(archive_path: Path, component: str, native_root: Path) -> Path:
    """Unpack one verified Mac engine archive into <native_root>/<component>.

    Members must be <component>/<metadata file> or <component>/package/<file>,
    with no links, folders below package or other files. Every package file must
    then match the component's SHA256SUMS.txt, and every listed file must exist.
    """
    target = native_root / component
    if target.exists():
        shutil.rmtree(target)
    with zipfile.ZipFile(archive_path) as archive:
        members = [info for info in archive.infolist() if not info.is_dir()]
        if not members or archive.testzip() is not None:
            raise ValueError(f"Invalid archive: {archive_path.name}")
        for info in members:
            parts = info.filename.split("/")
            mode = info.external_attr >> 16
            if mode and (mode & 0o170000) not in (0, 0o100000):
                raise ValueError(f"Unexpected archive member: {info.filename}")
            if parts[0] != component or not (
                (len(parts) == 2 and parts[1] in MAC_METADATA)
                or (
                    len(parts) == 3
                    and parts[1] == "package"
                    and MAC_PACKAGE_NAME.fullmatch(parts[2])
                )
            ):
                raise ValueError(f"Unexpected archive member: {info.filename}")
        for info in members:
            destination = native_root / info.filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(destination.name + ".part")
            with archive.open(info) as source, temporary.open("wb") as output:
                shutil.copyfileobj(source, output)
            temporary.chmod(0o755 if (info.external_attr >> 16) & 0o111 else 0o644)
            temporary.replace(destination)
    sums_path = target / "SHA256SUMS.txt"
    if not sums_path.is_file():
        raise ValueError(f"{component} has no SHA256SUMS.txt")
    listed = {}
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            listed[name.strip().lstrip("*")] = digest
    package = target / "package"
    present = {path.name for path in package.iterdir()} if package.is_dir() else set()
    if not listed or present != set(listed):
        raise ValueError(f"{component} package does not match its SHA256SUMS.txt")
    for name, digest in listed.items():
        if sha256_file(package / name) != digest:
            raise ValueError(f"{component}/{name} does not match its SHA256SUMS.txt")
    return target


def fetch_macos_engine(root: Path, pins: dict[str, Any]) -> None:
    """Fetch the pinned Mac engine into build/engine-macos and stage build/bin from it.

    The fetched packages get their own folder, so a local engine build in
    build/macos-arm64 is never replaced. build/bin must be new or empty.
    """
    engine = pins["engine_release_macos"]
    downloads = root / "build/downloads"
    native_root = root / MAC_FETCHED_NATIVE
    for asset_name, (hash_key, component) in MAC_ENGINE_ASSETS.items():
        url = f"https://github.com/{REPO}/releases/download/{engine['tag']}/{asset_name}"
        archive_path = downloads / asset_name
        download_verified(url, archive_path, engine[hash_key])
        extract_mac_component(archive_path, component, native_root)
        print(f"Verified {asset_name}")
    # Lay out bin_dir the way dusty.engine.binaries expects, from those packages only.
    subprocess.run(
        [
            sys.executable,
            str(root / "tools/stage_macos_dev_bin.py"),
            "--source-build",
            str(root / "build/engine-macos"),
            "--out",
            str(root / "build/bin"),
            "--no-models",
        ],
        check=True,
    )


def selected_models(
    manifest: dict[str, Any], release_tag: str, *, recommended: bool = False
) -> list[dict[str, Any]]:
    """Select the exact PM-approved dev set from a pinned release manifest."""
    if manifest.get("release_tag") != release_tag:
        raise ValueError("Model release tag mismatch")
    models = {entry["id"]: entry for entry in manifest["models"]}
    vad = {entry["id"]: entry for entry in manifest["vad"]}
    ids = DEV_MODEL_IDS + (("large-v3-turbo-q8_0", "small-f16") if recommended else ())
    entries = [models[model_id] for model_id in ids] + [vad[VAD_ID]]
    prefix = f"https://github.com/{REPO}/releases/download/{release_tag}/"
    for entry in entries:
        if entry["url"] != prefix + entry["file_name"]:
            raise ValueError("Model URL does not match pinned release")
        if len(entry["sha256"]) != 64 or entry["size_bytes"] <= 0:
            raise ValueError("Invalid model hash or size")
    return entries


def fetch(root: Path = ROOT, *, recommended: bool = False) -> None:
    pins = tomllib.loads((root / "native/versions.toml").read_text(encoding="utf-8"))
    models = pins["models_release"]
    downloads = root / "build/downloads"
    if sys.platform != "darwin":
        engine = pins["engine_release"]
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
    for entry in selected_models(manifest, models["tag"], recommended=recommended):
        destination = root / "build/models" / entry["file_name"]
        download_verified(entry["url"], destination, entry["sha256"])
        if destination.stat().st_size != entry["size_bytes"]:
            raise ValueError(f"Size mismatch for {entry['file_name']}")
        print(f"Verified {entry['file_name']}")
    if sys.platform == "darwin":
        fetch_macos_engine(root, pins)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--recommended-models",
        action="store_true",
        help="Also fetch Turbo q8_0 and Small for GUI walkthroughs",
    )
    arguments = parser.parse_args()
    fetch(arguments.root.resolve(), recommended=arguments.recommended_models)


if __name__ == "__main__":
    main()
