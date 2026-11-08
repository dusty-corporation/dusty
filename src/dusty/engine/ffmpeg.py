"""Probe and decode local audio through the network-disabled FFmpeg package."""

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dusty.core.types import Cancellation

if TYPE_CHECKING:
    from dusty.platform.process import ProcessResult


def run_job_process(
    args: list[str],
    *,
    cwd: Path | None = None,
    on_stderr: Callable[[str], None] | None = None,
    on_stdout: Callable[[str], None] | None = None,
    cancel: Cancellation | None = None,
    timeout_sec: float | None = None,
    on_poll: Callable[[], None] | None = None,
) -> "ProcessResult":
    """Load the platform runner (Windows Job Object or macOS lifeline) only when called."""
    from dusty.platform.process import platform_runner

    return platform_runner(sys.platform)(
        args,
        cwd=cwd,
        on_stderr=on_stderr,
        on_stdout=on_stdout,
        cancel=cancel,
        timeout_sec=timeout_sec,
        on_poll=on_poll,
    )


class DecoderError(RuntimeError):
    """A local input could not be probed or decoded."""

    def __init__(
        self,
        message: str = "Audio decode failed",
        *,
        disk_full: bool = False,
        unreadable: bool = False,
    ):
        super().__init__(message)
        self.disk_full = disk_full
        self.unreadable = unreadable


@dataclass(frozen=True)
class AudioProbe:
    duration_sec: float
    has_audio: bool


def probe_audio(ffprobe: Path, source: Path, *, cancel: Cancellation | None = None) -> AudioProbe:
    """Read duration from FFprobe JSON in memory without logging input paths."""
    lines: list[str] = []
    result = run_job_process(
        [
            str(ffprobe.resolve()),
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_type,duration:format=duration",
            "-of",
            "json",
            str(source),
        ],
        on_stdout=lines.append,
        cancel=cancel,
        timeout_sec=30,
    )
    if result.cancelled:
        raise DecoderError("Audio probe cancelled")
    if result.exit_code:
        raise DecoderError("Audio probe failed")
    try:
        data = json.loads("\n".join(lines))
        streams = data.get("streams", [])
        has_audio = any(stream.get("codec_type") == "audio" for stream in streams)
        if not has_audio:
            return AudioProbe(0.0, False)
        duration_text = streams[0].get("duration") or data.get("format", {}).get("duration")
        if duration_text in (None, "N/A"):
            return AudioProbe(0.0, True)
        duration = float(duration_text)
        if duration <= 0:
            raise ValueError("Invalid duration")
        return AudioProbe(duration, True)
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        raise DecoderError("Audio probe output invalid") from exc


def transcode_audio(
    ffmpeg: Path,
    source: Path,
    output_wav: Path,
    *,
    cancel: Cancellation | None = None,
) -> float:
    """Decode to 16 kHz mono PCM in the per-job work directory."""
    disk_full = False
    unreadable = False

    def failure(line: str) -> None:
        nonlocal disk_full, unreadable
        text = line.lower()
        # FFmpeg ends input at a read error and still exits 0 (D-MAC-023), for
        # example when the drive holding the recording is ejected. Damaged data
        # reports "invalid data" instead and keeps decoding as before.
        unreadable |= "input/output error" in text
        disk_full |= any(
            phrase in text
            for phrase in (
                "no space left on device",
                "not enough space on the disk",
                "disk is full",
            )
        )

    result = run_job_process(
        [
            str(ffmpeg.resolve()),
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
            str(output_wav),
        ],
        cancel=cancel,
        on_stderr=failure,
        timeout_sec=12 * 3600,
    )
    if result.cancelled:
        raise DecoderError("Decode cancelled")
    if result.exit_code or not output_wav.is_file() or unreadable:
        raise DecoderError("Audio decode failed", disk_full=disk_full, unreadable=unreadable)
    return result.elapsed_sec
