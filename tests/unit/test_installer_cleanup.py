"""Uninstall cleanup preserves output content and refuses uncertain ownership."""

import json
from pathlib import Path

import pytest

from dusty.installer_cleanup import cleanup
from dusty.runtime_paths import RuntimePaths

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("remove_models", [False, True])
def test_cleanup_known_files_and_preserve_outputs(tmp_path, remove_models):
    root = tmp_path / "Dusty"
    root.mkdir()
    paths = RuntimePaths(tmp_path / "bin", root / "models", ROOT / "resources", root)
    outputs = tmp_path / "Transcripts"
    outputs.mkdir(parents=True)
    (outputs / "raw.json").write_text("user transcript")
    (root / "settings.json").write_text(
        json.dumps({"schema_version": 1, "output_dir": str(outputs)})
    )
    (root / "work/job").mkdir(parents=True)
    (root / "work/job/audio.wav").write_bytes(b"temporary")
    (root / "work/job/transcript.txt").write_text("preserve unknown file")
    (root / "logs").mkdir()
    (root / "logs/dusty.log").write_text("status=done")
    (root / "models").mkdir()
    model = root / "models/ggml-tiny.bin"
    model.write_bytes(b"model")
    # Unknown files cause a kept-data notice.
    assert not cleanup(paths, remove_models=remove_models)
    assert (outputs / "raw.json").read_text() == "user transcript"
    assert (root / "work/job/transcript.txt").exists()
    assert (root / "work/job/audio.wav").exists()  # Unknown work folder is not app-owned.
    assert not (root / "logs/dusty.log").exists()
    assert model.exists() is not remove_models


def test_cleanup_protects_internal_output_and_retains_metadata(tmp_path):
    root = tmp_path / "Dusty"
    outputs = root / "work/probe"
    outputs.mkdir(parents=True)
    (outputs / "raw.json").write_text("user transcript")
    (root / "settings.json").write_text(
        json.dumps({"schema_version": 1, "output_dir": str(outputs)})
    )
    paths = RuntimePaths(tmp_path, root / "models", ROOT / "resources", root)
    assert not cleanup(paths, remove_models=True)
    assert (outputs / "raw.json").read_text() == "user transcript"
    assert (root / "settings.json").exists()


def test_cleanup_removes_recognized_job_work_only(tmp_path):
    root = tmp_path / "Dusty"
    work = root / "work/7661d396-f8aa-4abf-bdd0-6292417a66b2"
    work.mkdir(parents=True)
    (work / "audio.wav").write_bytes(b"temporary")
    (work / "raw.json").write_text("temporary")
    paths = RuntimePaths(tmp_path, root / "models", ROOT / "resources", root)
    assert cleanup(paths, remove_models=False)
    assert not root.exists()


def test_cleanup_corrupt_settings_fails_closed(tmp_path):
    root = tmp_path / "Dusty"
    root.mkdir()
    (root / "settings.json").write_text("{broken")
    paths = RuntimePaths(tmp_path, root / "models", ROOT / "resources", root)
    assert not cleanup(paths, remove_models=True)
    assert (root / "settings.json").exists()


def test_cleanup_unknown_metadata_schema_is_preserved(tmp_path):
    root = tmp_path / "Dusty"
    root.mkdir()
    (root / "settings.json").write_text('{"unrecognized": true}')
    paths = RuntimePaths(tmp_path, root / "models", ROOT / "resources", root)
    assert not cleanup(paths, remove_models=True)
    assert (root / "settings.json").exists()
