"""Compute public-reference WER from benchmark CSV and engine JSON files."""

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path

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


def transcript(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    return " ".join(segment["text"] for segment in data["transcription"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    reference = args.reference.read_text(encoding="utf-8")
    with args.csv.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    lines = [
        "# Accuracy and speed summary",
        "",
        "| Model | Backend | RTF | WER |",
        "| --- | --- | ---: | ---: |",
    ]
    for row in rows:
        if row["sample"] != "public":
            raise ValueError("WER can only be computed for public reference runs")
        name = (
            f"public-{row['machine']}-{row['model']}-{row['backend_requested']}-"
            f"t{row['threads']}.json"
        )
        wer = word_error_rate(reference, transcript(args.results / name))
        lines.append(f"| {row['model']} | {row['backend_actual']} | {row['rtf']} | {wer:.4f} |")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
