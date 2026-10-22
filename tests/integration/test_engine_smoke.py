"""Run the pinned CPU native pipeline on a small public-domain fixture."""

import sys
from pathlib import Path

import pytest

from dusty.engine import probe_audio, run_whisper, transcode_audio
from dusty.models import ModelRegistry, load_manifest
from dusty.runtime_paths import resolve_paths

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(sys.platform != "win32", reason="Pinned development binaries target Windows")
def test_cpu_decode_transcribe_with_vad(tmp_path: Path) -> None:
    paths = resolve_paths(repo_root=ROOT, frozen=False)
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    source = ROOT / "tests/fixtures/audio/formats/jfk.wav"
    probe = probe_audio(paths.bin_dir / "ffmpeg/ffprobe.exe", source)
    assert probe.has_audio and 10 <= probe.duration_sec <= 12
    wav = tmp_path / "audio.wav"
    assert transcode_audio(paths.bin_dir / "ffmpeg/ffmpeg.exe", source, wav) >= 0
    result = run_whisper(
        paths.bin_dir / "cpu/whisper-cli.exe",
        registry.model_path("tiny"),
        wav,
        tmp_path / "raw",
        model_id="tiny",
        task="transcribe",
        language="en",
        threads=4,
        duration_sec=probe.duration_sec,
        backend="cpu",
        vad_model=registry.vad_path(),
        prompt="",
    )
    assert result.transcript.backend == "cpu"
    assert result.transcript.language == "en"
    assert len(result.transcript.segments) > 0
    assert result.timings_ms["total"] > 0
