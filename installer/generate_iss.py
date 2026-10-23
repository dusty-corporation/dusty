"""Generate a draft Inno Setup 6 script from the bundled model trust anchor."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dusty import __version__  # noqa: E402
from dusty.app import messages as M  # noqa: E402
from dusty.models import load_manifest  # noqa: E402
from tools.installer_notices import runtime_notices  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def pascal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def generate(output: Path, bundle: Path) -> Path:
    manifest = load_manifest(bundle / "resources/models.json")
    raw = json.loads((bundle / "resources/models.json").read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    license_text = (
        "DUSTY: APACHE LICENSE 2.0\n\n"
        + (ROOT / "LICENSE").read_text(encoding="utf-8")
        + "\n\nDUSTY NOTICE\n\n"
        + (ROOT / "NOTICE").read_text(encoding="utf-8")
        + "\n\nMICROSOFT DISTRIBUTABLE CODE: PROTECTIVE END-USER TERMS\n"
        "The following terms apply to Microsoft's runtime components only. They do not "
        "restrict rights under the Apache or LGPL licenses for other components.\n\n"
        + (ROOT / "packaging/licenses/microsoft/runtime-eula.txt").read_text(encoding="utf-8")
        + "\n\nINNO SETUP (INSTALLER RUNTIME)\n\n"
        + (ROOT / "packaging/licenses/inno/license.txt").read_text(encoding="utf-8")
    )
    (output / "LICENSE.txt").write_text(license_text, encoding="utf-8", newline="\n")
    (output / "THIRD_PARTY_NOTICES.md").write_text(
        runtime_notices(bundle), encoding="utf-8", newline="\n"
    )
    setup_models = []
    for index, (key, model) in enumerate(manifest.models.items()):
        label = f"{M.MODEL_NAMES[key]}: {model.size_bytes / 1_000_000:.1f} MB"
        setup_models += [
            f"  ModelIds[{index}] := {pascal(key)};",
            f"  ModelBytes[{index}] := {model.size_bytes};",
            f"  ModelsPage.Add({pascal(label)});",
        ]
    template = (ROOT / "installer/dusty.iss.template").read_text(encoding="utf-8")
    values = {
        "VERSION": __version__,
        "BUNDLE": str(bundle.resolve()),
        "MODEL_COUNT": str(len(manifest.models)),
        "MODEL_SETUP": "\n".join(setup_models),
        "VAD_BYTES": str(raw["vad"][0]["size_bytes"]),
        "MESSAGES": "\n".join(f"{key}={value}" for key, value in M.INSTALLER.items()),
        "INNO_LICENSE": str(ROOT / "packaging/licenses/inno/license.txt"),
        "INSTALLER_NOTICES": str((output / "THIRD_PARTY_NOTICES.md").resolve()),
        "JEDI_SOURCE": str((output / "installer-jedi-source.zip").resolve()),
    }
    for key, value in values.items():
        template = template.replace("@@" + key + "@@", value)
    script = output / "dusty.iss"
    script.write_text(template, encoding="utf-8", newline="\r\n")
    (output / "inputs.json").write_text(
        json.dumps(
            {
                "manifest_sha256": hashlib.sha256(
                    (bundle / "resources/models.json").read_bytes()
                ).hexdigest(),
                "license_sha256": hashlib.sha256((output / "LICENSE.txt").read_bytes()).hexdigest(),
                "inno_version": "6.7.3",
                "draft_only": True,
            },
            indent=2,
        ),
        encoding="utf-8",
        newline="\n",
    )
    return script


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=ROOT / "dist/Dusty")
    parser.add_argument("--output", type=Path, default=ROOT / "build/installer")
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        raise ValueError("Installer output must stay in the repository")
    print(generate(output, args.bundle.resolve()))


if __name__ == "__main__":
    main()
