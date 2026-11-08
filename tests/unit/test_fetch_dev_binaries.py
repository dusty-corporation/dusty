"""Verify that development assets are pinned and safely unpacked."""

import hashlib
import io
import stat
import sys
import zipfile
from pathlib import Path

import pytest

from tools.fetch_dev_binaries import (
    MAC_ENGINE_ASSETS,
    download_verified,
    extract_flat_zip,
    extract_mac_component,
    selected_models,
)


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


def test_recommended_models_are_an_explicit_optional_pinned_set() -> None:
    import json

    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((root / "resources/models.json").read_text(encoding="utf-8"))
    for entry in manifest["models"]:
        entry["id"] = entry["release_model_id"]
    ids = {item["id"] for item in selected_models(manifest, "models-v1", recommended=True)}
    assert {"small-f16", "large-v3-turbo-q8_0"} <= ids
    assert "large-v3-turbo-q8_0" not in {
        item["id"] for item in selected_models(manifest, "models-v1")
    }


def _mac_archive(
    path: Path, files: dict[str, bytes], *, sums: dict[str, bytes] | None = None
) -> Path:
    """A Mac engine archive like native-macos.yml makes: sums, metadata, package files."""
    listed = files if sums is None else sums
    lines = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in listed.items()
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("whisper-cpu/SHA256SUMS.txt", lines)
        archive.writestr("whisper-cpu/minimum-os.txt", "whisper-cli: 13.3\n")
        archive.mkdir("whisper-cpu/package")
        for name, data in files.items():
            info = zipfile.ZipInfo(f"whisper-cpu/package/{name}")
            info.external_attr = (stat.S_IFREG | (0o755 if name == "whisper-cli" else 0o644)) << 16
            archive.writestr(info, data)
    return path


def test_mac_engine_assets_cover_both_whisper_builds_and_ffmpeg() -> None:
    assert {component for _, component in MAC_ENGINE_ASSETS.values()} == {
        "whisper-cpu",
        "whisper-metal",
        "ffmpeg",
    }


def test_mac_component_unpacks_and_matches_its_sums(tmp_path: Path) -> None:
    files = {"whisper-cli": b"program", "libwhisper.1.dylib": b"library", "LICENSE.txt": b"MIT"}
    archive = _mac_archive(tmp_path / "cpu.zip", files)
    target = extract_mac_component(archive, "whisper-cpu", tmp_path / "native-v3")
    assert {path.name for path in (target / "package").iterdir()} == set(files)
    assert (target / "package/libwhisper.1.dylib").read_bytes() == b"library"
    assert (target / "minimum-os.txt").is_file()
    assert not list(tmp_path.rglob("*.part"))


@pytest.mark.skipif(sys.platform == "win32", reason="Windows does not store POSIX execute bits")
def test_mac_component_keeps_execute_bits(tmp_path: Path) -> None:
    files = {"whisper-cli": b"program", "LICENSE.txt": b"MIT"}
    target = extract_mac_component(
        _mac_archive(tmp_path / "cpu.zip", files), "whisper-cpu", tmp_path / "native-v3"
    )
    assert (target / "package/whisper-cli").stat().st_mode & 0o777 == 0o755
    assert (target / "package/LICENSE.txt").stat().st_mode & 0o777 == 0o644


@pytest.mark.parametrize(
    "member",
    [
        "../outside",
        "whisper-metal/package/whisper-cli",
        "whisper-cpu/package/sub/x",
        "whisper-cpu/notes.md",
    ],
)
def test_mac_component_rejects_unexpected_members(tmp_path: Path, member: str) -> None:
    archive = _mac_archive(tmp_path / "cpu.zip", {"whisper-cli": b"program"})
    with zipfile.ZipFile(archive, "a") as stream:
        stream.writestr(member, b"bad")
    with pytest.raises(ValueError, match="Unexpected archive member"):
        extract_mac_component(archive, "whisper-cpu", tmp_path / "native-v3")
    assert not (tmp_path / "outside").exists()
    assert not (tmp_path / "native-v3/whisper-cpu").exists()


def test_mac_component_rejects_links(tmp_path: Path) -> None:
    archive = _mac_archive(tmp_path / "cpu.zip", {"whisper-cli": b"program"})
    with zipfile.ZipFile(archive, "a") as stream:
        info = zipfile.ZipInfo("whisper-cpu/package/libggml.dylib")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        stream.writestr(info, b"/usr/local/lib/libggml.dylib")
    with pytest.raises(ValueError, match="Unexpected archive member"):
        extract_mac_component(archive, "whisper-cpu", tmp_path / "native-v3")


def test_mac_component_rejects_changed_or_missing_files(tmp_path: Path) -> None:
    changed = _mac_archive(
        tmp_path / "changed.zip", {"whisper-cli": b"tampered"}, sums={"whisper-cli": b"program"}
    )
    with pytest.raises(ValueError, match="does not match its SHA256SUMS"):
        extract_mac_component(changed, "whisper-cpu", tmp_path / "a")
    missing = _mac_archive(
        tmp_path / "missing.zip",
        {"whisper-cli": b"program"},
        sums={"whisper-cli": b"program", "libwhisper.1.dylib": b"library"},
    )
    with pytest.raises(ValueError, match="package does not match"):
        extract_mac_component(missing, "whisper-cpu", tmp_path / "b")


def test_mac_engine_pins_are_complete_and_separate_from_windows() -> None:
    import tomllib

    root = Path(__file__).resolve().parents[2]
    pins = tomllib.loads((root / "native/versions.toml").read_text(encoding="utf-8"))
    mac, windows = pins["engine_release_macos"], pins["engine_release"]
    for key, _ in MAC_ENGINE_ASSETS.values():
        assert len(mac[key]) == 64 and int(mac[key], 16) >= 0
    # Older pin tools rewrite Windows keys by name, so the Mac section shares none.
    assert not (set(mac) - {"tag"}) & set(windows)
