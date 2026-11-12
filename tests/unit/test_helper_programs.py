"""Add-on helper programs in the app builds (tools/helper_programs.py).

Public Dusty has no packaging/addons/programs.json: no helper program is built,
checked or registered, and its GUI may embed no add-on module. A made up
program shows what a programs.json adds.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools import check_macos_bundle, helper_programs
from tools.helper_programs import gui_module_findings, load_programs

ROOT = Path(__file__).resolve().parents[2]
NOTES = {
    "name": "dusty-notes",
    "entry": "packaging/addons/notes_entry.py",
    "module": "dusty_addons.notes.helper",
    "excludes": ["PySide6"],
    "excludes_darwin": ["_scproxy"],
    "gui_excludes": ["dusty_addons.notes.helper", "notes_runtime"],
    "drop_binaries": {"win32": ["unused.dll"], "darwin": ["libunused.*"]},
    "required_modules": ["dusty_addons.notes.helper"],
    "forbidden_modules": ["PySide6", "socket"],
    "macos_minimum": "15.2",
    "check": "tools.check_notes_example",
}


def programs_file(root: Path, *programs: dict) -> Path:
    path = root / helper_programs.PROGRAMS
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "programs": list(programs)}))
    return path


def test_without_programs_json_there_are_no_helper_programs(tmp_path) -> None:
    assert load_programs(tmp_path) == ()


def test_a_program_is_read_with_its_places(tmp_path) -> None:
    programs_file(tmp_path, NOTES)
    (program,) = load_programs(tmp_path)
    assert program.mac_executable == "Contents/Helpers/dusty-notes/dusty-notes"
    assert program.mac_data == "Contents/Resources/dusty-notes"
    assert program.windows_executable == "dusty-notes/dusty-notes.exe"
    assert program.group == "dusty_notes"
    assert program.macos_minimum == (15, 2, 0)
    assert program.all_excludes("darwin") == ["PySide6", "_scproxy"]
    assert program.all_excludes("win32") == ["PySide6"]
    assert program.drops("Unused.DLL", "win32") and not program.drops("unused.dll", "darwin")
    assert program.drops("libunused.1.dylib", "darwin")


@pytest.mark.parametrize("name", ["dusty", "dusty-fetch", "notes", "dusty-notes,dusty-notes"])
def test_program_names_are_checked(tmp_path, name) -> None:
    programs_file(tmp_path, *({**NOTES, "name": part} for part in name.split(",")))
    with pytest.raises(ValueError):
        load_programs(tmp_path)


def test_the_public_gui_holds_no_add_on_module() -> None:
    modules = ["dusty.app.window", "dusty_addons", "dusty_addons.notes.labeler"]
    assert gui_module_findings(modules, ()) == [
        "Public GUI embeds add-on module dusty_addons",
        "Public GUI embeds add-on module dusty_addons.notes.labeler",
    ]
    assert gui_module_findings(["dusty.app.window", "dusty_fetch_like"], ()) == []


def test_no_gui_holds_a_helper_programs_own_modules(tmp_path) -> None:
    programs_file(tmp_path, NOTES)
    programs = load_programs(tmp_path)
    modules = ["dusty_addons", "dusty_addons.notes.helper.run", "notes_runtime"]
    assert gui_module_findings(modules, programs) == [
        "GUI embeds helper program module dusty_addons.notes.helper.run",
        "GUI embeds helper program module notes_runtime",
    ]


def test_the_mac_bundle_holds_only_known_helper_folders(tmp_path) -> None:
    app = tmp_path / "Dusty.app"
    for folder in ("bin", "dusty-fetch", "dusty-notes"):
        (app / "Contents/Helpers" / folder).mkdir(parents=True)
    findings = check_macos_bundle.helper_folder_findings(app, "Contents/Helpers/bin", ())
    assert findings == ["Unexpected helper folder: Contents/Helpers/dusty-notes"]
    programs_file(tmp_path, NOTES)
    programs = load_programs(tmp_path)
    assert check_macos_bundle.helper_folder_findings(app, "Contents/Helpers/bin", programs) == []


def test_the_helper_program_check_passes_without_programs(monkeypatch) -> None:
    from tools import check_helper_programs

    monkeypatch.setattr(check_helper_programs, "load_programs", lambda: ())
    assert check_helper_programs.main(["--mac-app", "Dusty.app"]) == 0
    assert check_helper_programs.main(["--windows-bundle", "dist/Dusty"]) == 0


def test_the_helper_program_check_runs_each_programs_check(tmp_path, monkeypatch) -> None:
    from tools import check_helper_programs

    programs_file(tmp_path, NOTES)
    programs = load_programs(tmp_path)
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(check_helper_programs, "load_programs", lambda: programs)
    monkeypatch.setattr(check_helper_programs, "run", lambda *args: calls.append(args) or 0)
    assert check_helper_programs.main(["--mac-app", "Dusty.app"]) == 0
    assert [as_posix(call) for call in calls] == [
        ("-m", "tools.check_notes_example", "Dusty.app/Contents/Helpers/dusty-notes/dusty-notes")
    ]
    calls.clear()
    monkeypatch.setattr(check_helper_programs, "run", lambda *args: calls.append(args) or 1)
    assert check_helper_programs.main(["--windows-bundle", "dist"]) == 1
    assert as_posix(calls[0])[:2] == ("tools/check_pe_imports.py", "dist/dusty-notes")
    assert as_posix(calls[1]) == (
        "-m",
        "tools.check_notes_example",
        "dist/dusty-notes/dusty-notes.exe",
    )


def as_posix(call: tuple[str, ...]) -> tuple[str, ...]:
    """The arguments with this computer's path separator written as /."""
    return tuple(argument.replace(os.sep, "/") for argument in call)


def test_shared_build_files_never_name_a_helper_program() -> None:
    """Shared build files reach helper programs only through tools/helper_programs.py."""
    names = {item for program in load_programs() for item in (program.name, program.module)}
    tracked = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "packaging", "installer", "tools", ".github"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    for name in tracked:
        path = ROOT / name
        addon = {"addons", "dusty_addons"} & set(Path(name).parts[:-1])
        if addon or not path.is_file() or path.suffix in {".png", ".icns", ".ico"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for item in names:
            assert item not in text, (name, item)


@pytest.mark.skipif(sys.platform != "darwin", reason="Reads the Mac spec's helper loop")
def test_the_specs_read_the_programs() -> None:
    for name in ("dusty.spec", "dusty-macos.spec"):
        text = (ROOT / "packaging" / name).read_text(encoding="utf-8")
        assert "load_programs(root)" in text and "gui_module_findings" in text
