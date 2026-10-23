"""Extend the actual app inventory with the pinned compiled installer runtime.

Source-identified static subcomponents stay separate; unknown or unapproved
licenses are findings, never silently covered by the wrapper exception.
"""

import argparse
import hashlib
import json
from pathlib import Path

from cyclonedx.schema import SchemaVersion
from cyclonedx.validation.json import JsonStrictValidator

ROOT = Path(__file__).resolve().parents[1]


def generate(bundle: Path, app_audit: Path, output: Path) -> None:
    pins = json.loads((ROOT / "packaging/licenses/inno/source.json").read_text())
    components = json.loads((ROOT / "packaging/licenses/inno/components.json").read_text())
    wrapper = {
        "name": "inno-setup-installer",
        "version": pins["version"],
        "license": "InnoSetup",
        "source": pins["url"],
        "notice": "license.txt",
        "notice_sha256": pins["repository_sha256"],
    }
    components.insert(0, wrapper)
    inventory = json.loads((app_audit / "inventory.json").read_text(encoding="utf-8"))
    installers = list((output / "output").glob("*.exe"))
    if len(installers) != 1:
        raise ValueError("Expected exactly one compiled installer")
    image = installers[0]
    with image.open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    record = {
        "installer": {"name": image.name, "sha256": sha, "bytes": image.stat().st_size},
        "app_inventory": inventory,
        "wrapper_components": components,
        "limits": (
            "Static attribution from pinned source, not a binary symbol proof. "
            "Compiler/IDE/compressor tools are build-only. "
            "Delphi RTL/VCL provenance needs independent review."
        ),
    }
    (output / "inventory.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    sbom = json.loads((app_audit / "sbom.cdx.json").read_text(encoding="utf-8"))
    notices = (bundle / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    notices += "\n\n# Installer runtime\n\nMade using RemObjects Pascal Script: https://www.remobjects.com/ps.aspx\n"
    for item in components:
        sbom["components"].append(
            {
                "type": "library",
                "bom-ref": "installer-" + item["name"],
                "name": item["name"],
                "version": item["version"],
                "licenses": [{"expression": item["license"]}],
                "externalReferences": [{"type": "vcs", "url": item["source"]}],
            }
        )
        notice = (ROOT / "packaging/licenses/inno" / item["notice"]).read_text(encoding="utf-8")
        notices += f"\n## {item['name']} {item['version']}\n\n{item['source']}\n\n{notice}\n"
    encoded = json.dumps(sbom, indent=2)
    errors = JsonStrictValidator(SchemaVersion.V1_6).validate_str(encoded)
    if errors:
        raise ValueError(f"Installer SBOM schema errors: {errors}")
    (output / "sbom.cdx.json").write_text(encoded + "\n", encoding="utf-8")
    (output / "THIRD_PARTY_NOTICES.md").write_text(notices, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=ROOT / "dist/Dusty")
    args = parser.parse_args()
    generate(args.bundle, ROOT / "build/packaging/audit", ROOT / "build/installer")


if __name__ == "__main__":
    main()
