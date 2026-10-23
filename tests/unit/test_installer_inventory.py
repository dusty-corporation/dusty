"""Installer static licenses must not inherit the wrapper's approval."""

import json
from pathlib import Path

from tools.check_installer_licenses import check_inventory

ROOT = Path(__file__).resolve().parents[2]


def test_installer_approved_static_inventory_and_notice_tamper(tmp_path):
    pins = json.loads((ROOT / "packaging/licenses/inno/source.json").read_text())
    rows = json.loads((ROOT / "packaging/licenses/inno/components.json").read_text())
    wrapper = {
        "name": "inno-setup-installer",
        "license": "InnoSetup",
        "notice": "license.txt",
        "notice_sha256": pins["repository_sha256"],
    }
    file = tmp_path / "inventory.json"
    file.write_text(json.dumps({"wrapper_components": [wrapper, *rows]}))
    findings = check_inventory(file)
    assert findings == []
    wrapper["notice_sha256"] = "0" * 64
    file.write_text(json.dumps({"wrapper_components": [wrapper, *rows]}))
    assert any("notice hash changed" in item for item in check_inventory(file))
