"""The headless wrapper must use the same safe silence default as the app."""

import inspect

import pytest

from dusty import devcli


@pytest.mark.parametrize(
    ("flags", "expected"), [([], False), (["--vad"], True), (["--no-vad"], False)]
)
def test_headless_silence_default_and_explicit_override(monkeypatch, flags, expected):
    seen = []
    monkeypatch.setattr(devcli, "transcribe", lambda *args, **kwargs: seen.append(kwargs) or 0)
    assert devcli.main(["transcribe", "clip.wav", "--out", "output", *flags]) == 0
    assert seen[0]["vad"] is expected


def test_headless_api_default_is_also_off():
    assert inspect.signature(devcli.transcribe).parameters["vad"].default is False
