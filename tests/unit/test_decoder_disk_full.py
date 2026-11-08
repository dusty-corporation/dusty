"""Derive only a redacted disk-full category from native decoder stderr."""

from types import SimpleNamespace

import pytest

from dusty.engine import ffmpeg


@pytest.mark.parametrize(
    "message", ["No space left on device", "Not enough space on the disk", "Disk is full"]
)
def test_native_no_space_message_is_not_reported_as_a_damaged_recording(
    tmp_path, monkeypatch, message
):
    def process(args, **kwargs):
        kwargs["on_stderr"]("Error writing trailer: " + message)
        return SimpleNamespace(cancelled=False, exit_code=1, elapsed_sec=0.1)

    monkeypatch.setattr(ffmpeg, "run_job_process", process)
    with pytest.raises(ffmpeg.DecoderError) as error:
        ffmpeg.transcode_audio(tmp_path / "ffmpeg.exe", tmp_path / "clip.wav", tmp_path / "out.wav")
    assert error.value.disk_full
    assert str(error.value) == "Audio decode failed"


@pytest.mark.parametrize(
    "payload,has_audio,duration",
    [
        ('{"streams":[{"codec_type":"audio","duration":"11.0"}]}', True, 11.0),
        ('{"streams":[{"codec_type":"audio","duration":"N/A"}]}', True, 0.0),
        ('{"streams":[]}', False, 0.0),
    ],
)
def test_existing_probe_parser_and_arguments_remain_available(
    tmp_path, monkeypatch, payload, has_audio, duration
):
    source = tmp_path / "clip.wav"
    executable = tmp_path / "ffprobe.exe"
    cancel = object()

    def process(args, **kwargs):
        assert args == [
            str(executable.resolve()),
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_type,duration:format=duration",
            "-of",
            "json",
            str(source),
        ]
        assert kwargs["cancel"] is cancel and kwargs["timeout_sec"] == 30
        kwargs["on_stdout"](payload)
        return SimpleNamespace(cancelled=False, exit_code=0, elapsed_sec=0.1)

    monkeypatch.setattr(ffmpeg, "run_job_process", process)
    result = ffmpeg.probe_audio(executable, source, cancel=cancel)
    assert result.has_audio is has_audio and result.duration_sec == duration


def test_decode_arguments_and_success_result_remain_unchanged(tmp_path, monkeypatch):
    executable, source, output = (
        tmp_path / name for name in ("ffmpeg.exe", "clip.wav", "audio.wav")
    )
    cancel = object()

    def process(args, **kwargs):
        assert args == [
            str(executable.resolve()),
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-protocol_whitelist",
            "file,pipe",
            "-i",
            str(source),
            "-vn",
            "-map",
            "0:a:0",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
            str(output),
        ]
        assert kwargs["cancel"] is cancel and kwargs["timeout_sec"] == 43200
        output.write_bytes(b"controlled decoder output")
        return SimpleNamespace(cancelled=False, exit_code=0, elapsed_sec=0.25)

    monkeypatch.setattr(ffmpeg, "run_job_process", process)
    assert ffmpeg.transcode_audio(executable, source, output, cancel=cancel) == 0.25


# D-MAC-023: FFmpeg logs a read error, ends the input there and still exits 0.
EJECTED = "[in#0/mp3 @ 0x8a901c000] Error during demuxing: Input/output error"
DAMAGED = "[in#0/mp3 @ 0x8a901c000] Error during demuxing: Invalid data found when processing input"


@pytest.mark.parametrize(("line", "lost"), [(EJECTED, True), (DAMAGED, False), ("", False)])
def test_read_error_fails_the_decode_even_when_ffmpeg_exits_zero(tmp_path, monkeypatch, line, lost):
    output = tmp_path / "audio.wav"

    def process(args, **kwargs):
        if line:
            kwargs["on_stderr"](line)
        output.write_bytes(b"truncated decoder output")
        return SimpleNamespace(cancelled=False, exit_code=0, elapsed_sec=0.1)

    monkeypatch.setattr(ffmpeg, "run_job_process", process)
    if not lost:
        # Slightly damaged recordings that decode usefully keep working.
        assert ffmpeg.transcode_audio(tmp_path / "ffmpeg", tmp_path / "clip.mp3", output) == 0.1
        return
    with pytest.raises(ffmpeg.DecoderError) as error:
        ffmpeg.transcode_audio(tmp_path / "ffmpeg", tmp_path / "clip.mp3", output)
    assert error.value.unreadable and not error.value.disk_full
    assert str(error.value) == "Audio decode failed"
