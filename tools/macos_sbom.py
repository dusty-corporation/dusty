"""Write a CycloneDX 1.6 software bill of materials for a built Dusty.app.

    python -m tools.macos_sbom build/mac-app/Dusty.app build/mac-app/audit/notices-inventory.json \\
        build/mac-release/sbom.cdx.json

The components and the component of every file come from the notices inventory
that tools/build_macos_app.py writes while it generates THIRD_PARTY_NOTICES.md,
so the SBOM and the notices cannot disagree. Every file is hashed from the
finished, signed app. A file in the app that the inventory does not list, or a
listed file that is missing, stops the tool, as does an inventory with open
license items. The result is checked against the CycloneDX 1.6 JSON schema.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from pathlib import Path

from cyclonedx.schema import SchemaVersion
from cyclonedx.validation.json import JsonStrictValidator
from license_expression import get_spdx_licensing  # type: ignore[import-untyped]


class SbomError(RuntimeError):
    """The app and its notices inventory do not describe the same files."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def app_files(app: Path) -> dict[str, Path]:
    """Every regular file in the app, by its path inside the bundle; links are skipped."""
    return {
        path.relative_to(app).as_posix(): path
        for path in sorted(app.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


NOTICES = "Contents/Resources/THIRD_PARTY_NOTICES.md"
SIGNATURE = "_CodeSignature/CodeResources"


def added_after_inventory(relative: str, listed: dict[str, list[str]]) -> list[str] | None:
    """Owners of the two kinds of file made after the inventory, else None.

    The notices file is written from the inventory, and codesign adds a
    CodeResources seal to the app and to each framework it signs. A seal
    belongs to the component of the code it seals.
    """
    if relative == NOTICES:
        return ["dusty"]
    if not relative.endswith("/" + SIGNATURE) and relative != "Contents/" + SIGNATURE:
        return None
    sealed = relative[: -len(SIGNATURE)]
    if sealed == "Contents/":
        return ["dusty"]
    owners = {owner for path, keys in listed.items() if path.startswith(sealed) for owner in keys}
    return sorted(owners) or None


def license_entry(text: str) -> dict:
    """An SPDX expression when the text is one, otherwise the text as a license name."""
    try:
        info = get_spdx_licensing().validate(text)
    except Exception:  # the library raises for some malformed keys instead of reporting
        return {"license": {"name": text}}
    # SPDX allows LicenseRef- identifiers, which the SPDX key list cannot know.
    unknown = [s for s in info.invalid_symbols if not s.startswith("LicenseRef-")]
    other = [e for e in info.errors if not e.startswith("Unknown license key(s): LicenseRef-")]
    valid = not unknown and not other
    return {"expression": text} if valid else {"license": {"name": text}}


def build(app: Path, inventory: dict) -> dict:
    if inventory.get("open_items"):
        raise SbomError("The notices inventory has open license items")
    components = inventory["components"]
    listed = dict(inventory["files"])
    present = app_files(app)
    for relative in set(present) - set(listed):
        owners = added_after_inventory(relative, inventory["files"])
        if owners is not None:
            listed[relative] = owners
    if set(listed) != set(present):
        extra = sorted(set(present) - set(listed))[:5]
        missing = sorted(set(listed) - set(present))[:5]
        raise SbomError(f"App and inventory differ: unlisted {extra}, missing {missing}")
    sbom: dict = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "serialNumber": "urn:uuid:" + str(uuid.uuid4()),
        "components": [],
        "dependencies": [],
    }
    for key, item in sorted(components.items()):
        sbom["components"].append(
            {
                "type": "library",
                "bom-ref": key,
                "name": item["name"],
                "version": item["version"],
                "licenses": [license_entry(item["license"])],
                "copyright": item["copyright"],
            }
        )
    for relative, owners in sorted(listed.items()):
        unknown = set(owners) - set(components)
        if not owners or unknown:
            raise SbomError(f"{relative} has no known component")
        ref = "file:" + relative
        sbom["components"].append(
            {
                "type": "file",
                "bom-ref": ref,
                "name": relative,
                "hashes": [{"alg": "SHA-256", "content": sha256(present[relative])}],
            }
        )
        sbom["dependencies"].append({"ref": ref, "dependsOn": sorted(owners)})
    error = JsonStrictValidator(SchemaVersion.V1_6).validate_str(json.dumps(sbom))
    if error:
        raise SbomError(f"CycloneDX 1.6 validation failed: {error}")
    return sbom


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("app", type=Path, help="The finished Dusty.app")
    parser.add_argument("inventory", type=Path, help="audit/notices-inventory.json of that build")
    parser.add_argument("output", type=Path, help="New SBOM file to write")
    args = parser.parse_args(argv)
    if args.output.exists():
        print(f"error: {args.output} already exists", file=sys.stderr)
        return 1
    try:
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        sbom = build(args.app, inventory)
    except (SbomError, OSError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(sbom, indent=2) + "\n", encoding="utf-8")
    files = sum(item["type"] == "file" for item in sbom["components"])
    print(f"Wrote {args.output}: {len(sbom['components']) - files} components, {files} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
