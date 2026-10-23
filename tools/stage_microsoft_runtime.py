"""Copy only the ADR 0020 CRT names from an installed VS 2022 release redist."""

import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pefile  # type: ignore[import-untyped]

from tools.check_pe_imports import imports

PINS = Path(__file__).resolve().parents[1] / "packaging/microsoft-runtime.json"


def runtime_pins() -> dict:
    return json.loads(PINS.read_text(encoding="utf-8"))


def file_version(path: Path) -> str:
    with pefile.PE(str(path)) as executable:
        fixed = executable.VS_FIXEDFILEINFO[0]
        return ".".join(
            str(value)
            for value in (
                fixed.FileVersionMS >> 16,
                fixed.FileVersionMS & 0xFFFF,
                fixed.FileVersionLS >> 16,
                fixed.FileVersionLS & 0xFFFF,
            )
        )


def crt_importers(bundle: Path) -> dict[str, list[str]]:
    """Normal and delayed imports, scoped to each executable family."""
    result: dict[str, list[str]] = {}
    for path in sorted(bundle.rglob("*")):
        if not path.is_file():
            continue
        with path.open("rb") as stream:
            if stream.read(2) != b"MZ":
                continue
        relative = path.relative_to(bundle)
        for name in imports(path):
            if is_crt(name) and name != path.name.lower():
                result.setdefault(relative.parts[0] + "/" + name, []).append(relative.as_posix())
    return result


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def is_crt(name: str) -> bool:
    return any(
        fnmatch.fnmatchcase(name.lower(), pattern)
        for pattern in ("vcruntime140*.dll", "msvcp140*.dll")
    )


def microsoft_vendor(path: Path) -> bool:
    with path.open("rb") as stream:
        if stream.read(2) != b"MZ":
            return False
    with pefile.PE(str(path)) as executable:
        for group in getattr(executable, "FileInfo", []):
            for info in group:
                for table in getattr(info, "StringTable", []):
                    company = table.entries.get(b"CompanyName", b"").decode("utf-8", "replace")
                    if "microsoft" in company.lower():
                        return True
    return False


def find_redist() -> Path:
    override = os.environ.get("DUSTY_VC_REDIST")
    if override:
        return Path(override).resolve()
    program_files = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
    locator = program_files / "Microsoft Visual Studio/Installer/vswhere.exe"
    if not locator.is_file():
        raise ValueError("VS 2022 redist unavailable; set DUSTY_VC_REDIST to its VC/redist folder")
    result = subprocess.run(
        [
            str(locator),
            "-latest",
            "-version",
            "[17.0,18.0)",
            "-products",
            "*",
            "-property",
            "installationPath",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    if not result.stdout.strip():
        raise ValueError("VS 2022 installation not found")
    return Path(result.stdout.strip()) / "VC/redist"


def valid_source(source: Path, redist: Path) -> bool:
    source, redist = source.resolve(), redist.resolve()
    relative = source.relative_to(redist)
    return (
        redist.name.lower() == "redist"
        and redist.parent.name.lower() == "vc"
        and relative.parent.as_posix().lower() == runtime_pins()["folder"].lower()
        and source.name.lower() in runtime_pins()["files"]
    )


def stage(bundle: Path, redist: Path, receipt: Path) -> None:
    records: list[dict] = []
    pins = runtime_pins()
    # Prune unreferenced CRTs before recording imports, then inspect the final set.
    importers = crt_importers(bundle)
    for target in sorted(bundle.rglob("*")):
        if target.is_file() and is_crt(target.name):
            key = target.relative_to(bundle).parts[0] + "/" + target.name.lower()
            if key not in importers:
                target.unlink()
    for target in sorted(bundle.rglob("*")):
        if not target.is_file():
            continue
        if is_crt(target.name):
            source = redist / pins["folder"] / target.name.lower()
            if not source.is_file() or not valid_source(source, redist):
                raise ValueError(
                    f"Required pinned CRT not found in release VC/redist: {target.name}"
                )
            pin = pins["files"][target.name.lower()]
            if not microsoft_vendor(source) or sha256(source) != pin["sha256"]:
                raise ValueError(f"CRT source differs from Owner's pinned copy: {target.name}")
            if file_version(source) != pin["version"]:
                raise ValueError(f"CRT source version changed: {target.name}")
            collected_sha, collected_version = sha256(target), file_version(target)
            shutil.copyfile(source, target)
            if sha256(source) != sha256(target):
                raise ValueError("CRT copy changed bytes")
            records.append(
                {
                    "path": target.relative_to(bundle).as_posix(),
                    "source": str(source.resolve()),
                    "redist": str(redist.resolve()),
                    "sha256": sha256(target),
                    "version": file_version(source),
                    "collected_sha256": collected_sha,
                    "collected_version": collected_version,
                    "basis": "VS2022-Community-section-4/Visual-C++-Runtime-Files",
                }
            )
        elif microsoft_vendor(target):
            raise ValueError(f"Unapproved Microsoft PE in bundle: {target.relative_to(bundle)}")
    importers = crt_importers(bundle)
    names = {item["path"].split("/")[0] + "/" + Path(item["path"]).name.lower() for item in records}
    if importers.keys() != names:
        raise ValueError("Bundled CRT filenames do not exactly cover the PE imports")
    for item in records:
        key = item["path"].split("/")[0] + "/" + Path(item["path"]).name.lower()
        item["imported_by"] = importers[key]
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({"files": records}, indent=2), encoding="utf-8", newline="\n")
    print(f"Verified {len(records)} required app-local CRT copies against Owner's pinned VC/redist")
