"""Uninstall cleanup preserves output content and refuses uncertain ownership."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from dusty.installer_cleanup import cleanup
from dusty.runtime_paths import RuntimePaths

ROOT = Path(__file__).resolve().parents[2]


def test_uninstall_retains_sanitized_legacy_destination(tmp_path):
    from dusty.queue.storage import save_settings
    from dusty.work_area import sanitize_output

    root = tmp_path / "Dusty"
    folder = root / "models"
    folder.mkdir(parents=True)
    sentinel = folder / "ggml-tiny.bin"
    sentinel.write_bytes(b"synthetic private destination sentinel")
    paths = RuntimePaths(tmp_path, folder, ROOT / "resources", root)
    save_settings(root / "settings.json", {"schema_version": 1, "output_dir": str(folder)})
    assert sanitize_output(paths)
    assert not cleanup(paths, remove_models=True)
    assert sentinel.read_bytes() == b"synthetic private destination sentinel"
    assert (root / "settings.json").exists()


def test_uninstall_keeps_metadata_for_protected_installed_payload(tmp_path):
    from dusty.queue.storage import save_settings

    root = tmp_path / "user"
    install = tmp_path / "Programs/Dusty"
    resources = install / "resources"
    resources.mkdir(parents=True)
    sentinel = resources / "models.json"
    sentinel.write_text('{"private":"synthetic transcript"}')
    save_settings(
        root / "settings.json", {"schema_version": 1, "preserved_paths": [str(resources)]}
    )
    paths = replace(
        RuntimePaths(tmp_path, root / "models", ROOT / "resources", root), install_dir=install
    )
    assert not cleanup(paths, remove_models=False)
    assert (root / "settings.json").exists()
    assert sentinel.read_text() == '{"private":"synthetic transcript"}'


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
    from dusty.work_area import OwnedWork

    root = tmp_path / "Dusty"
    owned = OwnedWork(root / "work", "job")
    work = owned.path
    (work / "audio.wav").write_bytes(b"temporary")
    (work / "raw.json").write_text("temporary")
    owned.record("audio.wav", "raw.json")
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


def test_cleanup_preserves_empty_saved_output_folder(tmp_path):
    root = tmp_path / "Dusty"
    output = root / "custom-transcripts"
    output.mkdir(parents=True)
    (root / "settings.json").write_text(
        json.dumps({"schema_version": 1, "output_dir": str(output)})
    )
    paths = RuntimePaths(tmp_path, root / "models", ROOT / "resources", root)
    assert not cleanup(paths, remove_models=True)
    assert output.is_dir()
    assert (root / "settings.json").exists()
    assert not cleanup(paths, remove_models=True)
    assert output.is_dir()
