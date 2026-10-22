"""Translate a public-domain Persian quatrain against an independent reference."""

import re
import sys
from pathlib import Path

import pytest

from dusty.engine import run_whisper
from dusty.models import ModelRegistry, load_manifest
from dusty.runtime_paths import resolve_paths

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(sys.platform != "win32", reason="Pinned binaries target Windows")
def test_persian_translation_is_english(tmp_path: Path) -> None:
    paths = resolve_paths(repo_root=ROOT, frozen=False)
    registry = ModelRegistry(load_manifest(paths.resources_dir / "models.json"), paths.models_dir)
    texts = {}
    for task in ("transcribe", "translate"):
        result = run_whisper(
            paths.bin_dir / "cpu/whisper-cli.exe",
            registry.model_path("small"),
            ROOT / "tests/fixtures/audio/translate/rubaiyat-fa.wav",
            tmp_path / task,
            model_id="small",
            task=task,
            language="fa",
            threads=4,
            duration_sec=15,
            backend="cpu",
            vad_model=registry.vad_path(),
            prompt="",
        )
        assert result.transcript.task == task
        texts[task] = " ".join(segment.text for segment in result.transcript.segments)
    # The alternating English reading is excluded from the fixture. The control
    # must recognize Persian, and Translate must actually change the output script.
    assert sum("\u0600" <= char <= "\u06ff" for char in texts["transcribe"]) >= 20
    translated = texts["translate"]
    assert not any("\u0600" <= char <= "\u06ff" for char in translated)
    words = set(re.findall(r"[a-z]+", translated.lower()))
    # Whinfield's published quatrain 2 says "burns as fire". This is a loose
    # translation smoke test, not a WER or literary translation quality claim.
    assert "fire" in words
    assert len(words & {"who", "you", "your", "the", "is", "and", "was", "it", "in", "to"}) >= 4
