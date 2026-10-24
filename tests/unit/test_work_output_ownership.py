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
def test_uncertain_work_preserved(tmp_path, damage):
    from dusty.privacy.logging import configure_logger

    configure_logger(tmp_path / "user")
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
    assert not cleanup_owned(owned.path, protected=set())
    assert audio.exists()
    log = (tmp_path / "user/logs/dusty.log").read_text(encoding="utf-8")
    assert "work_cleanup=preserved" in log
    assert str(owned.path) not in log
    assert "patient-secret" not in log


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
    paths = RuntimePaths(
        tmp_path / "install/bin", root / "models", ROOT / "resources", root, tmp_path / "install"
    )
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
    paths = RuntimePaths(
        tmp_path / "install/bin", root / "models", ROOT / "resources", root, tmp_path / "install"
    )
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


def test_installer_reports_damaged_model_without_removing_it(tmp_path):
    from dusty.installer_support import model_status

    models = tmp_path / "models"
    models.mkdir()
    damaged = models / "ggml-tiny.bin"
    damaged.write_bytes(b"damaged synthetic model")
    paths = RuntimePaths(tmp_path / "install/bin", models, ROOT / "resources", tmp_path / "user")
    assert model_status(paths)["tiny"] == "damaged"
    assert damaged.read_bytes() == b"damaged synthetic model"


@pytest.mark.parametrize("kind", ["junction", "symlink"])
def test_downloader_refuses_linked_destination_before_any_transfer(tmp_path, kind):
    import subprocess

    from dusty_fetch.downloader import Asset, Downloader, Exit, FetchError

    outside = tmp_path / "outside-models"
    outside.mkdir()
    sentinel = outside / "ggml-tiny.bin.part"
    sentinel.write_bytes(b"not disposable")
    link = tmp_path / "model-link"
    if kind == "junction":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)], check=True, capture_output=True
        )
    else:
        link.symlink_to(outside, target_is_directory=True)
    asset = Asset("tiny", "ggml-tiny.bin", "https://github.com/example/model", 3, "0" * 64)
    with pytest.raises(FetchError) as caught:
        Downloader().download(asset, link, lambda _: None)
    assert caught.value.code == Exit.IO
    assert sentinel.read_bytes() == b"not disposable"
    link.rmdir() if kind == "junction" else link.unlink()


def test_legacy_logs_output_folder_is_untouched_even_by_logging(tmp_path):
    from dusty.privacy.logging import configure_logger

    root = tmp_path / "user"
    logs = root / "logs"
    logs.mkdir(parents=True)
    sentinel = logs / "dusty.log"
    sentinel.write_text("user transcript")
    save_settings(root / "settings.json", {"schema_version": 1, "output_dir": str(logs)})
    before = {p.name: p.read_bytes() for p in logs.iterdir()}
    configure_logger(root).info("status=done")
    assert {p.name: p.read_bytes() for p in logs.iterdir()} == before


def test_development_outputs_can_be_siblings_of_native_staging(tmp_path):
    from dusty.runtime_paths import resolve_paths

    paths = resolve_paths(
        repo_root=tmp_path, frozen=False, environment={"LOCALAPPDATA": str(tmp_path / "local")}
    )
    assert not managed_destination(tmp_path / "build/offline-run/outputs", paths)
    assert managed_destination(tmp_path / "build/bin/cpu", paths)
    installed = resolve_paths(
        frozen=True,
        executable=tmp_path / "app/dusty/dusty.exe",
        environment={"LOCALAPPDATA": str(tmp_path / "local")},
    )
    assert managed_destination(tmp_path / "app/anywhere", installed)


@pytest.mark.parametrize("damage", ["missing", "changed"])
def test_recording_outputs_cannot_recreate_lost_ownership(tmp_path, damage):
    owned = OwnedWork(tmp_path / "user/work", "job")
    file = owned.path / "raw.json"
    file.write_text("preserve data")
    marker = owned.path / ".dusty-owned.json"
    if damage == "missing":
        marker.unlink()
    else:
        marker.write_text('{"purpose":"other"}')
    before = marker.read_bytes() if marker.exists() else None
    owned.record("raw.json")
    assert not owned.cleanup(tmp_path / "user")
    assert file.read_text() == "preserve data"
    assert (marker.read_bytes() if marker.exists() else None) == before


def test_record_cannot_adopt_a_changed_previously_owned_file(tmp_path):
    owned = OwnedWork(tmp_path / "user/work", "job")
    file = owned.path / "audio.wav"
    file.write_bytes(b"generated")
    owned.record("audio.wav")
    file.write_bytes(b"user replacement")
    owned.record("audio.wav")
    assert not owned.cleanup(tmp_path / "user")
    assert file.read_bytes() == b"user replacement"
