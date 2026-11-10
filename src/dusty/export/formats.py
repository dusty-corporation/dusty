"""Render Dusty transcript formats with controlled line endings and metadata."""

import io
import json
import re
import textwrap
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from pathlib import Path

from dusty import __version__
from dusty.core import Segment, Transcript
from dusty.core.types import UnsureLevel

UNSURE_MARK = "[?]"
UNSURE_NOTE = "Words marked [?] may be wrong. Unmarked words can be wrong too."
# A word is marked when its confidence is below the cut-off of the chosen level.
# Starting values from the measurements in docs/dev/transcript-extras.md; they are
# to be tuned per model on checked recordings before release.
UNSURE_CUTOFFS: dict[UnsureLevel, float] = {"very": 0.5, "somewhat": 0.7}
# Text a sentence can end with, before closing quotes or brackets.
_SENTENCE_ENDS = (".", "?", "!", "\u2026", "\u3002", "\uff1f", "\uff01", "\u061f")
_CLOSERS = "\"'\u201d\u2019\u00bb)]"


@dataclass(frozen=True)
class TextExtras:
    """Optional additions to TXT and DOCX; both off writes exactly the plain files.

    ``marker_sec`` is the time marker interval in whole seconds. ``unsure_below``
    marks words whose confidence is below it.
    """

    marker_sec: int | None = None
    unsure_below: float | None = None

    @classmethod
    def choose(
        cls,
        *,
        time_markers: bool,
        marker_minutes: float,
        mark_unsure: bool,
        unsure_level: UnsureLevel,
    ) -> "TextExtras":
        return cls(
            max(1, round(marker_minutes * 60)) if time_markers else None,
            UNSURE_CUTOFFS[unsure_level] if mark_unsure else None,
        )

    @property
    def active(self) -> bool:
        return self.marker_sec is not None or self.unsure_below is not None


# A run of paragraph text; ``unsure`` runs are words that may be wrong.
Run = tuple[str, bool]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _paragraphs(segments: tuple[Segment, ...]) -> list[tuple[float, str]]:
    paragraphs: list[tuple[float, str]] = []
    current: list[str] = []
    first_start = 0.0
    previous_end = 0.0
    for segment in segments:
        text = _clean(segment.text)
        if not text:
            continue
        if current and segment.start - previous_end >= 2.0:
            paragraphs.append((first_start, " ".join(current)))
            current = []
        if not current:
            first_start = segment.start
        current.append(text)
        previous_end = segment.end
    if current:
        paragraphs.append((first_start, " ".join(current)))
    return paragraphs


def _segment_runs(segment: Segment, unsure_below: float | None) -> list[Run]:
    """Split a segment into runs, marking unsure words with a following [?]."""
    if unsure_below is None or not segment.words:
        return [(segment.text, False)]
    runs: list[Run] = []
    for word in segment.words:
        letters = [index for index, char in enumerate(word.text) if char.isalnum()]
        if not letters or word.confidence >= unsure_below:
            runs.append((word.text, False))
            continue
        first, last = letters[0], letters[-1] + 1
        runs.extend(
            (
                (word.text[:first], False),
                (word.text[first:last], True),
                (" " + UNSURE_MARK + word.text[last:], False),
            )
        )
    return runs


def _clean_runs(runs: list[Run]) -> list[Run]:
    """Collapse whitespace across runs as _clean does, and merge equal neighbours."""
    chars: list[tuple[str, bool]] = []
    for text, unsure in runs:
        for char in text:
            if char.isspace():
                if chars and chars[-1][0] != " ":
                    chars.append((" ", False))
            else:
                chars.append((char, unsure))
    while chars and chars[-1][0] == " ":
        chars.pop()
    merged: list[Run] = []
    for char, unsure in chars:
        if merged and merged[-1][1] == unsure:
            merged[-1] = (merged[-1][0] + char, unsure)
        else:
            merged.append((char, unsure))
    return merged


def _ends_sentence(text: str) -> bool:
    """Read from the engine's plain text, never from runs with [?] marks in them."""
    return text.rstrip().rstrip(_CLOSERS).endswith(_SENTENCE_ENDS)


