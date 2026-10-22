"""Verify that development assets are pinned and safely unpacked."""

import hashlib
import io
import zipfile
from pathlib import Path

import pytest

from tools.fetch_dev_binaries import download_verified, extract_flat_zip, selected_models


def test_download_rejects_wrong_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tools.fetch_dev_binaries.urllib.request.urlopen",
        lambda _url, timeout: io.BytesIO(b"tampered"),
    )
    target = tmp_path / "file.bin"
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        download_verified("https://example.invalid/file.bin", target, "0" * 64)
    assert not target.exists()
    assert not target.with_name("file.bin.part").exists()


def test_download_reuses_only_verified_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "file.bin"
    target.write_bytes(b"trusted")
    digest = hashlib.sha256(b"trusted").hexdigest()

    def fail_request(_url: str, timeout: int) -> io.BytesIO:
        raise AssertionError("Existing verified file should be reused")

    monkeypatch.setattr("tools.fetch_dev_binaries.urllib.request.urlopen", fail_request)
    download_verified("https://example.invalid/file.bin", target, digest)
    assert target.read_bytes() == b"trusted"


def test_zip_rejects_path_traversal(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../outside.exe", b"bad")
    with pytest.raises(ValueError, match="Unexpected archive member"):
        extract_flat_zip(archive_path, tmp_path / "output")
    assert not (tmp_path / "outside.exe").exists()


def test_zip_preserves_native_license_notice(tmp_path: Path) -> None:
    archive_path = tmp_path / "native.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("whisper-cli.exe", b"native fixture")
        archive.writestr("LICENSE.txt", b"MIT notice fixture")
    extract_flat_zip(archive_path, tmp_path / "output")
    assert (tmp_path / "output/LICENSE.txt").read_bytes() == b"MIT notice fixture"


def test_selected_models_use_pm_approved_release_set() -> None:
    prefix = "https://github.com/dusty-corporation/dusty/releases/download/models-v1/"

    def entry(model_id: str, file_name: str) -> dict[str, object]:
        return {
            "id": model_id,
            "file_name": file_name,
            "url": prefix + file_name,
            "sha256": "a" * 64,
            "size_bytes": 1,
        }

    manifest = {
        "release_tag": "models-v1",
        "models": [
            entry("tiny-f16", "ggml-tiny.bin"),
            entry("small.en-f16", "ggml-small.en.bin"),
            entry("medium-f16", "ggml-medium.bin"),
        ],
        "vad": [entry("silero-vad", "ggml-silero-vad.bin")],
    }
    assert [item["id"] for item in selected_models(manifest, "models-v1")] == [
        "tiny-f16",
        "small.en-f16",
        "medium-f16",
        "silero-vad",
    ]
