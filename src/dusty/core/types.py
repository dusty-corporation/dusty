"""Typed values shared by the headless pipeline and the future GUI."""

import math
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

Backend = Literal["auto", "cpu", "vulkan", "metal"]
EngineBackend = Literal["cpu", "vulkan", "metal"]
Task = Literal["transcribe", "translate"]
OutputFormat = Literal["txt", "srt", "vtt", "json", "docx"]
CollisionPolicy = Literal["ask", "skip", "overwrite", "keep_both"]
UnsureLevel = Literal["very", "somewhat"]

# Time markers in TXT and DOCX: the interval in minutes the user may choose.
MARKER_MINUTES_MIN = 0.5
MARKER_MINUTES_MAX = 120.0
MARKER_MINUTES_DEFAULT = 5.0


class Cancellation(Protocol):
    """Read-only cancellation signal, including a group of user cancel events."""

    def is_set(self) -> bool: ...


class JobStatus(str, Enum):
    QUEUED = "queued"
    PREFLIGHT = "preflight"
    DECODING = "decoding"
    TRANSCRIBING = "transcribing"
    # An extension stage after transcription; Job.stage_status names it.
    PROCESSING = "processing"
    EXPORTING = "exporting"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class FailureCode(str, Enum):
    NOT_FOUND = "NOT_FOUND"
    UNREADABLE = "UNREADABLE"
    EMPTY_FILE = "EMPTY_FILE"
    NO_AUDIO = "NO_AUDIO"
    DECODE_ERROR = "DECODE_ERROR"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    DISK_FULL = "DISK_FULL"
    MODEL_MISSING = "MODEL_MISSING"
    MODEL_CORRUPT = "MODEL_CORRUPT"
    ENGINE_ERROR = "ENGINE_ERROR"
    ENGINE_CRASH = "ENGINE_CRASH"
    GPU_ERROR = "GPU_ERROR"
    OUTPUT_UNWRITABLE = "OUTPUT_UNWRITABLE"
    STATE_SAVE_FAILED = "STATE_SAVE_FAILED"
    OUTPUT_EXISTS_SKIPPED = "OUTPUT_EXISTS_SKIPPED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(frozen=True)
class Word:
    """One word as the engine wrote it, with its leading space, and how sure it was.

    ``confidence`` is the lowest probability of the word's letter or digit
    tokens, from 0 to 1. Punctuation alone counts as fully sure. ``start`` and
    ``end`` are the engine's token times in seconds, or None when it gave none.
    """

    text: str
    confidence: float
    start: float | None = None
    end: float | None = None


# Values an extension stage attached, as (key, value) pairs; see annotation().
Annotations = tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class Segment:
    index: int
    start: float
    end: float
    text: str
    words: tuple[Word, ...] = ()
    annotations: Annotations = ()


@dataclass(frozen=True)
class Transcript:
    segments: tuple[Segment, ...]
    language: str
    task: Task
    model_id: str
    backend: EngineBackend
    duration_sec: float
    annotations: Annotations = ()


def annotation(item: Segment | Transcript, key: str, default: Any = None) -> Any:
    """The value an extension stage attached under key, or default."""
    return next((value for name, value in item.annotations if name == key), default)


def annotate[T: (Segment, Transcript)](item: T, key: str, value: Any) -> T:
    """A copy of item with value under key, replacing any value it had there."""
    kept: Annotations = tuple(pair for pair in item.annotations if pair[0] != key)
    return replace(item, annotations=(*kept, (key, value)))


@dataclass
class Job:
    source: Path
    id: UUID = field(default_factory=uuid4)
    relative_dir: Path | None = None
    status: JobStatus = JobStatus.QUEUED
    failure: FailureCode | None = None
    progress: float = 0.0
    outputs: list[Path] = field(default_factory=list)
    backend_used: EngineBackend | None = None
    gpu_fallback: bool = False
    duration_sec: float = 0.0
    elapsed_sec: float = 0.0
    # In memory only, never saved: a transcript an extension stage annotated and
    # the hash of each output Dusty wrote, so an extension action can render
    # again in this session without replacing a file someone changed since.
    transcript: Transcript | None = field(default=None, repr=False, compare=False)
    written: dict[Path, str] = field(default_factory=dict, repr=False, compare=False)
    # The status text of the extension stage running, and of one that failed.
    stage_status: str | None = field(default=None, repr=False, compare=False)
    stage_failed: str | None = field(default=None, repr=False, compare=False)


def default_batch_threads() -> int:
    """The default whisper.cpp thread count: the computer's default, at most four.

    More threads than cores make whisper.cpp spin instead of work, so a fixed four
    did not finish on a two-thread computer.
    """
    from dusty.platform.cpu_topology import default_threads

    return min(4, default_threads())


@dataclass(frozen=True)
class BatchOptions:
    model_id: str
    output_dir: Path | None
    formats: tuple[OutputFormat, ...] = ("txt", "docx")
    language: str = "auto"
    task: Task = "transcribe"
    backend: Backend = "auto"
    threads: int = field(default_factory=lambda: default_batch_threads())
    vad: bool = False
    prompt: str = ""
    collision: CollisionPolicy = "ask"
    same_folder: bool = False
    keep_structure: bool = False
    time_markers: bool = False
    marker_minutes: float = MARKER_MINUTES_DEFAULT
    mark_unsure: bool = False
    unsure_level: UnsureLevel = "very"
    # Keys of the extension options that are on.
    extension_options: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.model_id, str) or not self.model_id.strip():
            raise ValueError("Model id must be nonempty")
        if not isinstance(self.output_dir, Path) and not (
            self.same_folder and self.output_dir is None
        ):
            raise ValueError("Output directory must be a path")
        if (
            not isinstance(self.formats, tuple)
            or not self.formats
            or any(fmt not in ("txt", "srt", "vtt", "json", "docx") for fmt in self.formats)
            or len(set(self.formats)) != len(self.formats)
        ):
            raise ValueError("Invalid output formats")
        if self.task not in ("transcribe", "translate"):
            raise ValueError("Invalid task")
        if self.backend not in ("auto", "cpu", "vulkan", "metal"):
            raise ValueError("Invalid backend")
        if self.collision not in ("ask", "skip", "keep_both", "overwrite"):
            raise ValueError("Invalid collision policy")
        if type(self.threads) is not int or self.threads < 1:
            raise ValueError("Threads must be positive")
        if not isinstance(self.language, str) or not self.language.strip():
            raise ValueError("Language must be nonempty")
        if not isinstance(self.prompt, str):
            raise ValueError("Prompt must be text")
        if any(
            type(value) is not bool
            for value in (
                self.vad,
                self.same_folder,
                self.keep_structure,
                self.time_markers,
                self.mark_unsure,
            )
        ):
            raise ValueError("Invalid boolean preference")
        if (
            type(self.marker_minutes) not in (int, float)
            or not math.isfinite(self.marker_minutes)
            or not MARKER_MINUTES_MIN <= self.marker_minutes <= MARKER_MINUTES_MAX
        ):
            raise ValueError("Invalid time marker interval")
        if self.unsure_level not in ("very", "somewhat"):
            raise ValueError("Invalid unsure word level")
        if not isinstance(self.extension_options, frozenset) or any(
            not isinstance(key, str) or not key for key in self.extension_options
        ):
            raise ValueError("Invalid extension options")
