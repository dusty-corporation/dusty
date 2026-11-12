"""Invoke pinned whisper-cli and parse its JSON into platform-neutral types."""

import json
import math
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from dusty.core import Segment, Transcript, Word
from dusty.core.types import Cancellation, EngineBackend

from .progress import ProgressState

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


# The longest one transcription may run before it is stopped.
WHISPER_LIMIT_SEC = 12 * 3600


class EngineError(RuntimeError):
    """The native transcription process failed without exposing raw stderr.

    ``unsupported_gpu`` means the Metal engine cannot use this GPU: the engine
    reported so, or this is a virtual Mac (``virtual_mac``), where it never
    starts. ``device_name`` is the recognized GPU description it reported, if any.
    """

    def __init__(
        self,
        message: str,
        *,
        gpu_error: bool = False,
        cancelled: bool = False,
        unsupported_gpu: bool = False,
        device_name: str | None = None,
        virtual_mac: bool = False,
    ):
        super().__init__(message)
        self.gpu_error = gpu_error
        self.cancelled = cancelled
        self.unsupported_gpu = unsupported_gpu
        self.device_name = device_name
        self.virtual_mac = virtual_mac


@dataclass(frozen=True)
class _MetalStop:
    """Stop a Metal run on a user cancel, or once its stderr shows it cannot succeed.

    A GPU without the features the engine needs, or a failed Metal command,
    fails the run on the GPU whatever happens next. A stalled GPU can keep the
    engine waiting for hours, so it is stopped at once and the caller may
    retry on the CPU.
    """

    state: ProgressState
    cancel: Cancellation | None

    def is_set(self) -> bool:
        if self.state.metal_unsupported or self.state.gpu_error:
            return True
        return self.cancel is not None and self.cancel.is_set()


@dataclass(frozen=True)
class EngineRun:
    transcript: Transcript
    process_sec: float
    first_progress_sec: float | None
    timings_ms: dict[str, float]
    text_context: int | None
    device_name: str | None


# Scripts written without spaces between words: each token counts as one word,
# so one unsure character never marks a whole sentence.
_NO_SPACE_SCRIPTS = (
    (0x0E00, 0x0EFF),  # Thai, Lao
    (0x1000, 0x109F),  # Myanmar
    (0x1780, 0x17FF),  # Khmer
    (0x3040, 0x30FF),  # Hiragana, Katakana
    (0x3400, 0x4DBF),  # CJK extension A
    (0x4E00, 0x9FFF),  # CJK unified ideographs
    (0xF900, 0xFAFF),  # CJK compatibility ideographs
    (0x20000, 0x2FA1F),  # CJK extensions B and later
)


def _no_space_script(text: str) -> bool:
    return any(low <= ord(char) <= high for char in text for low, high in _NO_SPACE_SCRIPTS)


def _words(tokens: object, text: str) -> tuple[Word, ...]:
    """Group engine tokens into words; return none when they do not match the text.

    Special tokens such as "[_BEG_]" and "[_TT_150]" are not speech. A token that
    starts with a space starts a new word. The engine already joins tokens that
    split one character. Anything unexpected keeps the plain segment text only.
    """
    if not isinstance(tokens, list):
        return ()
    words: list[list] = []
    for token in tokens:
        if not isinstance(token, dict):
            return ()
        piece, probability = token.get("text"), token.get("p")
        if not isinstance(piece, str) or isinstance(probability, bool):
            return ()
        if not isinstance(probability, (int, float)) or not 0 <= probability <= 1:
            return ()
        if piece.startswith("[_") and piece.endswith("]"):
            continue
        spoken = any(char.isalnum() for char in piece)
        sure = float(probability) if spoken else 1.0
        previous = words[-1][0] if words else ""
        start, end = _token_times(token)
        if (
            not words
            or piece[:1].isspace()
            or _no_space_script(piece)
            or _no_space_script(previous[-1:])
        ):
            words.append([piece, sure, start, end])
        else:
            words[-1][0] += piece
            words[-1][1] = min(words[-1][1], sure)
            words[-1][3] = end if words[-1][3] is not None else None
            if start is None:
                words[-1][2] = None
    if "".join(word[0] for word in words).split() != text.split():
        return ()
    return tuple(
        Word(piece, confidence, start, end if start is not None else None)
        for piece, confidence, start, end in words
    )


