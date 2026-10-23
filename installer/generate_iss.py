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
from dusty.app.model_manager import format_size  # noqa: E402
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
        + "\n\nTHIRD-PARTY NOTICES\n\n"
        + runtime_notices(bundle)
    )
    (output / "LICENSE.txt").write_text(license_text, encoding="utf-8", newline="\n")
    (output / "DUSTY-LICENSE.txt").write_text(
        (ROOT / "LICENSE").read_text(encoding="utf-8")
        + "\n\n"
        + (ROOT / "NOTICE").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (output / "MICROSOFT-LICENSE.txt").write_bytes(
        (ROOT / "packaging/licenses/microsoft/runtime-eula.txt").read_bytes()
    )
    (output / "THIRD_PARTY_NOTICES.md").write_text(
        runtime_notices(bundle), encoding="utf-8", newline="\n"
    )
    setup_models = []
    for index, (key, model) in enumerate(manifest.models.items()):
        label = (
            f"{M.MODEL_TECHNICAL[key]}: {M.MODEL_QUALITY[key]} ({format_size(model.size_bytes)})"
        )
        detail = (
            "#13#10 + "
            + pascal(f"{M.MANAGER_HEADERS[1]}: {M.MODEL_BEST_FOR[key]}")
            + " + #13#10 + "
            + pascal(M.MODEL_NOTE[key])
        )
        recommended = label.replace(
            M.MODEL_TECHNICAL[key], M.RECOMMENDED.format(name=M.MODEL_TECHNICAL[key]), 1
        )
        setup_models += [
            f"  ModelIds[{index}] := {pascal(key)};",
            f"  ModelBytes[{index}] := {model.size_bytes};",
            f"  ModelNames[{index}] := {pascal(M.MODEL_TECHNICAL[key])};",
            f"  ModelFiles[{index}] := {pascal(model.file_name)};",
            f"  ModelLabels[{index}] := {pascal(label)};",
            f"  ModelRecommendedLabels[{index}] := {pascal(recommended)};",
            f"  ModelDetails[{index}] := {detail};",
            f"  ModelsPage.Add(ModelLabels[{index}] + ModelDetails[{index}]);",
        ]
    template = (ROOT / "installer/dusty.iss.template").read_text(encoding="utf-8")
    template = template.replace(
        "@@WIZARD_CODE@@", (ROOT / "installer/wizard.iss").read_text(encoding="utf-8")
    )
    consent_cases = []
    for mask in range(1, 1 << len(manifest.models)):
        chosen = [
            (key, item) for i, (key, item) in enumerate(manifest.models.items()) if mask & (1 << i)
        ]
        names = [M.MODEL_TECHNICAL[key] for key, _ in chosen] + [M.VOICE_MODEL]
        total = sum(item.size_bytes for _, item in chosen) + raw["vad"][0]["size_bytes"]
        consent = M.DOWNLOAD_CONFIRM.format(
            names=M.DOWNLOAD_NAMES_JOIN.join(names), size=format_size(total)
        )
        consent_cases.append(f"    {mask}: Result := {pascal(consent)};")
    values = {
        "VERSION": __version__,
        "BUNDLE": str(bundle.resolve()),
        "MODEL_COUNT": str(len(manifest.models)),
        "MODEL_SETUP": "\n".join(setup_models),
        "VAD_BYTES": str(raw["vad"][0]["size_bytes"]),
        "VAD_FILE": raw["vad"][0]["file_name"],
        "VOICE_NAME": M.VOICE_MODEL,
        "VOICE_DESCRIPTION": pascal(
            f"{M.VOICE_MODEL} ({format_size(raw['vad'][0]['size_bytes'])}): "
            f"{M.MODEL_QUALITY['silero-vad']}. "
            f"{M.MANAGER_HEADERS[1]}: {M.MODEL_BEST_FOR['silero-vad']}. "
            f"{M.MODEL_NOTE['silero-vad']}"
        ),
        "RECOMMENDED_SUFFIX": M.RECOMMENDED.format(name=""),
        "MODEL_REVIEW": M.MODEL_REVIEW,
        "MIN_RAM": str(raw["models"][0]["recommended_min_ram_gb"] * 1_000_000_000),
        "CONSENT_CASES": "\n".join(consent_cases),
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
