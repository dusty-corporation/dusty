"""Exercise output collision policies and restart state."""

import json
from pathlib import Path
from uuid import uuid4

import pytest

from dusty.core import BatchOptions, Job, JobStatus, Segment, Transcript
from dusty.queue import cleanup_orphaned_work
from dusty.queue.outputs import OutputExistsError, output_targets, write_outputs
from dusty.queue.storage import (
    clear_history,
    load_batch,
    load_settings,
    save_batch,
    save_settings,
)


def _transcript() -> Transcript:
    return Transcript((Segment(0, 0, 1, "Hello"),), "en", "transcribe", "tiny", "cpu", 1)


@pytest.mark.parametrize("relative", ["../elsewhere", "C:/elsewhere", "/elsewhere"])
def test_restored_relative_directory_must_stay_below_chosen_destination(tmp_path, relative):
    options = BatchOptions("tiny", tmp_path / "out", keep_structure=True)
    job = Job(tmp_path / "clip.wav", relative_dir=Path(relative))
    with pytest.raises(ValueError, match="relative output directory"):
        output_targets(job, options)
    saved = tmp_path / "queue.json"
    save_batch(saved, options, [job])
    assert load_batch(saved) is None
    assert len(list(tmp_path.glob("queue.json.corrupt-*"))) == 1
    assert not (tmp_path / "out").exists()


def test_output_collision_policies(tmp_path: Path) -> None:
    source = tmp_path / "clip.wav"
    source.write_bytes(b"original")
    job = Job(source)
    options = BatchOptions("tiny", tmp_path, formats=("txt", "json"), collision="skip")
    first = write_outputs(job, options, _transcript())
    assert [path.name for path in first] == ["clip.txt", "clip.json"]
    with pytest.raises(OutputExistsError):
        write_outputs(job, options, _transcript())
    both = BatchOptions("tiny", tmp_path, formats=("txt", "json"), collision="keep_both")
    second = write_outputs(job, both, _transcript())
    assert [path.name for path in second] == ["clip (1).txt", "clip (1).json"]
    assert source.read_bytes() == b"original"
    overwrite = BatchOptions("tiny", tmp_path, formats=("txt",), collision="overwrite")
    write_outputs(job, overwrite, _transcript())
    assert (tmp_path / "clip.txt").read_bytes() == b"Hello\r\n"


def test_same_folder_does_not_repeat_preserved_subfolders(tmp_path: Path) -> None:
    folder = tmp_path / "nested"
    folder.mkdir()
    source = folder / "clip.wav"
    source.write_bytes(b"original")
    job = Job(source, relative_dir=Path("nested"))
    options = BatchOptions(
        "tiny", tmp_path / "unused", formats=("txt",), same_folder=True, keep_structure=True
    )
    outputs = write_outputs(job, options, _transcript())
    assert outputs == [folder / "clip.txt"]
    assert source.read_bytes() == b"original"


def test_startup_cleans_preparation_work_but_keeps_unknown_directories(tmp_path: Path) -> None:
    from dusty.work_area import OwnedWork

    legacy = (str(uuid4()), "probe", "selftest", "unmanaged")
    for name in legacy:
        directory = tmp_path / name
        directory.mkdir()
        (directory / "temporary").write_bytes(b"generated fixture")
    for purpose in ("job", "probe", "selftest"):
        owned = OwnedWork(tmp_path, purpose)
        (owned.path / "audio.wav").write_bytes(b"generated")
        owned.record("audio.wav")
        del owned  # Simulate abandoned owners; live owners are tested separately.
    cleanup_orphaned_work(tmp_path)
    assert {path.name for path in tmp_path.iterdir()} == set(legacy)


def test_queue_recovers_unfinished_and_preserves_done(tmp_path: Path) -> None:
    path = tmp_path / "state/queue.json"
    output = tmp_path / "clip.txt"
    output.write_text("done", encoding="utf-8")
    done = Job(tmp_path / "clip.wav", status=JobStatus.DONE, outputs=[output])
    running = Job(tmp_path / "other.wav", status=JobStatus.TRANSCRIBING)
    options = BatchOptions("tiny", tmp_path, prompt="secret vocabulary")
    save_batch(path, options, [done, running])
    recovered = load_batch(path)
    assert recovered is not None
    loaded_options, jobs = recovered
    assert loaded_options.prompt == "secret vocabulary"
    assert jobs[0].status == JobStatus.DONE
    assert jobs[1].status == JobStatus.QUEUED
    clear_history(path)
    assert not path.exists()


def test_unknown_queue_schema_is_quarantined(tmp_path: Path) -> None:
    path = tmp_path / "queue.json"
    path.write_text('{"schema_version":99}', encoding="utf-8")
    assert load_batch(path) is None
    assert len(list(tmp_path.glob("queue.json.corrupt-*"))) == 1


