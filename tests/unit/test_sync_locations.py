"""Verify documented Google Drive streaming mounts without writing registry keys."""

import os
from pathlib import Path

import pytest

from dusty.platform.sync_locations import google_drive_roots


@pytest.mark.skipif(os.name != "nt", reason="Windows mount paths")
def test_google_drive_registry_precedence_and_drive_letter(tmp_path: Path) -> None:
    calls = []

    def read(scope, key):
        calls.append((scope, key))
        return "H:" if scope == "user" else None

    assert google_drive_roots({}, reader=read) == (Path("H:/"),)
    assert calls == [
        ("machine", r"Software\Policies\Google\DriveFS"),
        ("user", r"Software\Google\DriveFS"),
    ]
    assert google_drive_roots({}, reader=lambda *args: str(tmp_path)) == (tmp_path,)
    assert google_drive_roots({}, reader=lambda *args: r"\\server\share") == ()
    assert google_drive_roots(
        {"CLOUD_ROOT": str(tmp_path)}, reader=lambda *args: "%CLOUD_ROOT%"
    ) == (tmp_path,)


@pytest.mark.skipif(os.name != "nt", reason="Windows mount paths")
def test_google_drive_default_requires_local_drivefs_presence(tmp_path: Path) -> None:
    env = {"LOCALAPPDATA": str(tmp_path)}
    assert google_drive_roots(env, reader=lambda *args: None) == ()
    (tmp_path / "Google/DriveFS").mkdir(parents=True)
    assert google_drive_roots(env, reader=lambda *args: None) == (Path("G:/"),)
