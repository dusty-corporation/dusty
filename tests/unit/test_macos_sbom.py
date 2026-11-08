"""The Mac SBOM describes exactly the files of the finished app, from the notices inventory."""

import hashlib
import json
from pathlib import Path

import pytest

from tools import macos_sbom


def _app(tmp_path: Path) -> tuple[Path, dict]:
    app = tmp_path / "Dusty.app"
    files = {
        "Contents/MacOS/Dusty": b"bootloader",
        "Contents/Helpers/bin/cpu/whisper-cli": b"engine",
        "Contents/Frameworks/QtCore.framework/Versions/A/QtCore": b"qt",
        "Contents/Frameworks/QtCore.framework/Versions/A/_CodeSignature/CodeResources": b"seal",
        "Contents/_CodeSignature/CodeResources": b"app seal",
        "Contents/Resources/THIRD_PARTY_NOTICES.md": b"notices",
    }
    for relative, data in files.items():
        (app / relative).parent.mkdir(parents=True, exist_ok=True)
        (app / relative).write_bytes(data)
    (app / "Contents/THIRD_PARTY_NOTICES.md").symlink_to("Resources/THIRD_PARTY_NOTICES.md")
    component = {"copyright": "Copyright", "source": "https://example.invalid"}
    inventory = {
        "components": {
            "dusty": {"name": "Dusty", "version": "1.1.0", "license": "Apache-2.0", **component},
            "whisper.cpp": {
                "name": "whisper.cpp",
                "version": "v1.9.5",
                "license": "MIT",
                **component,
            },
            "qt": {"name": "Qt", "version": "6.9.2", "license": "LGPL-3.0-only", **component},
            "fixture": {
                "name": "JFK",
                "version": "1961",
                "license": "LicenseRef-Public-Domain",
                **component,
            },
            "bootloader": {
                "name": "PyInstaller bootloader",
                "version": "6.16.0",
                "license": "GPL-2.0-or-later WITH PyInstaller-bootloader-exception; hooks",
                **component,
            },
        },
        "files": {
            "Contents/MacOS/Dusty": ["bootloader"],
            "Contents/Helpers/bin/cpu/whisper-cli": ["whisper.cpp"],
            "Contents/Frameworks/QtCore.framework/Versions/A/QtCore": ["qt"],
        },
        "open_items": [],
    }
    return app, inventory


def test_sbom_lists_every_file_with_its_hash_and_component(tmp_path):
    app, inventory = _app(tmp_path)
    sbom = macos_sbom.build(app, inventory)
    files = {c["name"]: c for c in sbom["components"] if c["type"] == "file"}
    assert set(files) == set(macos_sbom.app_files(app))
    engine = files["Contents/Helpers/bin/cpu/whisper-cli"]
    assert engine["hashes"] == [
        {"alg": "SHA-256", "content": hashlib.sha256(b"engine").hexdigest()}
    ]
    owners = {d["ref"][5:]: d["dependsOn"] for d in sbom["dependencies"]}
    # Seals belong to the code they seal; the notices and the app seal to Dusty.
    assert owners[
        "Contents/Frameworks/QtCore.framework/Versions/A/_CodeSignature/CodeResources"
    ] == ["qt"]
    assert owners["Contents/_CodeSignature/CodeResources"] == ["dusty"]
    assert owners["Contents/Resources/THIRD_PARTY_NOTICES.md"] == ["dusty"]
    assert "Contents/THIRD_PARTY_NOTICES.md" not in owners


def test_licenses_are_expressions_only_when_valid_spdx(tmp_path):
    app, inventory = _app(tmp_path)
    sbom = macos_sbom.build(app, inventory)
    licenses = {
        c["bom-ref"]: c["licenses"][0] for c in sbom["components"] if c["type"] == "library"
    }
    assert licenses["qt"] == {"expression": "LGPL-3.0-only"}
    assert licenses["fixture"] == {"expression": "LicenseRef-Public-Domain"}
    assert "name" in licenses["bootloader"]["license"]


@pytest.mark.parametrize("damage", ["unlisted", "missing", "orphan", "open"])
def test_sbom_stops_when_app_and_inventory_disagree(tmp_path, damage):
    app, inventory = _app(tmp_path)
    if damage == "unlisted":
        (app / "Contents/Resources/extra.dylib").write_bytes(b"unknown")
    elif damage == "missing":
        (app / "Contents/Helpers/bin/cpu/whisper-cli").unlink()
    elif damage == "orphan":
        inventory["files"]["Contents/MacOS/Dusty"] = ["nobody"]
    else:
        inventory["open_items"] = ["a license text is missing"]
    with pytest.raises(macos_sbom.SbomError):
        macos_sbom.build(app, inventory)


def test_cli_refuses_to_overwrite(tmp_path):
    app, inventory = _app(tmp_path)
    inventory_path = tmp_path / "inventory.json"
    inventory_path.write_text(json.dumps(inventory))
    output = tmp_path / "sbom.cdx.json"
    assert macos_sbom.main([str(app), str(inventory_path), str(output)]) == 0
    assert json.loads(output.read_text())["bomFormat"] == "CycloneDX"
    assert macos_sbom.main([str(app), str(inventory_path), str(output)]) == 1