def _blocks(
    segments: tuple[Segment, ...], extras: TextExtras
) -> list[tuple[float, list[Run] | None]]:
    """Paragraphs as (start, runs) and time markers as (time, None).

    Paragraphs break at pauses of 2 s or more, as in plain files. A marker goes
    before the first sentence or paragraph that starts at or after each multiple
    of the interval, waiting at most 30 s (or a third of the interval) for one.
    It shows the real start of the text after it.
    """
    blocks: list[tuple[float, list[Run] | None]] = []
    current: list[Run] = []
    first_start = 0.0
    previous_end = 0.0
    previous_text = ""
    interval = extras.marker_sec
    next_marker = float(interval) if interval else 0.0
    slack = min(30.0, interval / 3) if interval else 0.0
    for segment in segments:
        if not _clean(segment.text):
            continue
        pause = bool(current) and segment.start - previous_end >= 2.0
        marker = bool(
            interval
            and segment.start >= next_marker
            and (
                not current
                or pause
                or _ends_sentence(previous_text)
                or segment.start >= next_marker + slack
            )
        )
        if current and (marker or pause):
            blocks.append((first_start, _clean_runs(current)))
            current = []
        if marker and interval:
            blocks.append((segment.start, None))
            while next_marker <= segment.start:
                next_marker += interval
        if not current:
            first_start = segment.start
        else:
            current.append((" ", False))
        current.extend(_segment_runs(segment, extras.unsure_below))
        previous_end = segment.end
        previous_text = segment.text
    if current:
        blocks.append((first_start, _clean_runs(current)))
    return blocks


def _clock(seconds: float) -> str:
    return _timestamp(seconds, separator=".").split(".")[0]


def render_txt(transcript: Transcript, extras: TextExtras | None = None) -> bytes:
    if extras is None or not extras.active:
        paragraphs = _paragraphs(transcript.segments)
        if not paragraphs:
            return b""
        return ("\r\n\r\n".join(text for _, text in paragraphs) + "\r\n").encode("utf-8")
    blocks = _blocks(transcript.segments, extras)
    if not blocks:
        return b""
    lines = [UNSURE_NOTE] if extras.unsure_below is not None else []
    for start, runs in blocks:
        lines.append(f"[{_clock(start)}]" if runs is None else "".join(text for text, _ in runs))
    return ("\r\n\r\n".join(lines) + "\r\n").encode("utf-8")


def _timestamp(seconds: float, *, separator: str) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02}{separator}{millis:03}"


def _segment_cues(segment: Segment) -> list[tuple[float, float, str]]:
    text = _clean(segment.text)
    if not text:
        return []
    lines = textwrap.wrap(text, width=42, break_long_words=True, break_on_hyphens=False)
    chunks = ["\n".join(lines[index : index + 2]) for index in range(0, len(lines), 2)]
    total_length = sum(len(chunk.replace("\n", "")) for chunk in chunks)
    duration = max(0.0, segment.end - segment.start)
    cues: list[tuple[float, float, str]] = []
    consumed = 0
    for chunk in chunks:
        start = segment.start + duration * consumed / total_length
        consumed += len(chunk.replace("\n", ""))
        end = segment.start + duration * consumed / total_length
        cues.append((start, end, chunk))
    return cues


def _captions(transcript: Transcript, *, vtt: bool) -> bytes:
    separator = "." if vtt else ","
    lines = ["WEBVTT", ""] if vtt else []
    cue_index = 0
    for segment in transcript.segments:
        for start, end, text in _segment_cues(segment):
            cue_index += 1
            if not vtt:
                lines.append(str(cue_index))
            lines.append(
                f"{_timestamp(start, separator=separator)} --> "
                f"{_timestamp(end, separator=separator)}"
            )
            lines.extend(text.split("\n"))
            lines.append("")
    return ("\r\n".join(lines) + ("\r\n" if lines else "")).encode("utf-8")


def render_srt(transcript: Transcript) -> bytes:
    return _captions(transcript, vtt=False)


def render_vtt(transcript: Transcript) -> bytes:
    return _captions(transcript, vtt=True)


def render_json(
    transcript: Transcript, source: Path, *, created_utc: datetime | None = None
) -> bytes:
    created = created_utc or datetime.now(UTC)
    value = {
        "schema": "dusty.transcript",
        "schema_version": 1,
        "app_version": __version__,
        "model_id": transcript.model_id,
        "backend": transcript.backend,
        "task": transcript.task,
        "language": transcript.language,
        "duration_sec": transcript.duration_sec,
        "source_file_name": source.name,
        "created_utc": created.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "segments": [
            {"index": part.index, "start": part.start, "end": part.end, "text": _clean(part.text)}
            for part in transcript.segments
            if _clean(part.text)
        ],
    }
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


_EXTRA_STYLES = (
    '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/>'
    '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>'
    '<w:pPr><w:keepNext/><w:spacing w:before="240" w:after="80"/><w:outlineLvl w:val="1"/>'
    '</w:pPr><w:rPr><w:b/><w:color w:val="2F5496"/><w:sz w:val="26"/></w:rPr></w:style>'
    '<w:style w:type="paragraph" w:styleId="DustyNote"><w:name w:val="Dusty Note"/>'
    '<w:basedOn w:val="Normal"/><w:rPr><w:i/><w:color w:val="595959"/></w:rPr></w:style>'
)


