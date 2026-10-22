"""Invoke pinned whisper-cli and parse its JSON into platform-neutral types."""

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dusty.core import Segment, Transcript
from dusty.platform.win_process import run_job_process

from .progress import ProgressState


class EngineError(RuntimeError):
    """The native transcription process failed without exposing raw stderr."""

    def __init__(self, message: str, *, gpu_error: bool = False, cancelled: bool = False):
        super().__init__(message)
        self.gpu_error = gpu_error
        self.cancelled = cancelled


@dataclass(frozen=True)
class EngineRun:
    transcript: Transcript
    process_sec: float
    first_progress_sec: float | None
    timings_ms: dict[str, float]
    text_context: int | None


def parse_whisper_json(
    output: Path,
    *,
    model_id: str,
    task: Literal["transcribe", "translate"],
    backend: Literal["cpu", "vulkan"],
    duration_sec: float,
) -> Transcript:
    """Read only the segment text needed for output; ignore engine metadata paths."""
    data = json.loads(output.read_text(encoding="utf-8"))
    segments = tuple(
        Segment(
            index=index,
            start=part["offsets"]["from"] / 1000,
            end=part["offsets"]["to"] / 1000,
            text=part["text"],
        )
        for index, part in enumerate(data["transcription"])
    )
    return Transcript(
        segments=segments,
        language=data["result"]["language"],
        task=task,
        model_id=model_id,
        backend=backend,
        duration_sec=duration_sec,
    )


def run_whisper(
    executable: Path,
    model: Path,
    wav: Path,
    output_stem: Path,
    *,
    model_id: str,
    task: Literal["transcribe", "translate"],
    language: str,
    threads: int,
    duration_sec: float,
    backend: Literal["cpu", "vulkan"],
    vad_model: Path | None,
    prompt: str,
    cancel: threading.Event | None = None,
) -> EngineRun:
    """Pass prompts as one argument and never retain raw native stderr."""
    args = [
        str(executable.resolve()),
        "-m",
        str(model),
        "-f",
        str(wav),
        "-l",
        language,
        "-t",
        str(threads),
        "-ojf",
        "-of",
        str(output_stem),
        "-pp",
    ]
    if task == "translate":
        args.append("-tr")
    if backend == "cpu":
        args.append("-ng")
    if vad_model:
        args.extend(["--vad", "-vm", str(vad_model)])
    if prompt:
        args.extend(["--prompt", prompt])
    state = ProgressState(started_at=time.monotonic())
    result = run_job_process(args, on_stderr=state.feed, cancel=cancel, timeout_sec=12 * 3600)
    if result.cancelled:
        raise EngineError("Transcription cancelled", cancelled=True)
    if result.exit_code:
        raise EngineError("Transcription engine failed", gpu_error=state.gpu_error)
    # The CPU-only package with -ng omits the backend banner. It cannot load Vulkan.
    if (
        backend == "vulkan"
        and state.backend != "vulkan"
        or (backend == "cpu" and state.backend == "vulkan")
    ):
        raise EngineError("Requested backend was not selected", gpu_error=backend == "vulkan")
    output = Path(str(output_stem) + ".json")
    if not output.is_file():
        raise EngineError("Transcription output missing")
    try:
        transcript = parse_whisper_json(
            output,
            model_id=model_id,
            task=task,
            backend=backend,
            duration_sec=duration_sec,
        )
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise EngineError("Transcription output invalid") from exc
    return EngineRun(
        transcript=transcript,
        process_sec=result.elapsed_sec,
        first_progress_sec=state.first_progress_sec,
        timings_ms=state.timings_ms,
        text_context=state.text_context,
    )
