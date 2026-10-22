"""Verify supported-folder scanning and complete actionable failure mapping."""

from pathlib import Path

from dusty.core import FailureCode, Job
from dusty.core.failures import FAILURE_MESSAGES
from dusty.queue.scanning import SUPPORTED_EXTENSIONS, scan_inputs


def test_scan_filters_recurses_and_deduplicates(tmp_path: Path) -> None:
    folder = tmp_path / "recordings"
    nested = folder / "nested"
    nested.mkdir(parents=True)
    wav = folder / "one.WAV"
    wav.touch()
    (folder / "notes.txt").touch()
    other = nested / "two.mp3"
    other.touch()
    shallow = scan_inputs([folder])
    assert [job.source for job in shallow.jobs] == [wav.resolve()]
    assert shallow.unsupported == 1
    deep = scan_inputs([folder, wav, folder / "../recordings/one.WAV"], recursive=True)
    assert {job.source for job in deep.jobs} == {wav.resolve(), other.resolve()}
    assert deep.unsupported == 1
    assert deep.duplicates == 2
    assert next(job for job in deep.jobs if job.source == other).relative_dir == Path("nested")
    existing = scan_inputs([folder], recursive=True, existing=[Job(wav)])
    assert [job.source for job in existing.jobs] == [other.resolve()]
    assert existing.duplicates == 1


def test_scan_includes_every_verified_extension(tmp_path: Path) -> None:
    for extension in SUPPORTED_EXTENSIONS:
        (tmp_path / ("clip" + extension.upper())).touch()
    result = scan_inputs([tmp_path])
    assert len(result.jobs) == 17
    assert result.unsupported == result.duplicates == 0


def test_every_failure_has_a_plain_explanation_and_action() -> None:
    assert set(FAILURE_MESSAGES) == set(FailureCode)
    for explanation in FAILURE_MESSAGES.values():
        assert explanation.message.strip()
        assert explanation.action.strip()
        assert "\\" not in explanation.message + explanation.action
