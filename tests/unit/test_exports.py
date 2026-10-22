"""Check transcript format boundaries, metadata, and caption limits."""

import io
import json
from datetime import UTC, datetime
from pathlib import Path

from docx import Document

from dusty.core import Segment, Transcript
from dusty.export import render_docx, render_json, render_srt, render_txt, render_vtt


def sample_transcript() -> Transcript:
    return Transcript(
        segments=(
            Segment(0, 0.0, 1.0, "  Hello   world.  "),
            Segment(1, 1.2, 2.0, "Another line."),
            Segment(2, 4.0, 7.0, "This is a later paragraph."),
        ),
        language="en",
        task="transcribe",
        model_id="tiny",
        backend="cpu",
        duration_sec=7.0,
    )


def test_txt_paragraph_gap_and_empty_transcript() -> None:
    transcript = sample_transcript()
    assert render_txt(transcript) == (
        b"Hello world. Another line.\r\n\r\nThis is a later paragraph.\r\n"
    )
    assert render_txt(Transcript((), "en", "transcribe", "tiny", "cpu", 0)) == b""


def test_captions_split_long_text_into_short_lines() -> None:
    words = " ".join(["transcription"] * 20)
    transcript = Transcript((Segment(0, 0, 10, words),), "en", "transcribe", "tiny", "cpu", 10)
    for render in (render_srt, render_vtt):
        content = render(transcript).decode("utf-8")
        assert "00:00:00" in content
        assert "00:00:10" in content
        text_lines = [line for line in content.splitlines() if "transcription" in line]
        assert len(text_lines) > 2
        assert all(len(line) <= 42 for line in text_lines)
    assert render_vtt(transcript).startswith(b"WEBVTT\r\n\r\n")
    assert b"00:00:00,000 -->" in render_srt(transcript)


def test_json_uses_basename_only_and_no_hidden_path() -> None:
    payload = render_json(
        sample_transcript(),
        Path("C:/private/recording.wav"),
        created_utc=datetime(2026, 10, 22, tzinfo=UTC),
    )
    output = json.loads(payload)
    assert output["source_file_name"] == "recording.wav"
    assert output["created_utc"] == "2026-10-22T00:00:00Z"
    assert "C:/private" not in payload.decode("utf-8")
    assert len(output["segments"]) == 3


def test_docx_clears_author_metadata() -> None:
    payload = render_docx(sample_transcript(), Path("recording.wav"))
    document = Document(io.BytesIO(payload))
    assert document.core_properties.author == ""
    assert document.core_properties.last_modified_by == ""
    assert document.paragraphs[0].text == "recording"
    assert any("Hello world." in paragraph.text for paragraph in document.paragraphs)
