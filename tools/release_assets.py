"""Stage only the approved, already-gated release assets and their checksums.

From 1.1.0 a public release is combined (ADR 0029): the Windows installer
assets and the Mac disk image assets, from one source snapshot, under one
SHA256SUMS.txt. A missing or failed Mac input stops the draft.
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from tools.ffmpeg_source import PIN as FFMPEG_SOURCE
from tools.ffmpeg_source import verify as verify_ffmpeg_source
from tools.release_policy import needs_receipts
from tools.release_version import public_version, versions

ROOT = Path(__file__).resolve().parents[1]
FIRST_COMBINED = (1, 1, 0)
# The first published Mac release. Every later release must prove its Mac
# upgrade from the previous published release, not from its own build.
FIRST_MAC_RELEASE = (1, 1, 3)
MAC_BUNDLE_ID = "org.dusty.Dusty"
MAC_SCENARIOS = ("1 first run", "2 upgrade", "3 remove and reinstall", "4 moved app")


def needs_mac(tag: str) -> bool:
    """Public releases from 1.1.0 ship Windows and Mac together."""
    version = public_version(tag)
    return version is not None and version >= FIRST_COMBINED


def _one(source: Path, pattern: str) -> Path:
    found = [path for path in source.rglob(pattern) if not path.is_symlink()]
    if len(found) != 1:
        raise ValueError(f"Expected exactly one Mac release input: {pattern}")
    return found[0]


def _row(rows: list[dict], scenario: str, step: str) -> dict:
    found = [row for row in rows if row.get("scenario") == scenario and row.get("step") == step]
    return found[0] if len(found) == 1 else {}


def mac_assets(source: Path, display: str, previous_tag: str = "") -> dict[str, Path]:
    """Check the macos CI job's receipts and return the Mac assets by release name.

    After the first Mac release, the upgrade scenario must have installed the
    previous published release (previous_tag) and replaced it with this one.
    """
    image_name = f"Dusty-{display}-macos-arm64.dmg"
    images = [path for path in source.rglob("*.dmg") if not path.is_symlink()]
    if len(images) != 1 or images[0].name != image_name:
        raise ValueError(f"Expected exactly one Mac disk image named {image_name}")
    image = images[0]
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    if _one(source, image_name + ".sha256").read_text(encoding="utf-8").split() != [
        digest,
        image_name,
    ]:
        raise ValueError("Mac disk image checksum file does not match the image")
    manifest = json.loads(_one(source, "dmg-manifest.json").read_text(encoding="utf-8"))
    if (
        manifest.get("image") != image_name
        or manifest.get("version") != display
        or manifest.get("bundle_id") != MAC_BUNDLE_ID
        or manifest.get("sha256") != digest
        or manifest.get("items") != ["Applications", "Dusty.app"]
    ):
        raise ValueError("Mac disk image manifest does not match this release")
    bundle = json.loads(_one(source, "bundle-check.json").read_text(encoding="utf-8"))
    if bundle.get("findings") != [] or not bundle.get("summary", {}).get("macho_files"):
        raise ValueError("Mac bundle check did not pass")
    rows = json.loads(_one(source, "results.json").read_text(encoding="utf-8"))
    checked = [row for row in rows if row.get("result") != "info"]
    if (
        not checked
        or any(row.get("result") != "pass" for row in checked)
        or {row.get("scenario") for row in checked} != set(MAC_SCENARIOS)
    ):
        raise ValueError("Mac self-test, upgrade, removal and moved app scenarios did not pass")
    current = public_version("v" + display)
    if current is not None and current > FIRST_MAC_RELEASE:
        if public_version(previous_tag) is None:
            raise ValueError("A Mac upgrade needs the previous public release tag")
        _, previous, _ = versions(previous_tag)
        old = _row(rows, "2 upgrade", "old app --version")
        new = _row(rows, "2 upgrade", "new app --version")
        if (
            old.get("result") != "pass"
            or old.get("observed") != f"exit 0, Dusty {previous}"
            or new.get("result") != "pass"
            or new.get("observed") != f"exit 0, Dusty {display}"
        ):
            raise ValueError(f"Mac upgrade did not start from the published Dusty {previous}")
    sbom = _one(source, "sbom.cdx.json")
    if json.loads(sbom.read_text(encoding="utf-8")).get("bomFormat") != "CycloneDX":
        raise ValueError("Expected a CycloneDX Mac SBOM")
    script = _one(source, "build_ffmpeg-macos.sh")
    if script.read_bytes() != (ROOT / "native/macos/build_ffmpeg.sh").read_bytes():
        raise ValueError("Mac FFmpeg build script differs from the released source")
    return {
        image_name: image,
        "THIRD_PARTY_NOTICES-macos.md": _one(source, "THIRD_PARTY_NOTICES.md"),
        f"dusty-{display}-macos-arm64-sbom.json": sbom,
        "build_ffmpeg-macos.sh": script,
    }


def verify_checksum(file: Path, sums: Path) -> None:
    """Check a previously gated installer before the upgrade test executes it."""
    matches = []
    for line in sums.read_text(encoding="utf-8").splitlines():
        fields = line.split("  ", 1)
        if len(fields) == 2 and fields[1] == file.name:
            matches.append(fields[0])
    if len(matches) != 1 or matches[0] != hashlib.sha256(file.read_bytes()).hexdigest():
        raise ValueError("Previous installer checksum missing, duplicated or mismatched")


def stage(
    source: Path,
    output: Path,
    tag: str,
    previous_tag: str = "",
    mac_source: Path | None = None,
) -> None:
    _, display, _ = versions(tag)
    if output.exists():
        raise ValueError("Release staging destination must be new")
    if needs_mac(tag) and mac_source is None:
        raise ValueError("A combined release needs the Mac disk image inputs")
    if mac_source is not None and not needs_mac(tag):
        raise ValueError("Only public releases from 1.1.0 include the Mac disk image")
    if needs_receipts(tag):
        summaries = list(source.rglob("acceptance/summary.json"))
        audits = list(source.rglob("acceptance/download-wfp.json"))
        if len(summaries) != 1 or len(audits) != 1:
            raise ValueError("Release lacks installed upgrade/download acceptance receipts")
        receipt = json.loads(summaries[0].read_text(encoding="utf-8-sig"))
        audit = json.loads(audits[0].read_text(encoding="utf-8-sig"))
        initial = tag == "v1.0.0"
        # The release workflow's validate job names the newest published release.
        expected_previous = previous_tag if public_version(tag) and not initial else None
        if expected_previous is not None and public_version(expected_previous) is None:
            raise ValueError("A public release needs the previous public release tag")
        version_evidence = (
            receipt.get("two_distinct_versions") is False
            and receipt.get("previous_tag") == ""
            and receipt.get("silent_per_user_install") == "passed"
            and receipt.get("same_version_reinstall_models_preserved") == "passed"
            if initial
            else receipt.get("two_distinct_versions") is True
        )
        if (
            not version_evidence
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
            or (expected_previous is not None and receipt.get("previous_tag") != expected_previous)
        ):
            raise ValueError(
                "Release requires reinstall or true upgrade and current-installer zero-event audit"
            )
    selected = {}
    for pattern, name in (
        (
            "*.exe",
            f"Dusty-{display}-Setup.exe"
            if public_version(tag)
            else f"Dusty-{display}-draft-unsigned.exe",
        ),
        ("THIRD_PARTY_NOTICES.md", "THIRD_PARTY_NOTICES.md"),
        ("sbom.cdx.json", f"dusty-{display}-sbom.json"),
        ("installer-jedi-source.zip", "installer-jedi-source.zip"),
        (FFMPEG_SOURCE["name"], FFMPEG_SOURCE["name"]),
        ("build_ffmpeg.sh", "build_ffmpeg.sh"),
    ):
        found = list(source.rglob(pattern))
        if pattern == "sbom.cdx.json":
            found = [p for p in found if p.parent.name == "installer"]
        if len(found) != 1 or found[0].is_symlink():
            raise ValueError(f"Expected exactly one installer asset: {pattern}")
        selected[name] = found[0]
    verify_ffmpeg_source(selected[FFMPEG_SOURCE["name"]].parent)
    if mac_source is not None:
        mac = mac_assets(mac_source, display, previous_tag)
        if set(mac) & set(selected):
            raise ValueError("Mac and Windows release assets would overwrite each other")
        selected.update(mac)
    # Parse before creating any output, so malformed SBOMs cannot be uploaded.
    for name, sbom in selected.items():
        if name.endswith("-sbom.json"):
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
    parser.add_argument("--previous-tag", default="")
    parser.add_argument("--mac-source", type=Path, help="The macos CI job's release artifact")
    args = parser.parse_args()
    stage(args.source, args.output, args.tag, args.previous_tag, args.mac_source)
