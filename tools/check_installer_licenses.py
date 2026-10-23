"""Fail closed on the installer wrapper's additional redistribution license."""

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.check_licenses import allowed_license, check_bundle  # noqa: E402
from tools.installer_notices import runtime_notices  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def check() -> list[str]:
    pins = json.loads((ROOT / "packaging/licenses/inno/source.json").read_text(encoding="utf-8"))
    license_file = ROOT / "packaging/licenses/inno/license.txt"
    findings = []
    if hashlib.sha256(license_file.read_bytes()).hexdigest() != pins["repository_sha256"]:
        findings.append("Inno Setup license text differs from its pinned provenance")
    if not allowed_license("inno-setup-installer", "InnoSetup", installer_wrapper=True):
        findings.append("Inno Setup installer wrapper license is not approved")
    return findings


def check_inventory(path: Path) -> list[str]:
    inventory = json.loads(path.read_text(encoding="utf-8"))
    findings = []
    expected = json.loads((ROOT / "packaging/licenses/inno/components.json").read_text())
    actual = inventory["wrapper_components"]
    if (
        actual[1:] != expected
        or actual[0]["name"] != "inno-setup-installer"
        or actual[0]["license"] != "InnoSetup"
    ):
        findings.append("Installer static inventory differs from the pinned source review")
    for item in actual:
        notice = ROOT / "packaging/licenses/inno" / item["notice"]
        if hashlib.sha256(notice.read_bytes()).hexdigest() != item["notice_sha256"]:
            findings.append(f"Installer notice hash changed: {item['name']}")
        for extra in item.get("additional_notices", []):
            file = ROOT / "packaging/licenses/inno" / extra["file"]
            if hashlib.sha256(file.read_bytes()).hexdigest() != extra["sha256"]:
                findings.append(f"Installer additional notice changed: {item['name']}")
        if not allowed_license(item["name"], item["license"], installer_wrapper=True):
            findings.append(f"Installer component {item['name']}: unapproved {item['license']}")
    return findings


def check_retained_sources(directory: Path) -> list[str]:
    proof_path = ROOT / "packaging/licenses/inno/runtime-source.json"
    proof = json.loads(proof_path.read_text(encoding="utf-8"))
    pins = json.loads((ROOT / "packaging/licenses/inno/source.json").read_text(encoding="utf-8"))
    receipt = json.loads((directory / "runtime-inputs.json").read_text(encoding="utf-8"))
    findings = []
    if (
        receipt["source_commit"] != proof["commit"]
        or receipt["compiler_bootstrap_sha256"] != pins["compiler_sha256"]
        or receipt["source_review_sha256"] != hashlib.sha256(proof_path.read_bytes()).hexdigest()
        or sorted(item["name"] for item in receipt["files"]) != sorted(proof["runtime_files"])
    ):
        findings.append("Installer runtime selection differs from source review")
    with zipfile.ZipFile(directory / "installer-jedi-source.zip") as archive:
        expected = {Path(item["path"]).name: item["sha256"] for item in proof["jedi_sources"]}
        for name, sha in expected.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != sha:
                findings.append("Retained JEDI source differs from upstream")
        notice = (ROOT / "packaging/licenses/inno/jedi-uxtheme.txt").read_bytes()
        if archive.read("LICENSE-and-notices.txt") != notice:
            findings.append("Retained JEDI source license changed")
    if (directory / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8") != runtime_notices(
        ROOT / "dist/Dusty"
    ):
        findings.append("Installer component notices are incomplete or changed")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "build/installer/license-findings.txt"
    )
    args = parser.parse_args()
    findings = check()
    inventory = ROOT / "build/installer/inventory.json"
    if not inventory.exists():
        findings.append("Installer-wide inventory missing")
    else:
        findings.extend(check_inventory(inventory))
        findings.extend(check_retained_sources(inventory.parent))
        record = json.loads(inventory.read_text(encoding="utf-8"))["installer"]
        image = inventory.parent / "output" / record["name"]
        with image.open("rb") as stream:
            sha = hashlib.file_digest(stream, "sha256").hexdigest()
        if sha != record["sha256"] or image.stat().st_size != record["bytes"]:
            findings.append("Compiled installer differs from its inventory")
        findings.extend(
            check_bundle(ROOT / "dist/Dusty", ROOT / "build/packaging/audit/inventory.json")
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(findings) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(findings) if findings else "Installer license check passed")
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
