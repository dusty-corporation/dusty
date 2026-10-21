"""Audit locked runtime Python distributions against the redistribution allowlist."""

import importlib.metadata
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


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    try:
        findings = check(root)
    except (OSError, ValueError, tomllib.TOMLDecodeError) as exc:
        findings = [str(exc)]
    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("Runtime license check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
