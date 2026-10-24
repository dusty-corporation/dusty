"""Audit actual Unicode shell links, retaining the two-shortcut/bare-route gates."""

import ctypes as C
from pathlib import Path

import pytest

from tools.audit_shortcuts import audit, checked, method, read_shortcut, shell_link


def write_link(file: Path, target: Path, arguments=""):
    with shell_link() as (link, persist):
        checked(method(link, 20, C.c_wchar_p)(link, str(target)))
        checked(method(link, 11, C.c_wchar_p)(link, arguments))
        checked(method(persist, 6, C.c_wchar_p, C.c_int)(persist, str(file), 1))


@pytest.mark.parametrize("uninstaller_name", ["unins000.exe", "UNINS000.EXE"])
def test_unicode_shortcuts_are_read_without_resolution_or_target_execution(
    tmp_path, uninstaller_name
):
    install = tmp_path / "App install گفتگو 日本語"
    target = install / "dusty/dusty.exe"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"not executable; audit must never launch it")
    roots = [tmp_path / "Programs", tmp_path / "Desktop"]
    for root in roots:
        root.mkdir()
        file = root / "Dusty.lnk"
        write_link(file, target)
        assert read_shortcut(file) == (str(target), "")
    assert len(audit(install, roots)) == 2
    bare = roots[0] / "Uninstall.lnk"
    uninstaller = install / uninstaller_name
    write_link(bare, uninstaller)
    with pytest.raises(ValueError, match="bare uninstaller"):
        audit(install, roots)
    write_link(bare, uninstaller, "/SILENT /DUSTYCONFIRM=yes")
    entries = audit(install, roots)
    assert len(entries) == 3
    assert any(entry["arguments"] == "/SILENT /DUSTYCONFIRM=yes" for entry in entries)


def test_missing_app_shortcut_still_fails(tmp_path):
    with pytest.raises(ValueError, match="Expected Start Menu"):
        audit(tmp_path / "App", [tmp_path])
