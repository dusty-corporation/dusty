"""Reject state files and non-image material in screenshot review assets."""

import zipfile

import pytest

from tools.check_screenshot_zip import check


@pytest.mark.parametrize("extra", [None, "state/settings.json", "../image.png", "audio.wav"])
def test_screenshot_archive_allowlist(tmp_path, extra):
    path = tmp_path / "review.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("README.md", "Synthetic review captures")
        archive.writestr("light-1/page.png", b"\x89PNG\r\n\x1a\nexample")
        if extra:
            archive.writestr(extra, b"unwanted")
    assert check(path) is (extra is None)
