"""N-6: Cloud Files tags are not name-surrogate links."""

import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from dusty.core import BatchOptions, Job, Segment, Transcript
from dusty.queue.outputs import write_outputs
from dusty.queue.scanning import scan_inputs


@pytest.mark.parametrize(
    "tag", [0x9000001A, 0x9000101A, 0x9000F01A, 0x80000015, 0x80000017, 0x8000001B]
)
@pytest.mark.parametrize("place", ["file", "ancestor", "output"])
def test_non_surrogate_reparse_tags_allow_recordings_and_outputs(tmp_path, monkeypatch, tag, place):
    folder = tmp_path / "OneDrive" / "Documents"
    folder.mkdir(parents=True)
    source = folder / "lecture.wav"
    source.write_bytes(b"public synthetic fixture")
    target = source if place == "file" else folder
    original = Path.lstat

    def tagged(path):
        value = original(path)
        if path == target:
            return SimpleNamespace(
                st_mode=value.st_mode,
                st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT,
                st_reparse_tag=tag,
            )
        return value

    monkeypatch.setattr(Path, "lstat", tagged)
    result = scan_inputs([source if place == "file" else folder], recursive=True)
    assert len(result.jobs) == 1 and result.rejected == 0
    transcript = Transcript(
        (Segment(0, 0, 1, "Public test"),), "en", "transcribe", "tiny", "cpu", 1
    )
    outputs = write_outputs(Job(source), BatchOptions("tiny", folder, formats=("txt",)), transcript)
    assert outputs[0].read_bytes() == b"Public test\r\n"


@pytest.mark.parametrize("tag", [0xA0000003, 0xA000000C, 0x20000001])
def test_name_surrogate_tags_still_refuse_scan_and_output(tmp_path, monkeypatch, tag):
    folder = tmp_path / "linked"
    folder.mkdir()
    source = folder / "lecture.wav"
    source.touch()
    original = Path.lstat

    def tagged(path):
        value = original(path)
        if path == folder:
            return SimpleNamespace(
                st_mode=value.st_mode,
                st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT,
                st_reparse_tag=tag,
            )
        return value

    monkeypatch.setattr(Path, "lstat", tagged)
    assert not scan_inputs([source]).jobs
    transcript = Transcript((), "en", "transcribe", "tiny", "cpu", 0)
    with pytest.raises(OSError, match="Linked output"):
        write_outputs(Job(source), BatchOptions("tiny", folder, formats=("txt",)), transcript)
