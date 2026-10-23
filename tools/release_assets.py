"""Stage only the approved, already-gated M5 release assets and their checksums."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from tools.release_version import versions


def stage(source: Path, output: Path, tag: str) -> None:
    _, display, _ = versions(tag)
    if output.exists():
        raise ValueError("Release staging destination must be new")
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
