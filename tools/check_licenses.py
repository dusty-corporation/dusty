"""Audit locked runtime Python distributions against the redistribution allowlist."""

import argparse
import hashlib
import importlib.metadata
import json
import sys
import tomllib
from pathlib import Path

ALLOWED = {
    "MIT",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "Apache-2.0",
    "ISC",
    "Zlib",
    "PSF-2.0",
    "LGPL-2.1-or-later",
    "LGPL-3.0-only",
    "LGPL-3.0-or-later",
}
ALIASES = {
    "MIT License": "MIT",
    "Apache Software License": "Apache-2.0",
    "ISC License (ISCL)": "ISC",
    "GNU Lesser General Public License v2 or later (LGPLv2+)": "LGPL-2.1-or-later",
}
LGPL_DYNAMIC = {"pyside6", "pyside6-addons", "pyside6-essentials", "shiboken6"}
PYINSTALLER_BOOTLOADER = "GPL-2.0-or-later WITH PyInstaller-bootloader-exception"


def normalized(name: str) -> str:
    return name.lower().replace("_", "-").replace(".", "-")


def allowed_license(name: str, license_text: str | None) -> bool:
    if not license_text or license_text == "UNKNOWN":
        return False
    if normalized(name) == "pyinstaller-bootloader" and license_text == PYINSTALLER_BOOTLOADER:
        return True
    # A dual-license package may be used under one permitted alternative.
    options = license_text.split(" OR ")
    for option in options:
        identifier = ALIASES.get(option.strip(), option.strip())
        if identifier in ALLOWED:
            if identifier.startswith("LGPL") and normalized(name) not in LGPL_DYNAMIC:
                continue
            return True
    return False


def runtime_packages(lock: dict[str, object]) -> dict[str, str]:
    packages = lock.get("package", [])
    if not isinstance(packages, list):
        raise ValueError("invalid lockfile package list")
    by_name = {normalized(item["name"]): item for item in packages}
    if "dusty" not in by_name:
        raise ValueError("dusty missing from lockfile")
    result: dict[str, str] = {}
    pending = ["dusty"]
    while pending:
        name = pending.pop()
        if name in result:
            continue
        item = by_name.get(name)
        if item is None:
            raise ValueError(f"locked runtime dependency missing: {name}")
        result[name] = item["version"]
        pending.extend(normalized(dep["name"]) for dep in item.get("dependencies", []))
    return result


def check(root: Path) -> list[str]:
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    findings: list[str] = []
    for name, version in sorted(runtime_packages(lock).items()):
        if name == "dusty":
            continue
        try:
            dist = importlib.metadata.distribution(name)
        except importlib.metadata.PackageNotFoundError:
            findings.append(f"{name}: installed distribution missing")
            continue
        if dist.version != version:
            findings.append(f"{name}: installed version differs from lockfile")
        license_text = dist.metadata.get("License-Expression") or dist.metadata.get("License")
        if not allowed_license(name, license_text):
            findings.append(f"{name}: unapproved or unknown license: {license_text}")
    return findings


def check_bundle(bundle: Path, inventory_path: Path) -> list[str]:
    """Audit every collected file and embedded component; unknowns fail closed."""
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    findings = []
    components = inventory["components"]
    recorded = {item["path"]: item for item in inventory["files"]}
    actual = {
        path.relative_to(bundle).as_posix(): path for path in bundle.rglob("*") if path.is_file()
    }
    if actual.keys() != recorded.keys():
        findings.append("Bundle files differ from the audited inventory")
    for name, path in actual.items():
        entry = recorded.get(name)
        if entry is None:
            continue
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != entry["sha256"]:
            findings.append(f"Bundle inventory hash mismatch: {name}")
        if not entry["components"] or any(key not in components for key in entry["components"]):
            findings.append(f"Bundle file has no valid component attribution: {name}")
    for key, entry in sorted(components.items()):
        expression = entry["license"]
        # SPEC explicitly permits FFmpeg as a separate executable and fixture data.
        approved = allowed_license(entry["name"], expression)
        if key == "ffmpeg" and expression == "LGPL-2.1-or-later":
            approved = entry.get("linkage") == "executable"
        if key == "jfk-fixture" and expression == "LicenseRef-Public-Domain":
            approved = entry.get("kind") == "data"
        if entry.get("linkage") == "static" and "LGPL" in expression:
            approved = False
        if not approved:
            findings.append(f"{key}: unapproved or unknown bundled license: {expression}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--inventory", type=Path)
    args = parser.parse_args()
    if bool(args.bundle) != bool(args.inventory):
        parser.error("--bundle and --inventory are required together")
    try:
        findings = check_bundle(args.bundle, args.inventory) if args.bundle else check(args.root)
    except (OSError, ValueError, KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        findings = [str(exc)]
    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("Bundle license check passed" if args.bundle else "Runtime license check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
