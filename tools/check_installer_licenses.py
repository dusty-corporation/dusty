"""Fail closed on the installer wrapper's additional redistribution license."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.check_licenses import allowed_license  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def check() -> list[str]:
    pins = json.loads((ROOT / "packaging/licenses/inno/source.json").read_text(encoding="utf-8"))
    license_file = ROOT / "packaging/licenses/inno/license.txt"
    findings = []
    if hashlib.sha256(license_file.read_bytes()).hexdigest() != pins["repository_sha256"]:
        findings.append("Inno Setup license text differs from its pinned provenance")
    if not allowed_license("inno-setup-installer", "InnoSetup"):
        findings.append(
            "Inno Setup 6.7.3: InnoSetup is not allowlisted; ISSUE-017 needs PM decision"
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "build/installer/license-findings.txt"
    )
    args = parser.parse_args()
    findings = check()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(findings) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(findings) if findings else "Installer license check passed")
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
