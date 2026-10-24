"""NN-7: a chosen transcript folder must survive app and installer cleanup."""

from pathlib import Path

import pytest

from dusty import selftest
from dusty.queue import cleanup_orphaned_work
from dusty.queue.storage import save_settings
from dusty.runtime_paths import RuntimePaths
from dusty.work_area import OwnedWork, cleanup_owned, managed_destination, sanitize_output

ROOT = Path(__file__).resolve().parents[2]


def saved_output(tmp_path: Path, name: str) -> tuple[Path, Path]:
    root = tmp_path / "Dusty"
    output = root / "work" / name
    output.mkdir(parents=True)
    transcript = output / "transcript.txt"
    transcript.write_text("Public synthetic preservation sentinel", encoding="utf-8")
    save_settings(root / "settings.json", {"schema_version": 1, "output_dir": str(output)})
    return root, transcript


@pytest.mark.parametrize("name", ["probe", "selftest"])
def test_startup_cleanup_preserves_saved_transcript_folder(tmp_path, name):
    root, transcript = saved_output(tmp_path, name)
    cleanup_orphaned_work(root / "work")
    assert transcript.exists(), "Startup deleted a file in the chosen transcript destination"


def test_installer_selftest_preserves_saved_transcript_folder(tmp_path, monkeypatch):
    root, transcript = saved_output(tmp_path, "selftest")
    paths = RuntimePaths(tmp_path / "bin", root / "models", ROOT / "resources", root)

    def unavailable_model(*args):
        raise ValueError("Synthetic unavailable model; no native process is launched")

    monkeypatch.setattr(selftest, "ModelRegistry", unavailable_model)
    assert selftest.run_selftest(paths, "tiny", backend="cpu", once=True) == "SELFTEST_FAILED_CPU"
    assert transcript.exists(), "Installer self-test deleted a chosen transcript destination"


@pytest.mark.parametrize("damage", ["missing", "unreadable", "mismatch", "unknown", "changed"])
def test_uncertain_work_preserved(tmp_path, damage, caplog):
    owned = OwnedWork(tmp_path / "work", "job")
    audio = owned.path / "audio.wav"
    audio.write_bytes(b"generated")
    owned.record("audio.wav")
    marker = owned.path / ".dusty-owned.json"
    if damage == "missing":
        marker.unlink()
    elif damage == "unreadable":
        marker.write_text("{broken")
    elif damage == "mismatch":
        marker.write_text(marker.read_text().replace('"purpose": "job"', '"purpose": "other"'))
    elif damage == "unknown":
        (owned.path / "patient-secret.txt").write_text("preserve")
    else:
        audio.write_bytes(b"user replacement")
    with caplog.at_level("INFO", logger="dusty"):
        assert not cleanup_owned(owned.path, protected=set())
    assert audio.exists()
    assert "work_cleanup=preserved" in caplog.text
    assert str(owned.path) not in caplog.text
    assert "patient-secret" not in caplog.text


@pytest.mark.parametrize("kind", ["junction", "symlink"])
def test_linked_work_never_deletes_external_target(tmp_path, kind):
    import subprocess

    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "keep.txt"
    sentinel.write_text("user data")
    owned = OwnedWork(tmp_path / "work", "job")
    link = owned.path / "linked"
    if kind == "junction":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)], check=True, capture_output=True
        )
    else:
        link.symlink_to(outside, target_is_directory=True)
    assert not cleanup_owned(owned.path, protected=set())
    assert sentinel.read_text() == "user data"
    assert not cleanup_owned(link, protected=set())
    assert sentinel.exists()
    # Remove the link itself only, so pytest's temp cleanup cannot traverse it.
    link.rmdir() if kind == "junction" else link.unlink()


def test_legacy_destination_cleared_once_but_preserved_across_restarts(tmp_path):
    from dusty.queue.storage import load_settings

    root, transcript = saved_output(tmp_path, "selftest")
    paths = RuntimePaths(tmp_path / "install/bin", root / "models", ROOT / "resources", root)
    assert sanitize_output(paths)
    settings = load_settings(root / "settings.json")
    assert "output_dir" not in settings
    assert settings["managed_folder_notice"] is True
    assert str(transcript.parent.resolve()) in settings["preserved_paths"]
    assert not sanitize_output(paths)
    cleanup_orphaned_work(root / "work")
    assert transcript.exists()


@pytest.mark.parametrize("area", ["work", "models", "state", "logs", "install"])
def test_managed_destinations_and_aliases_rejected(tmp_path, area):
    root = tmp_path / "user"
    paths = RuntimePaths(tmp_path / "install/bin", root / "models", ROOT / "resources", root)
    base = tmp_path / "install" if area == "install" else root / area
    base.mkdir(parents=True)
    assert managed_destination(base / "nested/clip.wav", paths)
    assert not managed_destination(tmp_path / "outputs", paths)
    alias = tmp_path / "alias"
    alias.symlink_to(base, target_is_directory=True)
    assert managed_destination(alias / "clip.wav", paths)
    alias.unlink()


def test_preexisting_atomic_temporary_is_not_deleted(tmp_path):
    from dusty.queue.storage import atomic_json

    file = tmp_path / "settings.json"
    sentinel = tmp_path / "settings.json.dusty-tmp"
    sentinel.write_text("user data")
    atomic_json(file, {"schema_version": 1})
    assert sentinel.read_text() == "user data"


def test_marked_work_with_protected_known_file_is_preserved(tmp_path):
    owned = OwnedWork(tmp_path / "user/work", "job")
    file = owned.path / "audio.wav"
    file.write_bytes(b"known data")
    owned.record("audio.wav")
    assert not cleanup_owned(owned.path, protected={file.resolve()})
    assert file.exists()
