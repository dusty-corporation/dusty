"""The macOS development staging tool verifies hashes and never overwrites."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools import stage_macos_dev_bin as stage

ROOT = Path(__file__).resolve().parents[2]
mac_only = pytest.mark.skipif(sys.platform != "darwin", reason="Stages Mach-O binaries")
posix_exec_bits = pytest.mark.skipif(
    sys.platform != "darwin", reason="checks POSIX execute bits, which Windows does not store"
)
real_sources = pytest.mark.skipif(
    sys.platform != "darwin"
    or not (stage.DEFAULT_SOURCE / "mac0-native/metal/bin/whisper-cli").is_file()
    or not (stage.DEFAULT_SOURCE / "macos-arm64/runtime-v1/Contents/Helpers/ffmpeg").is_file(),
    reason="Local pinned Mac build outputs are not present",
)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _catalog(tmp_path: Path, tiny: bytes, vad: bytes) -> Path:
    catalog = tmp_path / "models.json"
    catalog.write_text(
        json.dumps(
            {
                "models": [
                    {
                        "id": "tiny",
                        "file_name": "ggml-tiny.bin",
                        "size_bytes": len(tiny),
                        "sha256": _digest(tiny),
                    }
                ],
                "vad": [
                    {
                        "file_name": "ggml-silero-vad.bin",
                        "size_bytes": len(vad),
                        "sha256": _digest(vad),
                    }
                ],
            }
        )
    )
    return catalog


def test_refuses_non_empty_or_linked_targets(tmp_path):
    full = tmp_path / "full"
    full.mkdir()
    (full / "keep.txt").write_text("user data")
    with pytest.raises(stage.StageError, match="non-empty"):
        stage._check_target(full)
    link = tmp_path / "link"
    link.symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    with pytest.raises(stage.StageError, match="plain directory"):
        stage._check_target(link)
    (tmp_path / "empty").mkdir()
    stage._check_target(tmp_path / "empty")
    stage._check_target(tmp_path / "absent")
    assert (full / "keep.txt").read_text() == "user data"


def test_models_are_verified_against_the_catalog(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "ggml-tiny.bin").write_bytes(b"tiny model")
    (source / "ggml-silero-vad.bin").write_bytes(b"vad model")
    catalog = _catalog(tmp_path, b"tiny model", b"vad model")
    entries = stage.stage_models(source, tmp_path / "models", catalog)
    assert [entry["path"] for entry in entries] == ["ggml-tiny.bin", "ggml-silero-vad.bin"]
    assert (tmp_path / "models/ggml-tiny.bin").read_bytes() == b"tiny model"
    (source / "ggml-tiny.bin").write_bytes(b"tampered!!")
    with pytest.raises(stage.StageError, match="does not match"):
        stage.stage_models(source, tmp_path / "models2", catalog)


@posix_exec_bits
def test_ffmpeg_is_verified_against_the_runtime_manifest(tmp_path):
    contents = tmp_path / "build/macos-arm64/runtime-v1/Contents"
    (contents / "Helpers").mkdir(parents=True)
    (contents / "Resources").mkdir()
    artifacts = []
    for role in ("ffmpeg", "ffprobe"):
        data = f"{role} program".encode()
        (contents / "Helpers" / role).write_bytes(data)
        artifacts.append(
            {
                "role": role,
                "path": f"Helpers/{role}",
                "sha256": _digest(data),
                "size_bytes": len(data),
            }
        )
    (contents / "Resources/native-runtime-v1.json").write_text(json.dumps({"artifacts": artifacts}))
    entries = stage.stage_ffmpeg(tmp_path / "build", tmp_path / "bin")
    assert [entry["path"] for entry in entries] == ["ffmpeg/ffmpeg", "ffmpeg/ffprobe"]
    assert (tmp_path / "bin/ffmpeg/ffprobe").stat().st_mode & 0o111
    (contents / "Helpers/ffprobe").write_bytes(b"ffprobe changed")
    with pytest.raises(stage.StageError, match="ffprobe does not match"):
        stage.stage_ffmpeg(tmp_path / "build", tmp_path / "bin2")


def test_missing_lifeline_source_is_skipped_with_a_note(tmp_path, capsys):
    assert stage.stage_lifeline(tmp_path / "absent", None, tmp_path / "bin") == []
    assert "lifeline/ was not staged" in capsys.readouterr().out
    assert not (tmp_path / "bin/lifeline").exists()


@mac_only
def test_lifeline_source_is_built_into_the_expected_path(tmp_path):
    source = tmp_path / "lifeline"
    source.mkdir()
    (source / "main.c").write_text("int main(void) { return 7; }\n")
    entries = stage.stage_lifeline(source, None, tmp_path / "bin")
    program = tmp_path / "bin/lifeline/dusty-lifeline"
    assert entries[0]["path"] == "lifeline/dusty-lifeline" and entries[0]["built"]
    assert subprocess.run([str(program)], check=False).returncode == 7


@real_sources
def test_real_stage_is_self_contained_and_refuses_rerun(tmp_path):
    out, models = tmp_path / "bin", tmp_path / "models"
    manifest = stage.stage(out, models, lifeline_source=tmp_path / "no-lifeline")
    paths = {entry["path"] for entry in manifest["bin_files"]}
    assert {"ffmpeg/ffmpeg", "ffmpeg/ffprobe", "cpu/whisper-cli", "metal/whisper-cli"} <= paths
    assert "metal/libggml-metal.0.dylib" in paths and "cpu/libggml-metal.0.dylib" not in paths
    for entry in manifest["bin_files"]:
        file = out / entry["path"]
        assert not file.is_symlink() and stage.sha256(file) == entry["sha256"]
    for backend in ("cpu", "metal"):
        program = out / backend / "whisper-cli"
        assert stage.rpaths(program) == ["@loader_path"]
        assert all((out / backend / name).is_file() for name in stage.rpath_dependencies(program))
        subprocess.run(["/usr/bin/codesign", "--verify", str(program)], check=True)
    assert sorted(path.name for path in models.iterdir()) == [
        "ggml-silero-vad.bin",
        "ggml-tiny.bin",
    ]
    assert json.loads((out / "dev-stage-manifest.json").read_text()) == manifest
    with pytest.raises(stage.StageError, match="non-empty"):
        stage.stage(out, tmp_path / "models-again")
    assert not list(tmp_path.glob("*.partial-*"))


def test_sums_file_parsing_rejects_malformed_lines(tmp_path):
    sums = tmp_path / "SHA256SUMS.txt"
    sums.write_text(f"{'a' * 64}  whisper-cli\n{'b' * 64} *libggml.0.dylib\n\n")
    assert stage.read_sums(sums) == {"whisper-cli": "a" * 64, "libggml.0.dylib": "b" * 64}
    sums.write_text("not-a-hash  whisper-cli\n")
    with pytest.raises(stage.StageError, match="Invalid hash"):
        stage.read_sums(sums)


@real_sources
def test_package_hash_mismatch_is_refused(tmp_path):
    source_bin, sums, origin = stage.whisper_sources(stage.DEFAULT_SOURCE, "cpu")
    if sums is None:
        pytest.skip(f"{origin} has no SHA256SUMS.txt")
    tampered = dict(sums, **{"whisper-cli": "0" * 64})
    with pytest.raises(stage.StageError, match="does not match SHA256SUMS"):
        stage.stage_whisper(source_bin, tmp_path / "bin", "cpu", tampered)


def _runtime_v1(build: Path) -> None:
    contents = build / "macos-arm64/runtime-v1/Contents"
    (contents / "Helpers").mkdir(parents=True)
    (contents / "Resources").mkdir()
    artifacts = []
    for role in ("ffmpeg", "ffprobe"):
        data = f"runtime-v1 {role}".encode()
        (contents / "Helpers" / role).write_bytes(data)
        artifacts.append(
            {
                "role": role,
                "path": f"Helpers/{role}",
                "sha256": _digest(data),
                "size_bytes": len(data),
            }
        )
    (contents / "Resources/native-runtime-v1.json").write_text(json.dumps({"artifacts": artifacts}))


def _package(folder: Path, files: dict[str, bytes]) -> None:
    (folder / "package").mkdir(parents=True)
    for name, data in files.items():
        (folder / "package" / name).write_bytes(data)
    (folder / "SHA256SUMS.txt").write_text(
        "".join(f"{_digest(data)}  {name}\n" for name, data in files.items())
    )


@posix_exec_bits
def test_native_v3_ffmpeg_is_preferred_and_verified(tmp_path):
    build = tmp_path / "build"
    _runtime_v1(build)
    v3 = build / "macos-arm64/native-v3/ffmpeg"
    _package(v3, {"ffmpeg": b"v3 ffmpeg", "ffprobe": b"v3 ffprobe", "LICENSE.txt": b"LGPL"})
    entries = stage.stage_ffmpeg(build, tmp_path / "bin")
    assert [entry["trust"] for entry in entries] == ["native-v3 SHA256SUMS.txt"] * 2
    assert (tmp_path / "bin/ffmpeg/ffmpeg").read_bytes() == b"v3 ffmpeg"
    assert (tmp_path / "bin/ffmpeg/ffprobe").stat().st_mode & 0o111
    (v3 / "package/ffprobe").write_bytes(b"v3 ffprobe changed")
    with pytest.raises(stage.StageError, match="ffprobe does not match SHA256SUMS"):
        stage.stage_ffmpeg(build, tmp_path / "bin2")
    (v3 / "SHA256SUMS.txt").unlink()
    with pytest.raises(stage.StageError, match="SHA256SUMS.txt is missing"):
        stage.stage_ffmpeg(build, tmp_path / "bin3")


def test_runtime_v1_ffmpeg_is_the_fallback_without_native_v3(tmp_path):
    build = tmp_path / "build"
    _runtime_v1(build)
    entries = stage.stage_ffmpeg(build, tmp_path / "bin")
    assert [entry["trust"] for entry in entries] == ["native-runtime-v1.json"] * 2
    assert (tmp_path / "bin/ffmpeg/ffmpeg").read_bytes() == b"runtime-v1 ffmpeg"


def test_whisper_sources_prefer_native_v3_then_v2_then_mac0(tmp_path):
    build = tmp_path / "build"
    v2 = build / "macos-arm64/native-v2/whisper-cpu"
    v3 = build / "macos-arm64/native-v3/whisper-cpu"
    _package(v2, {"whisper-cli": b"v2"})
    _package(v3, {"whisper-cli": b"v3"})
    source, sums, origin = stage.whisper_sources(build, "cpu")
    assert (source, origin) == (v3 / "package", "native-v3")
    assert sums == {"whisper-cli": _digest(b"v3")}
    (v3 / "SHA256SUMS.txt").unlink()
    with pytest.raises(stage.StageError, match="SHA256SUMS.txt is missing"):
        stage.whisper_sources(build, "cpu")
    (v3 / "package/whisper-cli").unlink()
    source, sums, origin = stage.whisper_sources(build, "cpu")
    assert (source, origin, sums) == (v2 / "package", "native-v2", {"whisper-cli": _digest(b"v2")})
    (v2 / "package/whisper-cli").unlink()
    assert stage.whisper_sources(build, "cpu") == (
        build / "mac0-native/cpu/bin",
        None,
        "mac0-native",
    )


@real_sources
def test_bin_only_stage_leaves_fetched_models_alone(tmp_path):
    out, models = tmp_path / "bin", tmp_path / "models"
    models.mkdir()
    (models / "ggml-tiny.bin").write_bytes(b"fetched and verified elsewhere")
    manifest = stage.stage(
        out, models, lifeline_source=tmp_path / "no-lifeline", stage_model_files=False
    )
    assert manifest["model_files"] == []
    assert (out / "cpu/whisper-cli").is_file() and (out / "ffmpeg/ffprobe").is_file()
    assert [path.name for path in models.iterdir()] == ["ggml-tiny.bin"]
    assert (models / "ggml-tiny.bin").read_bytes() == b"fetched and verified elsewhere"
    assert not list(tmp_path.glob("*.partial-*"))
