"""A recording that loses data while it is decoded is never reported done (D-MAC-023).

The native process runner is replaced at the shim functions in dusty.engine.ffmpeg
and dusty.engine.whisper, as in test_coordinator_collisions.py. The fake FFmpeg
emits the real stderr line seen when the drive holding the input is ejected, or
removes or replaces the source while it decodes, and always exits 0.
"""

import json
import os
import shutil
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import pytest

from dusty.core import BatchOptions, FailureCode, Job, JobStatus
from dusty.engine import binaries, ffmpeg, whisper
from dusty.models import load_manifest
from dusty.queue import Coordinator
from dusty.runtime_paths import RuntimePaths

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/engine"
CPU_LINES = (FIXTURES / "mac-cpu-full-stderr.txt").read_text().splitlines()
MANIFEST = load_manifest(ROOT / "resources/models.json")
EJECTED = "[in#0/mp3 @ 0x8a901c000] Error during demuxing: Input/output error"
DAMAGED = "[in#0/mp3 @ 0x8a901c000] Error during demuxing: Invalid data found when processing input"


class FakeNative:
    """Answer ffprobe, ffmpeg and whisper-cli calls without starting processes."""

    def __init__(self, during_decode: Callable[[Path, Callable[[str], None]], None]) -> None:
        self.during_decode = during_decode
        self.calls: list[str] = []

    def run_ffmpeg(self, args, **kwargs):
        if Path(args[0]).name.startswith("ffprobe"):
            self.calls.append("ffprobe")
            kwargs["on_stdout"](
                json.dumps({"streams": [{"codec_type": "audio", "duration": "11.0"}]})
            )
        else:
            self.calls.append("ffmpeg")
            Path(args[-1]).write_bytes(b"RIFF fake decoded audio")
            source = Path(args[args.index("-i") + 1])
            if source.name == "clip.mp3":
                self.during_decode(source, kwargs["on_stderr"])
        return SimpleNamespace(cancelled=False, exit_code=0, elapsed_sec=0.01)

    def run_whisper(self, args, **kwargs):
        self.calls.append("whisper")
        for line in CPU_LINES:
            kwargs["on_stderr"](line)
        shutil.copyfile(FIXTURES / "sample-output.json", args[args.index("-of") + 1] + ".json")
        return SimpleNamespace(cancelled=False, exit_code=0, elapsed_sec=0.5)


class Registry:
    """The real bundled catalog; model files are never opened by the fakes."""

    def __init__(self, folder: Path):
        self.folder = folder
        self.manifest = MANIFEST

    def model_path(self, model_id: str) -> Path:
        return self.folder / MANIFEST.models[model_id].file_name

    def vad_path(self) -> Path:
        return self.folder / MANIFEST.vad_file_name


def _intact(source: Path, stderr: Callable[[str], None]) -> None:
    return None


def _ejected(source: Path, stderr: Callable[[str], None]) -> None:
    stderr(EJECTED)
    source.unlink()


def _read_error(source: Path, stderr: Callable[[str], None]) -> None:
    stderr(EJECTED)


def _damaged(source: Path, stderr: Callable[[str], None]) -> None:
    stderr(DAMAGED)


def _removed(source: Path, stderr: Callable[[str], None]) -> None:
    source.unlink()


def _replaced(source: Path, stderr: Callable[[str], None]) -> None:
    replacement = source.with_name("replacement.tmp")
    replacement.write_bytes(b"RIFF a different recording of another length")
    os.replace(replacement, source)


def _appended(source: Path, stderr: Callable[[str], None]) -> None:
    with source.open("ab") as stream:
        stream.write(b" still being recorded")


@pytest.mark.parametrize(
    ("during_decode", "status", "failure"),
    [
        (_intact, JobStatus.DONE, None),
        (_damaged, JobStatus.DONE, None),
        (_read_error, JobStatus.FAILED, FailureCode.UNREADABLE),
        (_ejected, JobStatus.FAILED, FailureCode.NOT_FOUND),
        (_removed, JobStatus.FAILED, FailureCode.NOT_FOUND),
        (_replaced, JobStatus.FAILED, FailureCode.UNREADABLE),
        (_appended, JobStatus.FAILED, FailureCode.UNREADABLE),
    ],
)
def test_input_lost_during_decode_fails_before_transcription(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    during_decode: Callable[[Path, Callable[[str], None]], None],
    status: JobStatus,
    failure: FailureCode | None,
) -> None:
    fake = FakeNative(during_decode)
    monkeypatch.setattr(binaries, "sys", SimpleNamespace(platform="darwin"))
    monkeypatch.setattr(ffmpeg, "run_job_process", fake.run_ffmpeg)
    monkeypatch.setattr(whisper, "run_job_process", fake.run_whisper)
    paths = RuntimePaths(tmp_path / "bin", tmp_path / "models", ROOT / "resources", tmp_path / "u")
    source = tmp_path / "in/clip.mp3"
    source.parent.mkdir()
    source.write_bytes(b"RIFF public fixture stand-in")
    later = tmp_path / "in/later.wav"
    later.write_bytes(b"RIFF second public fixture stand-in")
    out = tmp_path / "out"
    jobs = [Job(source), Job(later)]
    Coordinator(paths, Registry(paths.models_dir)).run_batch(  # type: ignore[arg-type]
        jobs, BatchOptions("tiny", out, formats=("txt",), backend="cpu"), vulkan_ok=False
    )
    assert (jobs[0].status, jobs[0].failure) == (status, failure)
    if status == JobStatus.FAILED:
        # No transcription for the lost input and nothing published for it.
        assert fake.calls[:3] == ["ffprobe", "ffmpeg", "ffprobe"]
        assert not jobs[0].outputs
        assert not (out / "clip.txt").exists()
    else:
        assert fake.calls[:3] == ["ffprobe", "ffmpeg", "whisper"]
        assert (out / "clip.txt").is_file()
    # The batch continues with the next file.
    assert (jobs[1].status, jobs[1].failure) == (JobStatus.DONE, None)
    assert list((paths.user_dir / "work").iterdir()) == []
