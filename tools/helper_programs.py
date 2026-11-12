"""Helper programs of installed add-ons, for the app builds (docs/dev/extensions.md).

Public Dusty has none: without packaging/addons/programs.json every list here
is empty, and the specs, bundle checks, notices and installer build exactly
what Dusty 1.2.0 built. With it, each program is a separate PyInstaller
analysis that the build places next to dusty-fetch:

- Mac: Contents/Helpers/<name>/<name>, its data under Contents/Resources/<name>;
- Windows: <name>/<name>.exe, a console program excluded from Windows Error
  Reporting like the other Dusty programs.
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRAMS = "packaging/addons/programs.json"
# Top-level module names that belong to add-ons; public Dusty's GUI holds none.
ADDON_MODULES = ("dusty_addons",)


@dataclass(frozen=True)
class NoticePackage:
    """A Python package a program bundles, with its pinned license texts (Mac)."""

    key: str
    module: str
    title: str
    license: str
    copyright: str
    url: str
    texts: str
    kind: str


@dataclass(frozen=True)
class Program:
    name: str
    entry: str
    module: str
    # Modules the program's own analysis leaves out, on every platform and on Mac.
    excludes: tuple[str, ...]
    excludes_darwin: tuple[str, ...]
    # Modules the GUI must leave out because only this program uses them.
    gui_excludes: tuple[str, ...]
    # Bundled files PyInstaller collects that the program does not use, per platform.
    drop_binaries: tuple[tuple[str, tuple[str, ...]], ...]
    required_modules: tuple[str, ...]
    forbidden_modules: tuple[str, ...]
    # The macOS version its own libraries need; its folder is left out of the
    # app's minimum, and the add-on gates itself at run time.
    macos_minimum: tuple[int, int, int] | None
    # The smoke test module, run as python -m <check> <built program>.
    check: str
    licenses: str
    notices: tuple[NoticePackage, ...]

    @property
    def mac_dir(self) -> str:
        return f"Contents/Helpers/{self.name}"

    @property
    def mac_data(self) -> str:
        return f"Contents/Resources/{self.name}"

    @property
    def mac_executable(self) -> str:
        return f"{self.mac_dir}/{self.name}"

    @property
    def windows_executable(self) -> str:
        return f"{self.name}/{self.name}.exe"

    @property
    def group(self) -> str:
        """Its key in the build's analysis.json: <group>_pure, _binaries, _datas, _scripts."""
        return self.name.replace("-", "_")

    def all_excludes(self, platform: str) -> list[str]:
        return [*self.excludes, *(self.excludes_darwin if platform == "darwin" else ())]

    def drops(self, name: str, platform: str) -> bool:
        patterns = dict(self.drop_binaries).get("darwin" if platform == "darwin" else "win32", ())
        return any(fnmatch.fnmatch(name.lower(), pattern.lower()) for pattern in patterns)


def _program(item: dict) -> Program:
    minimum = item.get("macos_minimum")
    return Program(
        name=item["name"],
        entry=item["entry"],
        module=item["module"],
        excludes=tuple(item.get("excludes", ())),
        excludes_darwin=tuple(item.get("excludes_darwin", ())),
        gui_excludes=tuple(item.get("gui_excludes", ())),
        drop_binaries=tuple(
            (key, tuple(value)) for key, value in sorted(item.get("drop_binaries", {}).items())
        ),
        required_modules=tuple(item.get("required_modules", ())),
        forbidden_modules=tuple(item.get("forbidden_modules", ())),
        macos_minimum=(
            tuple(int(part) for part in (minimum + ".0.0").split(".")[:3])  # type: ignore[arg-type]
            if minimum
            else None
        ),
        check=item["check"],
        licenses=item.get("licenses", ""),
        notices=tuple(NoticePackage(**package) for package in item.get("notices", ())),
    )


def load_programs(root: Path = ROOT) -> tuple[Program, ...]:
    """The add-on programs to build; none when packaging/addons is not there."""
    path = root / PROGRAMS
    if not path.is_file():
        return ()
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError(f"Unknown schema in {PROGRAMS}")
    programs = tuple(_program(item) for item in data["programs"])
    names = [program.name for program in programs]
    if len(set(names)) != len(names) or any(
        name in {"dusty", "dusty-fetch"} or not name.startswith("dusty-") for name in names
    ):
        raise ValueError(f"Invalid program names in {PROGRAMS}")
    return programs


def addon_module(name: str) -> bool:
    """True for a module that belongs to an add-on."""
    return name.split(".")[0] in ADDON_MODULES


def gui_module_findings(modules: list[str] | set[str], programs: tuple[Program, ...]) -> list[str]:
    """The GUI never embeds a program's own modules; public Dusty's GUI no add-on at all."""
    findings = []
    excluded = {name for program in programs for name in program.gui_excludes}
    for name in sorted(set(modules)):
        if not programs and addon_module(name):
            findings.append(f"Public GUI embeds add-on module {name}")
        elif any(name == item or name.startswith(item + ".") for item in excluded):
            findings.append(f"GUI embeds helper program module {name}")
    return findings
