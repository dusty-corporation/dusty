"""Run the shared coordinator with pinned binaries and public fixtures."""

import sys
import threading
from pathlib import Path

import pytest

from dusty.core import BatchOptions, FailureCode, Job, JobStatus
from dusty.engine import EngineError
from dusty.models import ModelRegistry, load_manifest
from dusty.privacy.logging import configure_logger
from dusty.queue import Coordinator
from dusty.runtime_paths import RuntimePaths, resolve_paths

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(sys.platform != "win32", reason="Pinned binaries target Windows")
def test_mixed_batch_all_formats_cleanup_and_canary(tmp_path: Path) -> None:
    dev = resolve_paths(repo_root=ROOT, frozen=False)
    paths = RuntimePaths(dev.bin_dir, dev.models_dir, dev.resources_dir, tmp_path / "user")
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    logger = configure_logger(paths.user_dir)
    source = ROOT / "tests/fixtures/audio/formats/jfk.wav"
    empty = tmp_path / "empty.wav"
    empty.touch()
    jobs = [Job(source), Job(empty)]
    options = BatchOptions(
        "tiny",
        tmp_path / "out",
        formats=("txt", "srt", "vtt", "json", "docx"),
        backend="cpu",
        prompt="CANARYMEDTERM",
    )
    Coordinator(paths, registry).run_batch(jobs, options, vulkan_ok=False)
    assert jobs[0].status == JobStatus.DONE
    assert len(jobs[0].outputs) == 5
    assert "fellow Americans" in (tmp_path / "out/jfk.txt").read_text(encoding="utf-8")
    assert jobs[1].status == JobStatus.FAILED
    assert jobs[1].failure == FailureCode.EMPTY_FILE
    assert list((paths.user_dir / "work").iterdir()) == []
    for handler in logger.handlers:
        handler.flush()
    log = (paths.user_dir / "logs/dusty.log").read_text(encoding="utf-8")
    assert "CANARYMEDTERM" not in log
    assert "jfk.wav" not in log
    assert str(source) not in log


@pytest.mark.skipif(sys.platform != "win32", reason="Pinned binaries target Windows")
def test_bad_inputs_and_cancel_are_isolated(tmp_path: Path) -> None:
    dev = resolve_paths(repo_root=ROOT, frozen=False)
    paths = RuntimePaths(dev.bin_dir, dev.models_dir, dev.resources_dir, tmp_path / "user")
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    fixtures = ROOT / "tests/fixtures/audio/bad"
    jobs = [
        Job(tmp_path / "missing.wav"),
        Job(fixtures / "zero-byte.mp3"),
        Job(fixtures / "no-audio.mp4"),
        Job(fixtures / "corrupt.mp3"),
    ]
    options = BatchOptions("tiny", tmp_path / "out", formats=("txt",), backend="cpu")
    Coordinator(paths, registry).run_batch(jobs, options, vulkan_ok=False)
    assert [job.failure for job in jobs] == [
        FailureCode.NOT_FOUND,
        FailureCode.EMPTY_FILE,
        FailureCode.NO_AUDIO,
        FailureCode.DECODE_ERROR,
    ]
    assert all(job.status == JobStatus.FAILED for job in jobs)
    assert list((paths.user_dir / "work").iterdir()) == []
    cancel = threading.Event()
    cancel.set()
    job = Job(ROOT / "tests/fixtures/audio/formats/jfk.wav")
    Coordinator(paths, registry).run_batch([job], options, cancel=cancel, vulkan_ok=False)
    assert job.status == JobStatus.CANCELLED
    assert not list((tmp_path / "out").glob("*")) if (tmp_path / "out").exists() else True


@pytest.mark.skipif(sys.platform != "win32", reason="Pinned binaries target Windows")
def test_gpu_failure_retries_same_file_on_cpu(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import dusty.engine as engine_module

    dev = resolve_paths(repo_root=ROOT, frozen=False)
    paths = RuntimePaths(dev.bin_dir, dev.models_dir, dev.resources_dir, tmp_path / "user")
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    original = engine_module.run_whisper
    seen: list[str] = []

    def fake_run(*args: object, **kwargs: object):
        backend = str(kwargs["backend"])
        seen.append(backend)
        if backend == "vulkan":
            raise EngineError("Device failed", gpu_error=True)
        return original(*args, **kwargs)

    monkeypatch.setattr(engine_module, "run_whisper", fake_run)
    job = Job(ROOT / "tests/fixtures/audio/formats/jfk.wav")
    options = BatchOptions("tiny", tmp_path / "out", formats=("txt",), backend="auto")
    Coordinator(paths, registry).run_batch([job], options, vulkan_ok=True)
    assert seen == ["vulkan", "cpu"]
    assert job.status == JobStatus.DONE
    assert job.backend_used == "cpu"
    assert job.gpu_fallback
