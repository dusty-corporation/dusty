"""Stage only the approved, already-gated M5 release assets and their checksums."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from tools.release_version import versions


def verify_checksum(file: Path, sums: Path) -> None:
    """Check a previously gated installer before the upgrade test executes it."""
    matches = []
    for line in sums.read_text(encoding="utf-8").splitlines():
        fields = line.split("  ", 1)
        if len(fields) == 2 and fields[1] == file.name:
            matches.append(fields[0])
    if len(matches) != 1 or matches[0] != hashlib.sha256(file.read_bytes()).hexdigest():
        raise ValueError("Previous installer checksum missing, duplicated or mismatched")


def stage(source: Path, output: Path, tag: str) -> None:
    _, display, _ = versions(tag)
    if output.exists():
        raise ValueError("Release staging destination must be new")
    if int(tag.rsplit(".", 1)[1]) >= 3:
        summaries = list(source.rglob("acceptance/summary.json"))
        audits = list(source.rglob("acceptance/download-wfp.json"))
        if len(summaries) != 1 or len(audits) != 1:
            raise ValueError("Release lacks installed upgrade/download acceptance receipts")
        receipt = json.loads(summaries[0].read_text(encoding="utf-8-sig"))
        audit = json.loads(audits[0].read_text(encoding="utf-8-sig"))
        if (
            receipt.get("two_distinct_versions") is not True
            or receipt.get("current_installer_fresh_download_wfp") != "passed"
            or receipt.get("installed_wfp") != "passed"
            or receipt.get("upgrade_models_preserved_with_downloader_blocked") != "passed"
            or receipt.get("uninstall_keep_models") != "passed"
            or receipt.get("uninstall_remove_models") != "passed"
            or receipt.get("normal_cancel_removes_partial") != "passed"
            or receipt.get("preserved_legacy_destination") != "passed"
            or receipt.get("protected_install_destination") != "passed"
            or receipt.get("user_outputs_unchanged") is not True
            or audit.get("calibration_blocked_event") is not True
            or any(audit.get(key) != 0 for key in ("installer", "gui", "native", "fetch_blocked"))
            or audit.get("fetch_allowed", 0) < 1
        ):
            raise ValueError(
                "Release requires a true upgrade and current-installer zero-event audit"
            )
    selected = {}
    for pattern, name in (
        ("*.exe", f"Dusty-{display}-draft-unsigned.exe"),
        ("THIRD_PARTY_NOTICES.md", "THIRD_PARTY_NOTICES.md"),
        ("sbom.cdx.json", f"dusty-{display}-sbom.json"),
        ("installer-jedi-source.zip", "installer-jedi-source.zip"),
    ):
        found = list(source.rglob(pattern))
        if pattern == "sbom.cdx.json":
            found = [p for p in found if p.parent.name == "installer"]
        if len(found) != 1 or found[0].is_symlink():
            raise ValueError(f"Expected exactly one installer asset: {pattern}")
        selected[name] = found[0]
    # Parse before creating any output, so malformed SBOMs cannot be uploaded.
    sbom = next(p for n, p in selected.items() if n.endswith("-sbom.json"))
    if json.loads(sbom.read_text(encoding="utf-8"))["bomFormat"] != "CycloneDX":
        raise ValueError("Expected CycloneDX SBOM")
    output.mkdir(parents=True)
    hashes = []
    for name, path in sorted(selected.items()):
        destination = output / name
        shutil.copyfile(path, destination)
        hashes.append(f"{hashlib.sha256(destination.read_bytes()).hexdigest()}  {name}")
    (output / "SHA256SUMS.txt").write_text("\n".join(hashes) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    stage(args.source, args.output, args.tag)
