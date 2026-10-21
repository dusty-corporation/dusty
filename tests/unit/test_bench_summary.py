"""Verify the benchmark word normalization and edit-distance calculation."""

from tools.bench.summarize_bench import word_error_rate, words


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
