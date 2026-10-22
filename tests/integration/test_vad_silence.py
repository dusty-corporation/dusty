"""Compare VAD on/off over public speech at 0 and 300 seconds in silence."""

import json
import re
from pathlib import Path

from dusty.engine import probe_audio, run_whisper, transcode_audio
from dusty.models import ModelRegistry, load_manifest
from dusty.runtime_paths import resolve_paths

ROOT = Path(__file__).resolve().parents[2]
SPEECH_WINDOWS = ((0.0, 13.0), (298.0, 314.0))
MAX_VAD_WORDS = 80
MAX_OUTSIDE_WORDS = 5


def test_vad_limits_hallucination_in_ten_minutes_of_silence(tmp_path: Path) -> None:
    paths = resolve_paths(repo_root=ROOT, frozen=False)
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    source = ROOT / "tests/fixtures/audio/vad/mostly-silence-10min.m4a"
    probe = probe_audio(paths.bin_dir / "ffmpeg/ffprobe.exe", source)
    assert 599 <= probe.duration_sec <= 601
    wav = tmp_path / "audio.wav"
    transcode_audio(paths.bin_dir / "ffmpeg/ffmpeg.exe", source, wav)
    results = {}
    for mode in ("on", "off"):
        run = run_whisper(
            paths.bin_dir / "cpu/whisper-cli.exe",
            registry.model_path("tiny"),
            wav,
            tmp_path / f"raw-{mode}",
            model_id="tiny",
            task="transcribe",
            language="en",
            threads=4,
            duration_sec=probe.duration_sec,
            backend="cpu",
            vad_model=registry.vad_path() if mode == "on" else None,
            prompt="",
        )
        words = sum(len(re.findall(r"\w+", segment.text)) for segment in run.transcript.segments)
        outside = sum(
            len(re.findall(r"\w+", segment.text))
            for segment in run.transcript.segments
            if not any(start <= segment.start <= end for start, end in SPEECH_WINDOWS)
        )
        results[mode] = {
            "words": words,
            "outside_words": outside,
            "segments": len(run.transcript.segments),
            "process_sec": round(run.process_sec, 3),
        }
        if mode == "on":
            contains_expected_speech = any(
                "fellow americans" in segment.text.lower() for segment in run.transcript.segments
            )
    (tmp_path / "vad-summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("vad_summary=" + json.dumps(results, sort_keys=True))
    assert results["on"]["words"] <= MAX_VAD_WORDS
    assert results["on"]["outside_words"] <= MAX_OUTSIDE_WORDS
    assert contains_expected_speech
