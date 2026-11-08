"""Verify supported-folder scanning and complete actionable failure mapping."""

import subprocess
import sys
from pathlib import Path

import pytest

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


@pytest.mark.parametrize("mac", [True, False])
def test_mac_skips_appledouble_sidecars_but_windows_scans_them_as_before(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mac: bool
) -> None:
    import dusty.queue.scanning as scanning

    # macOS writes "._name" metadata sidecars next to files on FAT and exFAT.
    monkeypatch.setattr(scanning, "_SKIP_APPLEDOUBLE", mac, raising=False)
    folder = tmp_path / "card"
    (folder / "nested").mkdir(parents=True)
    for relative in ("clip.wav", "nested/take.mp3"):
        recording = folder / relative
        recording.write_bytes(b"synthetic audio")
        sidecar = recording.with_name("._" + recording.name)
        sidecar.write_bytes(b"\x00\x05\x16\x07\x00\x02\x00\x00")
    # A user file that only looks like a sidecar by name is still a recording.
    (folder / "._named by user.wav").write_bytes(b"synthetic audio")
    result = scan_inputs([folder], recursive=True)
    names = sorted(job.source.name for job in result.jobs)
    if mac:
        assert names == ["._named by user.wav", "clip.wav", "take.mp3"]
        assert result.unsupported == 2
    else:
        assert names == ["._clip.wav", "._named by user.wav", "._take.mp3", "clip.wav", "take.mp3"]
        assert result.unsupported == 0
    assert len(scan_inputs([folder / "._clip.wav"]).jobs) == (0 if mac else 1)


def test_every_failure_has_a_plain_explanation_and_action() -> None:
    assert set(FAILURE_MESSAGES) == set(FailureCode)
    for explanation in FAILURE_MESSAGES.values():
        assert explanation.message.strip()
        assert explanation.action.strip()
        assert "\\" not in explanation.message + explanation.action


# The symlink case covers the same loop refusal on macOS.
@pytest.mark.parametrize(
    "kind",
    [
        pytest.param(
            "junction",
            marks=pytest.mark.skipif(
                sys.platform != "win32",
                reason="Windows-only: NTFS junction made with cmd mklink /J",
            ),
        ),
        "symlink",
    ],
)
def test_recursive_scan_never_follows_links_or_junction_loops(tmp_path, kind):
    folder = tmp_path / "recordings"
    folder.mkdir()
    source = folder / "one.wav"
    source.touch()
    link = folder / "loop"
    if kind == "junction":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(folder)], check=True, capture_output=True
        )
    else:
        link.symlink_to(folder, target_is_directory=True)
    try:
        result = scan_inputs([folder], recursive=True)
        assert len(result.jobs) == 1
        assert result.duplicates == 0
        assert scan_inputs([link], recursive=True).jobs == ()
    finally:
        link.rmdir() if kind == "junction" else link.unlink()
