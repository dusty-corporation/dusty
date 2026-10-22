"""Exercise output collision policies and restart state."""

from pathlib import Path

import pytest

from dusty.core import BatchOptions, Job, JobStatus, Segment, Transcript
from dusty.queue.outputs import OutputExistsError, write_outputs
from dusty.queue.storage import (
    clear_history,
    load_batch,
    load_settings,
    save_batch,
    save_settings,
)


def _transcript() -> Transcript:
    return Transcript((Segment(0, 0, 1, "Hello"),), "en", "transcribe", "tiny", "cpu", 1)


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
