"""Typed values shared by the headless pipeline and the future GUI."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid4

Backend = Literal["auto", "cpu", "vulkan"]
Task = Literal["transcribe", "translate"]
OutputFormat = Literal["txt", "srt", "vtt", "json", "docx"]
CollisionPolicy = Literal["ask", "skip", "overwrite", "keep_both"]


class JobStatus(str, Enum):
    QUEUED = "queued"
    PREFLIGHT = "preflight"
    DECODING = "decoding"
    TRANSCRIBING = "transcribing"
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
    OUTPUT_EXISTS_SKIPPED = "OUTPUT_EXISTS_SKIPPED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(frozen=True)
class Segment:
    index: int
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Transcript:
    segments: tuple[Segment, ...]
    language: str
    task: Task
    model_id: str
    backend: Literal["cpu", "vulkan"]
    duration_sec: float


@dataclass
class Job:
    source: Path
    id: UUID = field(default_factory=uuid4)
    relative_dir: Path | None = None
    status: JobStatus = JobStatus.QUEUED
    failure: FailureCode | None = None
    progress: float = 0.0
    outputs: list[Path] = field(default_factory=list)
    backend_used: Literal["cpu", "vulkan"] | None = None
    gpu_fallback: bool = False


@dataclass(frozen=True)
class BatchOptions:
    model_id: str
    output_dir: Path
    formats: tuple[OutputFormat, ...] = ("txt", "docx")
    language: str = "auto"
    task: Task = "transcribe"
    backend: Backend = "auto"
    threads: int = 4
    vad: bool = True
    prompt: str = ""
    collision: CollisionPolicy = "ask"
    same_folder: bool = False
    keep_structure: bool = False
