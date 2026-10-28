"""Audit locked runtime Python distributions against the redistribution allowlist."""

import argparse
import fnmatch
import hashlib
import importlib.metadata
import json
import sys
import tomllib
from pathlib import Path

import pefile  # type: ignore[import-untyped]

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import mingw_runtime  # noqa: E402
from tools.stage_microsoft_runtime import crt_importers, runtime_pins, valid_source  # noqa: E402

MSVC_LICENSE = "LicenseRef-Microsoft-Visual-Cpp-Runtime"
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
INSTALLER_ONLY = {
    "inno-setup-installer": "InnoSetup",
    "pascal-script": "LicenseRef-RemObjects-PascalScript",
    "lzma-sdk": "LicenseRef-Public-Domain-Code",
    "lzma-loader": "LicenseRef-Public-Domain-Code",
    "hash-utilities": "LicenseRef-Public-Domain-Code",
    "jedi-uxtheme": "MPL-1.1",
    "delphi-rtl-vcl": "LicenseRef-Embarcadero-Compiled-Runtime",
}


def normalized(name: str) -> str:
    return name.lower().replace("_", "-").replace(".", "-")


def allowed_license(
    name: str, license_text: str | None, *, installer_wrapper: bool = False
) -> bool:
    if not license_text or license_text == "UNKNOWN":
        return False
    if normalized(name) == "pyinstaller-bootloader" and license_text == PYINSTALLER_BOOTLOADER:
        return True
    # ADR 0023 is scoped to the installer wrapper, never an app dependency.
    if installer_wrapper and INSTALLER_ONLY.get(name) == license_text:
        return True
    # A dual-license package may be used under one permitted alternative.
    options = license_text.split(" OR ")
    for option in options:
        if " AND " in option:
            if all(allowed_license(name, term) for term in option.split(" AND ")):
                return True
            continue
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


def check_trust_data(bundle: Path, inventory: dict) -> bool:
    """PM ISSUE-029: exact public certificate data only, never arbitrary code."""
    from dusty_fetch.tls import ROOTS, bundled_pem

    attributed = {
        item["path"]
        for item in inventory["files"]
        if "public-ca-certificates" in item["components"]
    }
    if attributed != {"resources/tls/" + name for name in ROOTS}:
        return False
    try:
        bundled_pem(bundle / "resources/tls")
        return True
    except (OSError, ValueError):
        return False


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
        if key == "dusty" and expression != "Apache-2.0":
            approved = False
        if key == "microsoft-visual-cpp-runtime" and expression == MSVC_LICENSE:
            approved = bool(inventory.get("microsoft_runtime"))
        if key == "ffmpeg" and expression == "LGPL-2.1-or-later":
            approved = entry.get("linkage") == "executable"
        if key == "jfk-fixture" and expression == "LicenseRef-Public-Domain":
            approved = entry.get("kind") == "data"
        if key == "public-ca-certificates" and expression == "LicenseRef-Public-CA-Certificate":
            approved = entry.get("kind") == "data" and check_trust_data(bundle, inventory)
        if key == mingw_runtime.COMPONENT or entry["name"] == mingw_runtime.COMPONENT:
            approved = key == mingw_runtime.COMPONENT and mingw_runtime.approved(bundle, inventory)
        if entry.get("linkage") == "static" and "LGPL" in expression:
            approved = False
        if not approved:
            findings.append(f"{key}: unapproved or unknown bundled license: {expression}")
    texts = json.loads(
        (Path(__file__).resolve().parents[1] / "packaging/licenses/sources.json").read_text(
            encoding="utf-8"
        )
    )
    required_texts = []
    if "libffi" in components:
        required_texts.append("libffi-MIT.txt")
    if "openssl" in components:
        required_texts.append("openssl-Apache-2.0.txt")
    if "ffmpeg" in components:
        required_texts.append("ffmpeg-LGPL-2.1.txt")
        required_texts.extend(("mingw-w64-runtime.txt", "winpthreads-COPYING.txt"))
        for component_name in ("mingw-w64-runtime", "winpthreads"):
            if component_name not in components:
                findings.append(f"Missing static FFmpeg runtime attribution: {component_name}")
        for name in ("mingw-w64-runtime.txt", "winpthreads-COPYING.txt"):
            path = bundle / "bin/ffmpeg" / name
            if (
                not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != texts[name]["sha256"]
            ):
                findings.append(f"Missing or changed FFmpeg runtime notice: {name}")
    if "pyside6-essentials" in components:
        required_texts.extend(("qt-LGPL-3.0.txt", "qt-GPL-3.0-reference.txt"))
    for name in required_texts:
        path = bundle / "licenses" / name
        if (
            not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != texts[name]["sha256"]
        ):
            findings.append(f"Missing or changed required license text: {name}")
    findings.extend(check_microsoft(bundle, inventory, actual))
    return findings


