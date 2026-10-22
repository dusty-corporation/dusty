"""Compare VAD on/off over public speech at 0 and 300 seconds in silence."""

import json
import os
import re
from pathlib import Path

from dusty.engine import probe_audio, run_whisper, transcode_audio
from dusty.models import ModelRegistry, load_manifest
from dusty.runtime_paths import resolve_paths

ROOT = Path(__file__).resolve().parents[2]
# Spoken reference ends at 10.5 s (the M1 JFK reference), not the 11 s container end.
SPEECH_WINDOWS = ((0.0, 10.5), (300.0, 310.5))
TIMESTAMP_TOLERANCE = 0.5
MAX_VAD_WORDS = 80
MAX_OUTSIDE_WORDS = 5


def in_speech_span(start: float, end: float) -> bool:
    return any(
        low - TIMESTAMP_TOLERANCE <= start <= end <= high + TIMESTAMP_TOLERANCE
        for low, high in SPEECH_WINDOWS
    )


def word_spans(raw: dict) -> list[tuple[float, float]]:
    """Reassemble words from full-JSON tokens; exclude control tokens."""
    spans = []
    for segment in raw["transcription"]:
        current = ""
        start = end = 0.0
        for token in segment["tokens"]:
            if token["text"].startswith("<|"):
                continue
            for piece in re.split(r"(\s+)", token["text"]):
                if not piece:
                    continue
                if piece.isspace():
                    if re.search(r"\w", current):
                        spans.append((start, end))
                    current = ""
                else:
                    if not current:
                        start = token["offsets"]["from"] / 1000
                    end = token["offsets"]["to"] / 1000
                    current += piece
        if re.search(r"\w", current):
            spans.append((start, end))
    return spans


def test_vad_limits_hallucination_in_ten_minutes_of_silence(tmp_path: Path) -> None:
    paths = resolve_paths(repo_root=ROOT, frozen=False)
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    source = ROOT / "tests/fixtures/audio/vad/mostly-silence-10min.m4a"
    probe = probe_audio(paths.bin_dir / "ffmpeg/ffprobe.exe", source)
    assert 599 <= probe.duration_sec <= 601
    wav = tmp_path / "audio.wav"
    transcode_audio(paths.bin_dir / "ffmpeg/ffmpeg.exe", source, wav)
    results = {}
    backend = os.environ.get("DUSTY_TEST_BACKEND", "cpu")
    assert backend in {"cpu", "vulkan"}
    for mode in ("on", "off"):
        run = run_whisper(
            paths.bin_dir / backend / "whisper-cli.exe",
            registry.model_path("tiny"),
            wav,
            tmp_path / f"raw-{mode}",
            model_id="tiny",
            task="transcribe",
            language="en",
            threads=4,
            duration_sec=probe.duration_sec,
            backend=backend,
            vad_model=registry.vad_path() if mode == "on" else None,
            prompt="",
        )
        words = sum(len(re.findall(r"\w+", segment.text)) for segment in run.transcript.segments)
        outside = sum(
            len(re.findall(r"\w+", segment.text))
            for segment in run.transcript.segments
            if not in_speech_span(segment.start, segment.end)
        )
        raw = json.loads((tmp_path / f"raw-{mode}.json").read_text(encoding="utf-8"))
        word_times = word_spans(raw)
        results[mode] = {
            "words": words,
            "outside_words": outside,
            "segments": len(run.transcript.segments),
            "process_sec": round(run.process_sec, 3),
            "word_timestamp_violations": sum(not in_speech_span(a, b) for a, b in word_times),
        }
        if mode == "on":
            contains_expected_speech = any(
                "fellow americans" in segment.text.lower() for segment in run.transcript.segments
            )
            assert len(run.transcript.segments) == len(SPEECH_WINDOWS)
            for segment, (start, end) in zip(run.transcript.segments, SPEECH_WINDOWS, strict=True):
                assert in_speech_span(segment.start, segment.end)
                assert abs(segment.start - start) <= TIMESTAMP_TOLERANCE
                assert abs(segment.end - end) <= TIMESTAMP_TOLERANCE
            assert len(word_times) >= 40
    (tmp_path / "vad-summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("vad_summary=" + json.dumps(results, sort_keys=True))
    assert results["on"]["words"] <= MAX_VAD_WORDS
    assert results["on"]["outside_words"] <= MAX_OUTSIDE_WORDS
    assert results["on"]["word_timestamp_violations"] == 0
    assert contains_expected_speech
