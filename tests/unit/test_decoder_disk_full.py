"""Derive only a redacted disk-full category from native decoder stderr."""

from types import SimpleNamespace

import pytest

from dusty.engine import ffmpeg


def test_native_no_space_message_is_not_reported_as_a_damaged_recording(tmp_path, monkeypatch):
    def process(args, **kwargs):
        kwargs["on_stderr"]("Error writing trailer: No space left on device")
        return SimpleNamespace(cancelled=False, exit_code=1, elapsed_sec=0.1)

    monkeypatch.setattr(ffmpeg, "run_job_process", process)
    with pytest.raises(ffmpeg.DecoderError) as error:
        ffmpeg.transcode_audio(tmp_path / "ffmpeg.exe", tmp_path / "clip.wav", tmp_path / "out.wav")
    assert error.value.disk_full
    assert str(error.value) == "Audio decode failed"
