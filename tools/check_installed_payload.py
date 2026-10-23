"""Inventory installed files and reject changes beyond Inno's own runtime files."""

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def check(installed: Path, bundle: Path) -> tuple[list[str], list[dict[str, str]]]:
    expected = {
        file.relative_to(bundle).as_posix(): digest(file)
        for file in bundle.rglob("*")
        if file.is_file()
    }
    expected["licenses/inno-setup.txt"] = digest(ROOT / "packaging/licenses/inno/license.txt")
    findings = []
    checked = []
    seen = set()
    wrappers = []
    for file in installed.rglob("*"):
        if not file.is_file():
            continue
        relative = file.relative_to(installed).as_posix()
        sha = digest(file)
        checked.append({"path": relative, "sha256": sha})
        seen.add(relative)
        if relative in expected:
            if sha != expected[relative]:
                findings.append(f"Installed payload changed: {relative}")
        elif re.fullmatch(r"unins[0-9]{3}\.(exe|dat|msg)", relative):
            wrappers.append(relative)
        else:
            findings.append(f"Uninventoried installed file: {relative}")
    if expected.keys() - seen:
        findings.append("Installed payload is missing inventoried files")
    if len([name for name in wrappers if name.endswith(".exe")]) != 1:
        findings.append("Expected exactly one installed Inno uninstaller executable")
    return findings, checked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("installed", type=Path)
    parser.add_argument("--bundle", type=Path, default=ROOT / "dist/Dusty")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    findings, checked = check(args.installed, args.bundle)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"files": checked, "findings": findings}, indent=2))
    print("\n".join(findings) if findings else f"Installed file inventory passed: {len(checked)}")
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
