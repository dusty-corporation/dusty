"""Compute public-reference WER from benchmark CSV and engine JSON files."""

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

ONES = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen"
).split()
TENS = "zero ten twenty thirty forty fifty sixty seventy eighty ninety".split()


def number_words(value: int) -> list[str]:
    if value < 20:
        return [ONES[value]]
    if value < 100:
        tens, ones = divmod(value, 10)
        return [TENS[tens]] + (number_words(ones) if ones else [])
    if value < 1000:
        hundreds, rest = divmod(value, 100)
        return [ONES[hundreds], "hundred"] + (number_words(rest) if rest else [])
    if value < 10000:
        thousands, rest = divmod(value, 1000)
        return [ONES[thousands], "thousand"] + (number_words(rest) if rest else [])
    return [str(value)]


def words(text: str) -> list[str]:
    """Normalize NFKC, case, punctuation, and integer digits 0 through 9999."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = re.sub(r"(?<=\w)['’](?=\w)", "", normalized)
    tokens = re.findall(r"\d+|[a-z]+", normalized)
    result = []
    for token in tokens:
        result.extend(number_words(int(token)) if token.isdecimal() else [token])
    return result


def edit_distance(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for row, expected in enumerate(reference, 1):
        current = [row]
        for column, actual in enumerate(hypothesis, 1):
            cost = 0 if expected == actual else 1
            current.append(min(current[-1] + 1, previous[column] + 1, previous[column - 1] + cost))
        previous = current
    return previous[-1]


def word_error_rate(reference: str, hypothesis: str) -> float:
    expected = words(reference)
    if not expected:
        raise ValueError("Reference transcript has no words")
    return edit_distance(expected, words(hypothesis)) / len(expected)


def timestamp_ms(value: str) -> int:
    match = re.fullmatch(r"(\d+):(\d{2}):(\d{2}),(\d{3})", value)
    if match is None:
        raise ValueError("Invalid engine timestamp")
    hours, minutes, seconds, milliseconds = map(int, match.groups())
    return ((hours * 60 + minutes) * 60 + seconds) * 1000 + milliseconds


def scored_spans(reference: str, path: Path) -> list[tuple[int, int, str]]:
    config = json.loads(path.read_text(encoding="utf-8"))
    lines = reference.splitlines()
    spans = []
    previous_end = 0
    for item in config["spans"]:
        start, end = item["start_ms"], item["end_ms"]
        first, last = item["first_line"], item["last_line"]
        if start < previous_end or end <= start or first < 1 or last > len(lines) or last < first:
            raise ValueError("Invalid scored span")
        source_text = "\n".join(lines[first - 1 : last])
        if not words(source_text):
            raise ValueError("Empty scored reference span")
        spans.append((start, end, source_text))
        previous_end = end
    if not spans:
        raise ValueError("No scored spans")
    return spans


def scored_transcript(path: Path, spans: list[tuple[int, int, str]]) -> list[str]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    result: list[list[str]] = [[] for _ in spans]
    for segment in data["transcription"]:
        tokens = [token for token in segment["tokens"] if token["id"] < 50257]
        if "".join(token["text"] for token in tokens) != segment["text"]:
            raise ValueError("Engine text and tokens disagree")
        for token in tokens:
            start = timestamp_ms(token["timestamps"]["from"])
            end = timestamp_ms(token["timestamps"]["to"])
            for index, (span_start, span_end, _) in enumerate(spans):
                if start >= span_start and end <= span_end:
                    result[index].append(token["text"])
                    break
    return ["".join(parts) for parts in result]


def scored_word_error_rate(path: Path, spans: list[tuple[int, int, str]]) -> float:
    hypotheses = scored_transcript(path, spans)
    reference_count = 0
    errors = 0
    for (_, _, reference), hypothesis in zip(spans, hypotheses, strict=True):
        expected = words(reference)
        reference_count += len(expected)
        errors += edit_distance(expected, words(hypothesis))
    return errors / reference_count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--spans", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    reference = args.reference.read_text(encoding="utf-8")
    spans = scored_spans(reference, args.spans)
    with args.csv.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    lines = [
        "# Accuracy and speed summary",
        "",
        "| Model | Backend | Threads | RTF | WER |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in rows:
        if row["sample"] != "public":
            raise ValueError("WER can only be computed for public reference runs")
        mode_prefix = {
            "quick": "quick-",
            "quick_sweep": "quick-sweep-",
        }.get(row.get("run_mode", "full"), "")
        name = (
            f"public-{row['machine']}-{mode_prefix}{row['model']}-{row['backend_requested']}-"
            f"t{row['threads']}.json"
        )
        wer = scored_word_error_rate(args.results / name, spans)
        lines.append(
            f"| {row['model']} | {row['backend_actual']} | {row['threads']} | "
            f"{row['rtf']} | {wer:.4f} |"
        )
    print("\n".join(lines))


if __name__ == "__main__":
    main()
