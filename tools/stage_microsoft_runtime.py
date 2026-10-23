"""Copy only the ADR 0020 CRT names from an installed VS 2022 release redist."""

import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pefile  # type: ignore[import-untyped]


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
    parts = [part.lower() for part in relative.parts]
    return (
        redist.name.lower() == "redist"
        and redist.parent.name.lower() == "vc"
        and "x64" in parts
        and "microsoft.vc143.crt" in parts
        and "debug_nonredist" not in parts
        and "onecore" not in parts
        and is_crt(source.name)
    )


def stage(bundle: Path, redist: Path, receipt: Path) -> None:
    records = []
    for target in sorted(bundle.rglob("*")):
        if not target.is_file():
            continue
        if is_crt(target.name):
            candidates = [path for path in redist.rglob(target.name) if valid_source(path, redist)]
            if not candidates:
                # Windows filenames are case insensitive; glob matching can vary by host.
                candidates = [
                    path
                    for path in redist.rglob("*.dll")
                    if path.name.lower() == target.name.lower() and valid_source(path, redist)
                ]
            if not candidates:
                raise ValueError(f"Required CRT not found in release VC/redist: {target.name}")
            source = max(
                candidates,
                key=lambda path: tuple(
                    int(part) for part in path.relative_to(redist).parts[1].split(".")
                ),
            )
            if not microsoft_vendor(source):
                raise ValueError("Release CRT source is not a Microsoft PE")
            shutil.copyfile(source, target)
            if sha256(source) != sha256(target):
                raise ValueError("CRT copy changed bytes")
            records.append(
                {
                    "path": target.relative_to(bundle).as_posix(),
                    "source": str(source.resolve()),
                    "redist": str(redist.resolve()),
                    "sha256": sha256(target),
                    "basis": "VS2022-Community-section-4/Visual-C++-Runtime-Files",
                }
            )
        elif microsoft_vendor(target):
            raise ValueError(f"Unapproved Microsoft PE in bundle: {target.relative_to(bundle)}")
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps({"files": records}, indent=2), encoding="utf-8", newline="\n")
    print(f"Verified {len(records)} app-local CRT copies against VS 2022 VC/redist")
