"""Run the real Coordinator on macOS with a staged development bin_dir and models.

Stage them with tools/stage_macos_dev_bin.py, then set DUSTY_BIN_DIR and
DUSTY_MODELS_DIR. The test is skipped until the Mac process runner is present.
"""

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from dusty.core import BatchOptions, Job, JobStatus
from dusty.core.types import Backend
from dusty.engine.binaries import ffprobe_path, lifeline_path, whisper_path
from dusty.models import ModelRegistry, load_manifest
from dusty.privacy.logging import configure_logger
from dusty.queue import Coordinator
from dusty.runtime_paths import RuntimePaths, resolve_paths

ROOT = Path(__file__).resolve().parents[2]
FORMATS = ("txt", "srt", "vtt", "json", "docx")


def _staged() -> bool:
    bin_dir = os.environ.get("DUSTY_BIN_DIR")
    models_dir = os.environ.get("DUSTY_MODELS_DIR")
    if not bin_dir or not models_dir:
        return False
    return (
        whisper_path(Path(bin_dir), "cpu", "darwin").is_file()
        and lifeline_path(Path(bin_dir)).is_file()
        and (Path(models_dir) / "ggml-tiny.bin").is_file()
    )


pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or not _staged(),
    reason="Needs macOS plus a staged DUSTY_BIN_DIR (with lifeline) and DUSTY_MODELS_DIR",
)


@pytest.fixture
def mac_paths(tmp_path: Path) -> RuntimePaths:
    from dusty.engine import ffmpeg

    dev = resolve_paths(repo_root=ROOT, frozen=False)
    try:
        ffmpeg.run_job_process([str(ffprobe_path(dev.bin_dir).resolve()), "-version"])
    except OSError as exc:
        if "unavailable on this platform" in str(exc):
            pytest.skip("Mac process runner has not landed in this checkout")
        raise
    return RuntimePaths(dev.bin_dir, dev.models_dir, dev.resources_dir, tmp_path / "user")


def _run(
    paths: RuntimePaths, tmp_path: Path, backend: Backend, vulkan_ok: bool
) -> tuple[Job, Path]:
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    source = tmp_path / "CANARY_PATIENT_JANE_DOE.wav"
    shutil.copyfile(paths.resources_dir / "selftest.wav", source)
    out = tmp_path / f"out-{backend}"
    options = BatchOptions("tiny", out, formats=FORMATS, backend=backend, prompt="CANARYMEDTERM")
    job = Job(source)
    Coordinator(paths, registry).run_batch([job], options, vulkan_ok=vulkan_ok)
    return job, out


def _check_outputs(job: Job, out: Path, paths: RuntimePaths, backend: str) -> None:
    assert job.status == JobStatus.DONE, job.failure
    assert sorted(path.suffix for path in job.outputs) == sorted(f".{fmt}" for fmt in FORMATS)
    assert all(path.is_file() and path.stat().st_size > 0 for path in job.outputs)
    text = (out / "CANARY_PATIENT_JANE_DOE.txt").read_text(encoding="utf-8").lower()
    assert "fellow americans" in text and "your country" in text
    exported = json.loads((out / "CANARY_PATIENT_JANE_DOE.json").read_text(encoding="utf-8"))
    assert exported["backend"] == backend == job.backend_used
    assert exported["model_id"] == "tiny" and exported["segments"]
    for caption in ("srt", "vtt"):
        assert "-->" in (out / f"CANARY_PATIENT_JANE_DOE.{caption}").read_text(encoding="utf-8")
    assert list((paths.user_dir / "work").iterdir()) == []
    assert not list(out.glob("*.dusty-tmp"))


def _check_log(paths: RuntimePaths, backend: str) -> None:
    logger = configure_logger(paths.user_dir)
    for handler in logger.handlers:
        handler.flush()
    log = (paths.user_dir / "logs/dusty.log").read_text(encoding="utf-8")
    assert f"backend={backend}" in log
    assert "CANARY" not in log and "/Users/" not in log


def test_tiny_cpu_all_formats_and_clean_work(mac_paths: RuntimePaths, tmp_path: Path) -> None:
    configure_logger(mac_paths.user_dir)
    job, out = _run(mac_paths, tmp_path, "cpu", vulkan_ok=False)
    _check_outputs(job, out, mac_paths, "cpu")
    assert not job.gpu_fallback
    _check_log(mac_paths, "cpu")


@pytest.mark.usefixtures("metal_gpu")
def test_tiny_metal_when_probe_passes(mac_paths: RuntimePaths, tmp_path: Path) -> None:
    from dusty.engine.backend import probe_gpu

    registry = ModelRegistry(
        load_manifest(mac_paths.resources_dir / "models.json"), mac_paths.models_dir
    )
    if not whisper_path(mac_paths.bin_dir, "metal").is_file():
        pytest.skip("This staged bin_dir has no Metal engine")
    # Unless the engine reports a GPU it cannot use (metal_gpu skips then), the
    # GPU check must pass: a failing check fails this test instead of skipping it.
    assert probe_gpu(mac_paths, registry)
    configure_logger(mac_paths.user_dir)
    job, out = _run(mac_paths, tmp_path, "auto", vulkan_ok=True)
    _check_outputs(job, out, mac_paths, "metal")
    assert not job.gpu_fallback
    _check_log(mac_paths, "metal")
