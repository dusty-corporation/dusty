"""Extension points: what an extension may add to Dusty (docs/dev/extensions.md).

Dusty behaves exactly as it does without extensions while nothing is
registered: every point below is a list that is empty then. An extension is
the one package named EXTENSION_PACKAGE; when it is not installed, Dusty has
none. Its ``register(extensions)`` adds:

- ``options``: check boxes in Options, remembered while on;
- ``stages``: steps after transcription and before the outputs are written;
- ``decorations``: labels for paragraphs and captions, and extra JSON fields;
- ``actions``: context menu entries for a finished file of this session;
- ``models``: extra downloadable model files, each with its own catalog file;
- ``helpers``: programs of the extension, started like the engine;
- ``engine_hints``: a prompt for the engine while an option is on;
- ``about``: lines About adds after the version, worked out when it opens;
- ``commands``: entries of the Help menu;
- ``texts``: every text it shows, so the user guide check knows its labels.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID

from dusty.core import Segment, Transcript
from dusty.core.types import Cancellation

if TYPE_CHECKING:
    from dusty.core import BatchOptions, Job

# The one package that may register extensions.
EXTENSION_PACKAGE = "dusty_addons"


@dataclass(frozen=True)
class Option:
    """A check box in Options. Settings and saved queues hold it only while on."""

    key: str
    row: str
    label: str
    help: str
    # Added to the summary of choices while on.
    summary: str
    # Shown, with the box disabled, when ``supported()`` is False; a callable is
    # asked again each time Options refreshes.
    unsupported: str | Callable[[], str]
    supported: Callable[[], bool]
    # The extra model it needs, its start hint while missing, and the button text.
    model: str | None = None
    model_missing: str = ""
    download: str = ""


@dataclass(frozen=True)
class StageInput:
    job_id: UUID
    # The job's decoded 16 kHz WAV, in its owned work folder.
    wav: Path
    transcript: Transcript
    # The verified extra model, when the stage's option needs one.
    model: Path | None
    threads: int
    cancel: Cancellation | None
    on_progress: Callable[[float], None]


class StageFailed(Exception):
    """A stage failed or was cancelled. Carries only a fixed reason, never text or paths."""

    def __init__(self, reason: str, *, cancelled: bool = False):
        super().__init__(reason)
        self.reason = reason
        self.cancelled = cancelled


@dataclass(frozen=True)
class Stage:
    """Runs after transcription, before the outputs are written, while its option is on.

    If it fails, the file is still saved without what it adds, and the list
    shows ``failed`` for it. ``work_files`` are names it may leave in the job's
    owned work folder; they are removed with the job's other work files.
    """

    option: str
    status: str
    failed: str
    run: Callable[[StageInput], Transcript]
    work_files: tuple[str, ...] = ()


class Decoration(Protocol):
    """Labels for paragraphs and captions, and extra JSON fields.

    Used only for a transcript it ``applies`` to. A paragraph of TXT or DOCX
    starts where the label changes, with the label in bold; SRT cues start with
    "label: " and VTT cues carry it as their voice.
    """

    def applies(self, transcript: Transcript) -> bool: ...

    def label(self, transcript: Transcript, segment: Segment) -> str | None: ...

    def json_segment(self, transcript: Transcript, segment: Segment) -> dict[str, Any]: ...

    def json_transcript(self, transcript: Transcript) -> dict[str, Any]: ...


@dataclass(frozen=True)
class Action:
    """A context menu entry for one finished file of this session.

    ``run`` gets the main window, the job and the options it was written
    with. A ``default`` action also runs when the file is double clicked.
    """

    label: str
    available: Callable[[Job], bool]
    run: Callable[[Any, Job, BatchOptions], None]
    default: bool = False


@dataclass(frozen=True)
class ExtraModel:
    """A downloadable model file with its own catalog file in the resources folder.

    The catalog file has the downloader's format: schema_version 1 and a
    ``models`` list holding this one entry.
    """

    id: str
    catalog: str
    name: str
    quality: str
    note: str
    best_for: str


@dataclass(frozen=True)
class Helper:
    """A program frozen next to dusty-fetch; in a source tree, ``python -m module``."""

    name: str
    module: str


@dataclass(frozen=True)
class EngineHint:
    """A prompt the engine gets while ``option`` is on, for these languages only.

    It is used only when the user gave no hints of their own: with hints,
    the engine gets exactly the user's prompt, as without extensions.
    ``carry`` keeps it steering through the whole recording instead of only
    the first window.
    """

    option: str
    languages: frozenset[str]
    prompt: str
    carry: bool = False


@dataclass(frozen=True)
class Command:
    """A Help menu entry; ``run`` gets the main window."""

    label: str
    run: Callable[[Any], None]


def reason(option: Option) -> str:
    """The text Options shows while ``option`` is not supported."""
    return option.unsupported() if callable(option.unsupported) else option.unsupported


@dataclass
class Extensions:
    options: list[Option] = field(default_factory=list)
    stages: list[Stage] = field(default_factory=list)
    decorations: list[Decoration] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    models: list[ExtraModel] = field(default_factory=list)
    helpers: list[Helper] = field(default_factory=list)
    engine_hints: list[EngineHint] = field(default_factory=list)
    about: list[Callable[[], str | None]] = field(default_factory=list)
    commands: list[Command] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)

    def option(self, key: str) -> Option | None:
        return next((option for option in self.options if option.key == key), None)

    def model(self, model_id: str) -> ExtraModel | None:
        return next((model for model in self.models if model.id == model_id), None)

    def decorations_for(self, transcript: Transcript) -> list[Decoration]:
        return [item for item in self.decorations if item.applies(transcript)]


def _package() -> ModuleType | None:
    """The extension package, or None when it is not installed.

    A static import, so the offline checks see exactly what is imported. Any
    other missing module is an error of the installed extension and is raised.
    """
    try:
        # Absent from public Dusty, which mypy checks too.
        import dusty_addons as package  # type: ignore[import-not-found, unused-ignore]
    except ModuleNotFoundError as error:
        if error.name != EXTENSION_PACKAGE:
            raise
        return None
    return package


@cache
def loaded() -> Extensions:
    """The installed extension's registrations; empty when it is not installed."""
    extensions = Extensions()
    package = _package()
    if package is not None:
        package.register(extensions)
    return extensions


_chosen: list[Extensions] = []


def active() -> Extensions:
    """The extensions Dusty uses: those loaded, unless a test chose others."""
    return _chosen[-1] if _chosen else loaded()


@contextmanager
def use(extensions: Extensions) -> Iterator[Extensions]:
    """Use these extensions instead, for tests; ``Extensions()`` is Dusty without any."""
    _chosen.append(extensions)
    try:
        yield extensions
    finally:
        _chosen.pop()


class TextTranslator(Protocol):
    """Future local language-to-language translation after parsing (V2, not used)."""

    def available_pairs(self) -> list[tuple[str, str]]: ...

    def translate(self, transcript: Transcript, target_lang: str) -> Transcript: ...