def check_microsoft(bundle: Path, inventory: dict, actual: dict[str, Path]) -> list[str]:
    """ADR 0020: file-scoped exception, live release provenance and protective terms."""
    findings = []
    receipts = {item["path"]: item for item in inventory.get("microsoft_runtime", [])}
    expected = set()
    pins = runtime_pins()
    importers = crt_importers(bundle)
    for relative, path in actual.items():
        is_crt = any(
            fnmatch.fnmatchcase(path.name.lower(), pattern)
            for pattern in ("vcruntime140*.dll", "msvcp140*.dll")
        )
        with path.open("rb") as stream:
            mz = stream.read(2) == b"MZ"
        microsoft = False
        if mz:
            with pefile.PE(str(path)) as executable:
                for group in getattr(executable, "FileInfo", []):
                    for info in group:
                        for table in getattr(info, "StringTable", []):
                            company = table.entries.get(b"CompanyName", b"").lower()
                            microsoft |= b"microsoft" in company
        if microsoft and not is_crt:
            findings.append(f"Unapproved Microsoft PE: {relative}")
        if not is_crt:
            continue
        if not microsoft:
            findings.append(f"CRT filename is not a Microsoft PE: {relative}")
        expected.add(relative)
        record = receipts.get(relative)
        if not record:
            findings.append(f"Missing VC/redist provenance: {relative}")
            continue
        source, redist = Path(record["source"]).resolve(), Path(record["redist"]).resolve()
        valid = (
            valid_source(source, redist)
            and source.name.lower() == path.name.lower()
            and record["basis"] == "VS2022-Community-section-4/Visual-C++-Runtime-Files"
        )
        key = Path(relative).parts[0] + "/" + path.name.lower()
        if not importers.get(key) or record.get("imported_by") != importers.get(key):
            findings.append(f"CRT lacks verified importing PEs: {relative}")
        pin = pins["files"].get(path.name.lower(), {})
        if record.get("sha256") != pin.get("sha256") or record.get("version") != pin.get("version"):
            findings.append(f"CRT differs from the maintainer's pinned hash/version: {relative}")
        with source.open("rb") as stream:
            source_sha = hashlib.file_digest(stream, "sha256").hexdigest()
        with path.open("rb") as stream:
            actual_sha = hashlib.file_digest(stream, "sha256").hexdigest()
        if not valid or source_sha != actual_sha or actual_sha != record["sha256"]:
            findings.append(f"CRT is not an identical permitted release copy: {relative}")
    if receipts.keys() != expected:
        findings.append("CRT provenance does not exactly cover the bundled CRT files")
    if not expected and not receipts:
        return findings
    evidence_root = Path(__file__).resolve().parents[1] / "packaging/licenses/microsoft"
    documents = json.loads((evidence_root / "sources.json").read_text(encoding="utf-8"))
    for name, record in documents.items():
        pdf = bundle / "licenses/microsoft" / name
        text = pdf.with_suffix(".txt")
        for path, expected_sha in ((pdf, record["sha256"]), (text, record["text_sha256"])):
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
                findings.append(f"Missing or changed Microsoft license evidence: {path.name}")
    eula = bundle / "licenses/microsoft/runtime-eula.txt"
    notices = bundle / "THIRD_PARTY_NOTICES.md"
    if (
        not eula.is_file()
        or not notices.is_file()
        or eula.read_text(encoding="utf-8").strip() not in notices.read_text(encoding="utf-8")
    ):
        findings.append("Full runtime protective terms are missing from THIRD_PARTY_NOTICES")
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
