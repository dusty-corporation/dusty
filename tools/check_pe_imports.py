"""Inspect every PE by signature and enforce ADR 0021's exact platform pins."""

import argparse
import hashlib
import json
from pathlib import Path

import pefile  # type: ignore[import-untyped]

BLOCKED = {"ws2_32.dll", "wsock32.dll", "wininet.dll", "winhttp.dll", "dnsapi.dll"}
PINS = Path(__file__).resolve().parents[1] / "packaging/platform-socket-imports.json"


def imports(path: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    with pefile.PE(str(path)) as executable:
        for directory in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT"):
            for library in getattr(executable, directory, []):
                name = library.dll.decode("ascii").lower()
                functions = result.setdefault(name, [])
                functions.extend(
                    entry.name.decode("ascii") if entry.name else f"ordinal:{entry.ordinal}"
                    for entry in library.imports
                )
    return {name: sorted(set(functions)) for name, functions in result.items()}


def check(folder: Path, pins: dict) -> tuple[list[str], list[dict]]:
    findings, checked = [], []
    seen = set()
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        with path.open("rb") as stream:
            if stream.read(2) != b"MZ":
                continue
            stream.seek(0)
            sha = hashlib.file_digest(stream, "sha256").hexdigest()
        relative = path.relative_to(folder).as_posix()
        libraries = imports(path)
        checked.append({"path": relative, "sha256": sha, "imports": libraries})
        print(f"PE checked: {relative}")
        name = path.name.lower()
        pin = pins.get(name)
        prohibited = BLOCKED.intersection(libraries)
        if pin:
            seen.add(name)
            if sha != pin["sha256"] or libraries.get("ws2_32.dll") != sorted(pin["ws2_32"]):
                findings.append(f"Platform PE hash or Winsock function set changed: {relative}")
            if prohibited - {"ws2_32.dll"}:
                findings.append(f"Platform PE imports additional prohibited library: {relative}")
        elif prohibited:
            findings.append(
                f"Prohibited native network import: {relative}: {','.join(sorted(prohibited))}"
            )
    if seen != pins.keys():
        findings.append("Required pinned platform PE is missing")
    return findings, checked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--native", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("build/packaging/audit/offline-pe.json")
    )
    args = parser.parse_args()
    findings, checked = check(args.folder, json.loads(PINS.read_text(encoding="utf-8")))
    if args.native:
        native_findings, native_checked = check(args.native, {})
        findings.extend(native_findings)
        for item in native_checked:
            item["path"] = "bin/" + item["path"]
        checked.extend(native_checked)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"checked": checked, "findings": findings}, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    if findings:
        print("\n".join(findings))
        return 1
    print(f"PE gate passed: {len(checked)} checked, exact ADR 0021 platform pins")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
