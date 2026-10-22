"""V2 interfaces only; no V1 diarization or text-translation implementation."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from dusty.core import Transcript


@dataclass(frozen=True)
class SpeakerTurn:
    start: float
    end: float
    speaker: str


class Diarizer(Protocol):
    """Future local speaker labeling after native transcript parsing."""

    def diarize(self, wav_path: Path) -> list[SpeakerTurn]: ...


class TextTranslator(Protocol):
    """Future local language-to-language translation after parsing."""

    def available_pairs(self) -> list[tuple[str, str]]: ...

    def translate(self, transcript: Transcript, target_lang: str) -> Transcript: ...
