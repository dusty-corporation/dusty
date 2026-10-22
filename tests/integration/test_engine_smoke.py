"""Run the pinned CPU native pipeline on a small public-domain fixture."""

import os
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

import pytest

from dusty.engine import probe_audio, run_whisper, transcode_audio
from dusty.engine.backend import probe_vulkan
from dusty.models import ModelRegistry, load_manifest
from dusty.runtime_paths import RuntimePaths, resolve_paths

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(sys.platform != "win32", reason="Pinned development binaries target Windows")
def test_decode_transcribe_with_vad(tmp_path: Path) -> None:
    paths = resolve_paths(repo_root=ROOT, frozen=False)
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    backend = os.environ.get("DUSTY_TEST_BACKEND", "cpu")
    assert backend in {"cpu", "vulkan"}
    source = ROOT / "tests/fixtures/audio/formats/jfk.wav"
    probe = probe_audio(paths.bin_dir / "ffmpeg/ffprobe.exe", source)
    assert probe.has_audio and 10 <= probe.duration_sec <= 12
    wav = tmp_path / "audio.wav"
    assert transcode_audio(paths.bin_dir / "ffmpeg/ffmpeg.exe", source, wav) >= 0
    updates = []
    result = run_whisper(
        paths.bin_dir / backend / "whisper-cli.exe",
        registry.model_path("tiny"),
        wav,
        tmp_path / "raw",
        model_id="tiny",
        task="transcribe",
        language="en",
        threads=4,
        duration_sec=probe.duration_sec,
        backend=backend,
        vad_model=registry.vad_path(),
        prompt="",
        on_progress=updates.append,
    )
    assert result.transcript.backend == backend
    assert result.transcript.language == "en"
    assert len(result.transcript.segments) > 0
    assert result.timings_ms["total"] > 0
    assert updates and all(0 <= value <= 1 for value in updates)
    assert updates == sorted(updates)
    contains_expected = "fellow americans" in " ".join(
        segment.text.lower() for segment in result.transcript.segments
    )
    assert contains_expected


@pytest.mark.skipif(sys.platform != "win32", reason="Pinned development binaries target Windows")
def test_cpu_and_available_vulkan_agree(tmp_path: Path) -> None:
    dev = resolve_paths(repo_root=ROOT, frozen=False)
    paths = RuntimePaths(dev.bin_dir, dev.models_dir, dev.resources_dir, tmp_path / "user")
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    if not probe_vulkan(paths, registry):
        pytest.skip("No usable Vulkan device on this test host")
    texts = []
    for backend in ("cpu", "vulkan"):
        result = run_whisper(
            paths.bin_dir / backend / "whisper-cli.exe",
            registry.model_path("tiny"),
            ROOT / "tests/fixtures/audio/formats/jfk.wav",
            tmp_path / backend,
            model_id="tiny",
            task="transcribe",
            language="en",
            threads=4,
            duration_sec=11,
            backend=backend,
            vad_model=registry.vad_path(),
            prompt="",
        )
        assert result.transcript.backend == backend
        text = " ".join(segment.text for segment in result.transcript.segments)
        texts.append(" ".join(re.findall(r"\w+", text.lower())))
    assert texts[0] and texts[1]
    assert SequenceMatcher(None, texts[0], texts[1]).ratio() >= 0.9
