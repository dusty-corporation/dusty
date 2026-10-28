"""A crashed job must not strand its converted audio or remove live work."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dusty.installer_cleanup import cleanup
from dusty.queue import cleanup_orphaned_work
from dusty.runtime_paths import RuntimePaths
from dusty.work_area import cleanup_owned

ROOT = Path(__file__).resolve().parents[2]


def crashed_job(user_dir: Path, *, recorded: bool) -> Path:
    work_root = user_dir / "work"
    script = (
        "import os,sys; from pathlib import Path; from dusty.work_area import OwnedWork; "
        "w=OwnedWork(Path(sys.argv[1]),'job'); "
        "(w.path/'audio.wav').write_bytes(b'public synthetic PCM'); "
        + ("w.record('audio.wav'); " if recorded else "")
        + "os._exit(0)"
    )
    subprocess.run(
        [sys._base_executable, "-c", script, str(work_root)],
        check=True,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )
    return next(work_root.iterdir())


def test_startup_removes_crashed_job_before_audio_inventory_was_written(tmp_path):
    user_dir = tmp_path / "Dusty"
    directory = crashed_job(user_dir, recorded=False)
    assert (directory / "audio.wav").exists()
    cleanup_orphaned_work(user_dir / "work")
    assert not directory.exists()


def test_uninstall_removes_crashed_job_before_audio_inventory_was_written(tmp_path):
    user_dir = tmp_path / "Dusty"
    directory = crashed_job(user_dir, recorded=False)
    paths = RuntimePaths(tmp_path / "bin", user_dir / "models", ROOT / "resources", user_dir)
    assert cleanup(paths, remove_models=True)
    assert not directory.exists()


def test_startup_and_uninstall_keep_a_live_job_lock(tmp_path):
    from dusty.work_area import OwnedWork

    user_dir = tmp_path / "Dusty"
    owned = OwnedWork(user_dir / "work", "job")
    audio = owned.path / "audio.wav"
    audio.write_bytes(b"public synthetic PCM")
    paths = RuntimePaths(tmp_path / "bin", user_dir / "models", ROOT / "resources", user_dir)
    try:
        cleanup_orphaned_work(user_dir / "work")
        assert audio.exists()
        assert not cleanup(paths, remove_models=True)
        assert audio.exists()
    finally:
        owned._lease.close()


def test_startup_recovers_after_crash_during_prior_cleanup(tmp_path):
    user_dir = tmp_path / "Dusty"
    directory = crashed_job(user_dir, recorded=True)
    (directory / "audio.wav").unlink()
    cleanup_orphaned_work(user_dir / "work")
    assert not directory.exists()


@pytest.mark.parametrize("route", ["startup", "uninstall"])
def test_zero_filled_crash_marker_and_lock_recovered(tmp_path, route):
    user_dir = tmp_path / "Dusty"
    directory = crashed_job(user_dir, recorded=True)
    marker = directory / ".dusty-owned.json"
    assert len(marker.read_bytes()) == 270
    marker.write_bytes(bytes(270))
    (directory / ".dusty-active.lock").write_bytes(bytes(1))
    paths = RuntimePaths(tmp_path / "bin", user_dir / "models", ROOT / "resources", user_dir)
    if route == "startup":
        cleanup_orphaned_work(user_dir / "work")
    else:
        assert cleanup(paths, remove_models=True)
    assert not directory.exists()


def test_recorded_marker_recovers_zero_filled_lock(tmp_path):
    user_dir = tmp_path / "Dusty"
    directory = crashed_job(user_dir, recorded=True)
    (directory / ".dusty-active.lock").write_bytes(bytes(1))
    cleanup_orphaned_work(user_dir / "work")
    assert not directory.exists()


@pytest.mark.parametrize("route", ["startup", "uninstall"])
def test_valid_marker_without_lock_recovers_v100_cleanup_crash(tmp_path, route):
    user_dir = tmp_path / "Dusty"
    directory = crashed_job(user_dir, recorded=True)
    (directory / ".dusty-active.lock").unlink()
    paths = RuntimePaths(tmp_path / "bin", user_dir / "models", ROOT / "resources", user_dir)
    if route == "startup":
        cleanup_orphaned_work(user_dir / "work")
    else:
        assert cleanup(paths, remove_models=True)
    assert not directory.exists()


def test_zero_marker_in_another_folder_named_work_is_preserved(tmp_path):
    user_dir = tmp_path / "Dusty"
    managed_root = user_dir / "work"
    directory = crashed_job(user_dir, recorded=True)
    marker = directory / ".dusty-owned.json"
    marker.write_bytes(bytes(len(marker.read_bytes())))
    outside = tmp_path / "unrelated" / "work" / directory.name
    shutil.copytree(directory, outside)
    assert not cleanup_owned(outside, protected=set(), work_root=managed_root)
    assert (outside / "audio.wav").exists()


def test_zero_marker_without_lock_is_still_preserved(tmp_path):
    user_dir = tmp_path / "Dusty"
    directory = crashed_job(user_dir, recorded=True)
    marker = directory / ".dusty-owned.json"
    marker.write_bytes(bytes(len(marker.read_bytes())))
    (directory / ".dusty-active.lock").unlink()
    cleanup_orphaned_work(user_dir / "work")
    assert (directory / "audio.wav").exists()


@pytest.mark.parametrize("damage", ["unknown", "wrong_lock_hash"])
def test_missing_lock_does_not_override_other_ownership_checks(tmp_path, damage):
    import json

    user_dir = tmp_path / "Dusty"
    directory = crashed_job(user_dir, recorded=True)
    lease = directory / ".dusty-active.lock"
    lease.unlink()
    if damage == "unknown":
        (directory / "unrecognized.txt").write_bytes(b"private sentinel")
    else:
        marker = directory / ".dusty-owned.json"
        data = json.loads(marker.read_text(encoding="utf-8"))
        data["files"][".dusty-active.lock"] = "0" * 64
        marker.write_text(json.dumps(data), encoding="utf-8")
    cleanup_orphaned_work(user_dir / "work")
    assert (directory / "audio.wav").exists()
    if damage == "wrong_lock_hash":
        assert not lease.exists()


@pytest.mark.parametrize("damage", ["garbage", "extra", "held"])
def test_zero_marker_never_bypasses_other_safety_guards(tmp_path, damage):
    from dusty.work_area import OwnedWork

    user_dir = tmp_path / "Dusty"
    owned = OwnedWork(user_dir / "work", "job")
    directory = owned.path
    (directory / "audio.wav").write_bytes(b"public synthetic PCM")
    marker = directory / ".dusty-owned.json"
    marker.write_bytes(bytes(len(marker.read_bytes())))
    if damage == "garbage":
        marker.write_bytes(b"not valid ownership")
    elif damage == "extra":
        (directory / "unknown.txt").write_bytes(b"private sentinel")
    else:
        cleanup_orphaned_work(user_dir / "work")
        assert (directory / "audio.wav").exists()
    owned._lease.close()
    cleanup_orphaned_work(user_dir / "work")
    if damage == "held":
        # A later startup may remove a formerly live but now abandoned job.
        assert not directory.exists()
    else:
        assert (directory / "audio.wav").exists()


def test_marker_update_is_atomic_and_durable(tmp_path, monkeypatch):
    import dusty.work_area as work_area
    from dusty.work_area import OwnedWork

    user_dir = tmp_path / "Dusty"
    syncs = 0
    real_fsync = os.fsync

    def counting_fsync(fd):
        nonlocal syncs
        syncs += 1
        real_fsync(fd)

    monkeypatch.setattr(work_area.os, "fsync", counting_fsync)
    owned = OwnedWork(user_dir / "work", "job")
    marker = owned.path / ".dusty-owned.json"
    initial = marker.read_bytes()
    (owned.path / "audio.wav").write_bytes(b"public synthetic PCM")

    def interrupted_replace(source, destination):
        raise OSError("synthetic interruption before atomic rename")

    monkeypatch.setattr(work_area.os, "replace", interrupted_replace)
    owned.record("audio.wav")
    assert marker.read_bytes() == initial
    assert syncs >= 3  # Lock, initial marker and updated marker were flushed.
    owned._lease.close()
    cleanup_orphaned_work(user_dir / "work")
    assert not owned.path.exists()


def test_uninstall_kept_data_message_names_its_location():
    from dusty.app.messages import INSTALLER

    assert "%LOCALAPPDATA%\\Dusty" in INSTALLER["CleanupKept"]
