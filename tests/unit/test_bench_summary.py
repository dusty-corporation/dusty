"""Verify the benchmark word normalization and edit-distance calculation."""

import json
from pathlib import Path

from tools.bench.summarize_bench import (
    scored_spans,
    scored_word_error_rate,
    word_error_rate,
    words,
)


def test_normalization_handles_case_punctuation_and_numbers() -> None:
    assert words("ONE hundred-and-23, don't stop!") == [
        "one",
        "hundred",
        "and",
        "twenty",
        "three",
        "dont",
        "stop",
    ]


def test_word_error_rate_counts_substitution_insertion_and_deletion() -> None:
    assert word_error_rate("one two three", "one four three") == 1 / 3
    assert word_error_rate("one two three", "one two three four") == 1 / 3
    assert word_error_rate("one two three", "one three") == 1 / 3


def test_scored_spans_exclude_nonsource_lines() -> None:
    root = Path(__file__).parents[1] / "fixtures/audio/bench"
    reference = (root / "swineherd-reference.txt").read_text(encoding="utf-8")
    spans = scored_spans(reference, root / "swineherd-scored-spans.json")
    assert [(start, end) for start, end, _ in spans] == [
        (8000, 248000),
        (256000, 334000),
        (343000, 642000),
    ]
    assert all("All is gone, gone, gone!" not in text for _, _, text in spans)
    assert all("LibriVox recording" not in text for _, _, text in spans)


def test_scored_wer_ignores_tokens_outside_source_spans(tmp_path: Path) -> None:
    def token(text: str, start: int, end: int) -> dict[str, object]:
        def clock(value: int) -> str:
            return f"00:00:{value // 1000:02d},{value % 1000:03d}"

        return {
            "id": 10,
            "text": text,
            "timestamps": {"from": clock(start), "to": clock(end)},
        }

    tokens = [
        token("untrusted intro ", 0, 500),
        token("hello ", 1000, 1500),
        token("world", 1500, 2000),
        token("untrusted song", 2500, 2800),
        token("again", 3000, 3500),
        token("untrusted outro", 4500, 4800),
    ]
    sample = {
        "transcription": [{"text": "".join(item["text"] for item in tokens), "tokens": tokens}]
    }
    path = tmp_path / "public.json"
    path.write_text(json.dumps(sample), encoding="utf-8")
    assert scored_word_error_rate(path, [(1000, 2000, "hello world"), (3000, 4000, "again")]) == 0
