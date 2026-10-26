"""Render Dusty transcript formats with controlled line endings and metadata."""

import io
import json
import re
import textwrap
import unicodedata
import zipfile
from datetime import UTC, datetime
from html import escape
from pathlib import Path

from dusty import __version__
from dusty.core import Segment, Transcript


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


def render_txt(transcript: Transcript) -> bytes:
    paragraphs = _paragraphs(transcript.segments)
    if not paragraphs:
        return b""
    return ("\r\n\r\n".join(text for _, text in paragraphs) + "\r\n").encode("utf-8")


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


def render_docx(
    transcript: Transcript,
    source: Path,
    *,
    created_utc: datetime | None = None,
    timestamps: bool = True,
) -> bytes:
    created = created_utc or datetime.now(UTC)
    date = created.astimezone(UTC).strftime("%Y-%m-%d")
    paragraphs = [
        (source.stem, "Title"),
        (
            f"{date} | {transcript.duration_sec:.1f} s | "
            f"{transcript.model_id} | {transcript.language}",
            "",
        ),
    ]
    for start, text in _paragraphs(transcript.segments):
        prefix = f"[{_timestamp(start, separator='.').split('.')[0]}] " if timestamps else ""
        paragraphs.append((prefix + text, ""))

    def paragraph(text: str, style: str) -> str:
        # XML 1.0 excludes control characters and lone surrogates.
        clean = re.sub(r"[^\x09\x0a\x0d\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]", "", text)
        strong = [unicodedata.bidirectional(c) for c in clean]
        rtl = sum(c in {"R", "AL"} for c in strong) > strong.count("L")
        properties = f'<w:pStyle w:val="{style}"/>' if style else ""
        if rtl:
            properties += "<w:bidi/>"
        properties = f"<w:pPr>{properties}</w:pPr>" if properties else ""
        run = '<w:rPr><w:rFonts w:cs="Arial"/><w:rtl/></w:rPr>' if rtl else ""
        return (
            f'<w:p>{properties}<w:r>{run}<w:t xml:space="preserve">'
            f"{escape(clean)}</w:t></w:r></w:p>"
        )

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
            + "".join(paragraph(text, style) for text, style in paragraphs)
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
            "</w:styles>"
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
