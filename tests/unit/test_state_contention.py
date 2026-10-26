"""Audit F-03: sharing violations are not corruption or output failures."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from dusty.queue import storage


def sharing_error():
    error = PermissionError("synthetic sharing conflict")
    error.winerror = 5
    return error


def test_reader_error_never_quarantines_valid_state(tmp_path, monkeypatch):
    file = tmp_path / "settings.json"
    file.write_text('{"schema_version":1}')
    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", lambda *a, **kw: (_ for _ in ()).throw(sharing_error()))
        with pytest.raises(OSError):
            storage.load_settings(file)
    assert file.exists()
    assert not list(tmp_path.glob("*.corrupt-*"))


def test_atomic_state_write_retries_transient_sharing_violation(tmp_path, monkeypatch):
    original = storage.os.replace
    attempts = []

    def replace(source, destination):
        attempts.append(1)
        if len(attempts) < 3:
            raise sharing_error()
        return original(source, destination)

    monkeypatch.setattr(storage.os, "replace", replace)
    file = tmp_path / "settings.json"
    storage.atomic_json(file, {"schema_version": 1})
    assert len(attempts) == 3
    assert json.loads(file.read_text()) == {"schema_version": 1}
    assert not list(tmp_path.glob("*.dusty-tmp"))


def test_persistent_state_write_failure_is_dedicated_and_preserves_previous(tmp_path, monkeypatch):
    file = tmp_path / "queue.json"
    file.write_bytes(b"previous complete state")
    monkeypatch.setattr(storage.os, "replace", lambda *a: (_ for _ in ()).throw(sharing_error()))
    with pytest.raises(storage.StateSaveError):
        storage.atomic_json(file, {"schema_version": 1})
    assert file.read_bytes() == b"previous complete state"
    assert not list(tmp_path.glob("*.dusty-tmp"))


def test_second_gui_process_signals_owner_and_lock_recovers(tmp_path):
    from dusty.platform.single_instance import GuiInstance

    first = GuiInstance(tmp_path)
    try:
        assert first.owner
        child = subprocess.run(
            [
                sys.executable,
                "-c",
                "from pathlib import Path; from dusty.platform.single_instance "
                "import GuiInstance; import sys; g=GuiInstance(Path(sys.argv[1])); "
                "print(g.owner); g.close()",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        assert child.stdout.strip() == "False"
        assert first.activation_requested()
        assert not first.activation_requested()
        other = GuiInstance(tmp_path / "other-profile")
        assert other.owner
        other.close()
    finally:
        first.close()
    replacement = GuiInstance(tmp_path)
    assert replacement.owner
    replacement.close()


def test_existing_gui_is_restored_when_activation_arrives(qtbot):
    from PySide6.QtWidgets import QWidget

    from dusty.platform.single_instance import activate_window

    window = QWidget()
    qtbot.addWidget(window)
    window.showMinimized()
    assert window.isMinimized()
    activate_window(window)
    assert window.isVisible() and not window.isMinimized()


def test_state_failure_during_job_never_reports_output_unwritable(tmp_path, monkeypatch):
    import dusty.queue.coordinator as coordinator
    from dusty.core import BatchOptions, FailureCode, Job, JobStatus
    from dusty.models import ModelRegistry, load_manifest
    from dusty.queue import Coordinator
    from dusty.runtime_paths import RuntimePaths

    root = Path(__file__).resolve().parents[2]
    paths = RuntimePaths(
        tmp_path / "bin", tmp_path / "models", root / "resources", tmp_path / "user"
    )
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    original = coordinator.save_batch
    attempts = []

    def save(*args):
        attempts.append(1)
        if len(attempts) > 1:
            raise storage.StateSaveError("synthetic state failure")
        original(*args)

    monkeypatch.setattr(coordinator, "save_batch", save)
    jobs = [Job(tmp_path / "one.wav"), Job(tmp_path / "two.wav")]
    Coordinator(paths, registry).run_batch(jobs, BatchOptions("tiny", tmp_path / "out"))
    assert jobs[0].failure == FailureCode.STATE_SAVE_FAILED
    assert jobs[1].status == JobStatus.QUEUED
    assert not list((paths.user_dir / "work").iterdir())