def render_docx(
    transcript: Transcript,
    source: Path,
    *,
    created_utc: datetime | None = None,
    timestamps: bool = True,
    extras: TextExtras | None = None,
) -> bytes:
    created = created_utc or datetime.now(UTC)
    date = created.astimezone(UTC).strftime("%Y-%m-%d")
    paragraphs: list[tuple[list[Run], str]] = [
        ([(source.stem, False)], "Title"),
        (
            [
                (
                    f"{date} | {transcript.duration_sec:.1f} s | "
                    f"{transcript.model_id} | {transcript.language}",
                    False,
                )
            ],
            "",
        ),
    ]
    note = extras is not None and extras.unsure_below is not None
    if extras is None or not extras.active:
        for start, text in _paragraphs(transcript.segments):
            prefix = f"[{_clock(start)}] " if timestamps else ""
            paragraphs.append(([(prefix + text, False)], ""))
    else:
        blocks = _blocks(transcript.segments, extras)
        if note and blocks:
            paragraphs.append(([(UNSURE_NOTE, False)], "DustyNote"))
        after_marker = False
        for start, runs in blocks:
            if runs is None:
                # A heading, so markers are listed in Word's Navigation pane.
                paragraphs.append(([(_clock(start), False)], "Heading2"))
                after_marker = True
                continue
            # The paragraph right under a marker would repeat its time.
            prefix = f"[{_clock(start)}] " if timestamps and not after_marker else ""
            paragraphs.append(([(prefix, False), *runs] if prefix else runs, ""))
            after_marker = False

    def paragraph(runs: list[Run], style: str) -> str:
        # XML 1.0 excludes control characters and lone surrogates.
        clean = [
            (
                re.sub(r"[^\x09\x0a\x0d\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]", "", text),
                unsure,
            )
            for text, unsure in runs
        ]
        strong = [unicodedata.bidirectional(c) for text, _ in clean for c in text]
        rtl = sum(c in {"R", "AL"} for c in strong) > strong.count("L")
        properties = f'<w:pStyle w:val="{style}"/>' if style else ""
        if rtl:
            properties += "<w:bidi/>"
        properties = f"<w:pPr>{properties}</w:pPr>" if properties else ""
        xml = ""
        for text, unsure in clean:
            run = '<w:rFonts w:cs="Arial"/>' if rtl else ""
            if unsure:
                run += '<w:highlight w:val="yellow"/>'
            if rtl:
                run += "<w:rtl/>"
            run = f"<w:rPr>{run}</w:rPr>" if run else ""
            xml += f'<w:r>{run}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'
        return f"<w:p>{properties}{xml}</w:p>"

    declaration = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    word_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    office_rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    parts = {
        "[Content_Types].xml": (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" '
            'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.'
            'wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.'
            'wordprocessingml.styles+xml"/>'
            '<Override PartName="/docProps/core.xml" '
            'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": (
            f'<Relationships xmlns="{rel_ns}">'
            f'<Relationship Id="rId1" Type="{office_rel}/officeDocument" '
            'Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/'
            'package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            "</Relationships>"
        ),
        "word/_rels/document.xml.rels": (
            f'<Relationships xmlns="{rel_ns}">'
            f'<Relationship Id="rId1" Type="{office_rel}/styles" Target="styles.xml"/>'
            "</Relationships>"
        ),
        "word/document.xml": (
            f'<w:document xmlns:w="{word_ns}"><w:body>'
            + "".join(paragraph(runs, style) for runs, style in paragraphs)
            + "<w:sectPr/></w:body></w:document>"
        ),
        "word/styles.xml": (
            f'<w:styles xmlns:w="{word_ns}">'
            '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
            '<w:name w:val="Normal"/><w:pPr><w:spacing w:after="140"/></w:pPr>'
            '<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" '
            'w:eastAsia="Calibri" w:cs="Calibri"/>'
            '<w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:style>'
            '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/>'
            '<w:basedOn w:val="Normal"/><w:rPr><w:sz w:val="52"/></w:rPr></w:style>'
            + (_EXTRA_STYLES if extras is not None and extras.active else "")
            + "</w:styles>"
        ),
        "docProps/core.xml": (
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"/>'
        ),
    }
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, xml in parts.items():
            archive.writestr(name, (declaration + xml).encode("utf-8"))
    return stream.getvalue()