def test_settings_are_atomic_and_unknown_schema_is_quarantined(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    assert load_settings(path) == {"schema_version": 1}
    save_settings(path, {"schema_version": 1, "backend_probe": {"ok": True}})
    assert load_settings(path)["backend_probe"]["ok"] is True
    path.write_text('{"schema_version":99}', encoding="utf-8")
    assert load_settings(path) == {"schema_version": 1}
    assert len(list(tmp_path.glob("settings.json.corrupt-*"))) == 1


@pytest.mark.parametrize(
    "preference", [{"threads": "fast"}, {"formats": "txt"}, {"collision": "always"}, {"vad": "no"}]
)
def test_invalid_known_settings_are_quarantined(tmp_path: Path, preference: dict) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"schema_version": 1, **preference}), encoding="utf-8")
    assert load_settings(path) == {"schema_version": 1}
    assert len(list(tmp_path.glob("settings.json.corrupt-*"))) == 1
    with pytest.raises(ValueError):
        save_settings(path, {"schema_version": 1, **preference})
    assert not path.exists()


def test_invalid_queue_options_and_missing_done_outputs_recover(tmp_path: Path) -> None:
    path = tmp_path / "queue.json"
    options = BatchOptions("tiny", tmp_path)
    save_batch(path, options, [Job(tmp_path / "clip.wav", status=JobStatus.DONE)])
    recovered = load_batch(path)
    assert recovered is not None and recovered[1][0].status == JobStatus.QUEUED
    data = json.loads(path.read_text(encoding="utf-8"))
    data["options"]["threads"] = "invalid"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert load_batch(path) is None
    assert len(list(tmp_path.glob("queue.json.corrupt-*"))) == 1


@pytest.mark.parametrize("cancelled", [False, True])
def test_collision_wait_is_not_processing_elapsed(tmp_path, monkeypatch, cancelled):
    import threading

    import dusty.queue.coordinator as module
    from dusty.models import ModelRegistry, load_manifest
    from dusty.runtime_paths import RuntimePaths, resolve_paths

    root = Path(__file__).resolve().parents[2]
    dev = resolve_paths(repo_root=root, frozen=False)
    paths = RuntimePaths(dev.bin_dir, dev.models_dir, dev.resources_dir, tmp_path / "user")
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    worker = module.Coordinator(paths, registry)
    job = Job(tmp_path / "clip.wav", elapsed_sec=99)
    output = tmp_path / "out"
    output.mkdir()
    (output / "clip.txt").write_text("Existing transcript")
    clock = [10.0]
    cancel = threading.Event()
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])

    def ask(_):
        assert job.elapsed_sec == 0
        clock[0] += 600
        if cancelled:
            cancel.set()
        return "keep_both"

    seen = []

    def process(current, options, signals, vulkan_ok, changed):
        current.status = JobStatus.PREFLIGHT
        changed()
        clock[0] += 2
        current.status = JobStatus.DONE
        changed()

    monkeypatch.setattr(worker, "_run_one", process)
    worker.run_batch(
        [job],
        BatchOptions("tiny", output, formats=("txt",)),
        cancel=cancel,
        on_collision=ask,
        on_change=lambda current: seen.append(current.elapsed_sec),
    )
    assert seen == ([0] if cancelled else [0, 2])
    assert job.status == (JobStatus.CANCELLED if cancelled else JobStatus.DONE)


@pytest.mark.parametrize("winerror", [2, 5, 32, 33])
def test_settings_read_retries_transient_replace_errors(tmp_path, monkeypatch, winerror):
    path = tmp_path / "settings.json"
    original = {
        "schema_version": 1,
        "prompt": "private canary",
        "output_dir": str(tmp_path / "chosen"),
    }
    save_settings(path, original)
    real_read = Path.read_text
    attempts = []

    def interrupted(item, *args, **kwargs):
        if item == path:
            attempts.append(1)
            if len(attempts) == 1:
                error = FileNotFoundError() if winerror == 2 else PermissionError()
                error.winerror = winerror
                raise error
        return real_read(item, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", interrupted)
    assert load_settings(path) == original
    assert len(attempts) == 2
    assert not list(tmp_path.glob("*.corrupt-*"))


def test_settings_missing_snapshot_rereads_before_saving(tmp_path):
    path = tmp_path / "settings.json"
    snapshot = load_settings(path)
    # A concurrent installer/state writer appears after the bounded missing read.
    original = {
        "schema_version": 1,
        "prompt": "keep private hints",
        "output_dir": str(tmp_path / "chosen"),
        "model_id": "small",
    }
    save_settings(path, original)
    snapshot["backend_probe"] = {"ok": False}
    save_settings(path, snapshot)
    assert load_settings(path) == {**original, "backend_probe": {"ok": False}}


def test_missing_settings_cannot_overwrite_a_writer_between_recheck_and_publish(
    tmp_path, monkeypatch
):
    import os

    path = tmp_path / "settings.json"
    snapshot = load_settings(path)
    snapshot["backend_probe"] = {"ok": False}
    original = {
        "schema_version": 1,
        "prompt": "preserve concurrent hints",
        "output_dir": str(tmp_path / "chosen"),
    }
    appeared = []
    replace, rename = os.replace, os.rename

    def race(operation):
        def publish(source, target):
            if Path(target) == path and not appeared:
                appeared.append(True)
                path.write_text(json.dumps(original), encoding="utf-8")
            return operation(source, target)

        return publish

    monkeypatch.setattr(os, "replace", race(replace))
    monkeypatch.setattr(os, "rename", race(rename))
    save_settings(path, snapshot)
    assert load_settings(path) == {**original, "backend_probe": {"ok": False}}
    assert not list(tmp_path.glob("*.dusty-tmp"))