def _token_times(token: dict) -> tuple[float | None, float | None]:
    """A token's start and end in seconds, or None for both when they are missing."""
    offsets = token.get("offsets")
    if not isinstance(offsets, dict):
        return None, None
    begin, finish = offsets.get("from"), offsets.get("to")
    if not (isinstance(begin, int | float) and isinstance(finish, int | float)):
        return None, None
    if isinstance(begin, bool) or isinstance(finish, bool):
        return None, None
    if not (math.isfinite(finish) and 0 <= begin <= finish):
        return None, None
    return begin / 1000, finish / 1000


def parse_whisper_json(
    output: Path,
    *,
    model_id: str,
    task: Literal["transcribe", "translate"],
    backend: EngineBackend,
    duration_sec: float,
) -> Transcript:
    """Read the segment text and word confidence needed for output.

    Engine metadata paths are ignored.
    """
    data = json.loads(output.read_text(encoding="utf-8"))
    segments = tuple(
        Segment(
            index=index,
            start=part["offsets"]["from"] / 1000,
            end=part["offsets"]["to"] / 1000,
            text=part["text"],
            words=_words(part.get("tokens"), part["text"]),
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
    backend: EngineBackend,
    vad_model: Path | None,
    prompt: str,
    cancel: Cancellation | None = None,
    on_progress: Callable[[float], None] | None = None,
    timeout_sec: float = WHISPER_LIMIT_SEC,
    carry_prompt: bool = False,
) -> EngineRun:
    """Pass prompts as one argument and never retain raw native stderr."""
    if backend == "metal":
        from dusty.platform import virtual_mac

        # Inside a virtual Mac the Metal engine can stall while it compiles its
        # shaders, before it reports anything, so it never starts there and the
        # caller may run the CPU engine instead.
        if virtual_mac.is_virtual_mac():
            if cancel is not None and cancel.is_set():
                raise EngineError("Transcription cancelled", cancelled=True)
            raise EngineError(
                "Dusty does not use the GPU inside a virtual Mac",
                gpu_error=True,
                unsupported_gpu=True,
                virtual_mac=True,
            )
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
        if carry_prompt:
            # Keep steering with the prompt through the whole recording, not
            # only its first window (an engine hint of an extension).
            args.append("--carry-initial-prompt")
    state = ProgressState(started_at=time.monotonic())
    previous_progress = 0.0

    def publish_progress() -> None:
        nonlocal previous_progress
        if on_progress and state.progress != previous_progress:
            previous_progress = state.progress
            on_progress(state.progress)

    result = run_job_process(
        args,
        on_stderr=state.feed,
        cancel=_MetalStop(state, cancel) if backend == "metal" else cancel,
        timeout_sec=timeout_sec,
        on_poll=publish_progress,
    )
    # A Metal run whose stderr showed a GPU the engine cannot use, or a failed
    # Metal command, fails on the GPU whether it was stopped or exited itself.
    # A user cancel still wins. Other backends never consult the cancel here.
    if backend == "metal" and not (cancel is not None and cancel.is_set()):
        if state.metal_unsupported:
            raise EngineError(
                "GPU cannot run the Metal engine",
                gpu_error=True,
                unsupported_gpu=True,
                device_name=state.device_name,
            )
        if state.gpu_error:
            raise EngineError("Transcription engine failed", gpu_error=True)
    if result.cancelled:
        raise EngineError("Transcription cancelled", cancelled=True)
    if result.exit_code:
        raise EngineError("Transcription engine failed", gpu_error=state.gpu_error)
    # The Windows CPU-only package with -ng omits the backend banner and cannot
    # load a GPU backend; the Mac CPU package prints "no GPU found". A GPU request
    # is accepted only when stderr shows that exact backend was selected.
    if (backend != "cpu" and state.backend != backend) or (
        backend == "cpu" and state.backend not in (None, "cpu")
    ):
        raise EngineError("Requested backend was not selected", gpu_error=backend != "cpu")
    # Metal failure lines are anchored to known ggml messages, so a reported
    # command buffer failure fails the GPU run even when the exit code is zero.
    if backend == "metal" and state.gpu_error:
        raise EngineError("Transcription engine failed", gpu_error=True)
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
        device_name=state.device_name,
    )
