"""Installer static licenses must not inherit the wrapper's approval."""

import hashlib
import json
import zipfile
from pathlib import Path

from tools import check_installer_licenses as gate
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


def test_retained_runtime_source_and_notices_fail_on_changes(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    licenses = root / "packaging/licenses/inno"
    licenses.mkdir(parents=True)
    directory = root / "build/installer"
    directory.mkdir(parents=True)
    original = b"unchanged source\r\n"
    proof = {
        "commit": "pinned",
        "runtime_files": ["Setup.e32", "SetupLdr.e32"],
        "jedi_sources": [
            {"path": "Components/Theme.pas", "sha256": hashlib.sha256(original).hexdigest()}
        ],
    }
    proof_path = licenses / "runtime-source.json"
    proof_path.write_text(json.dumps(proof))
    (licenses / "source.json").write_text(json.dumps({"compiler_sha256": "bootstrap"}))
    (licenses / "jedi-uxtheme.txt").write_bytes(b"MPL and notice")
    (directory / "runtime-inputs.json").write_text(
        json.dumps(
            {
                "source_commit": "pinned",
                "source_review_sha256": hashlib.sha256(proof_path.read_bytes()).hexdigest(),
                "compiler_bootstrap_sha256": "bootstrap",
                "files": [{"name": name} for name in proof["runtime_files"]],
            }
        )
    )
    (directory / "THIRD_PARTY_NOTICES.md").write_text("all notices")
    monkeypatch.setattr(gate, "ROOT", root)
    monkeypatch.setattr(gate, "runtime_notices", lambda _: "all notices")

    def pack(contents):
        with zipfile.ZipFile(directory / "installer-jedi-source.zip", "w") as archive:
            archive.writestr("Theme.pas", contents)
            archive.writestr("LICENSE-and-notices.txt", b"MPL and notice")

    pack(original)
    assert gate.check_retained_sources(directory) == []
    pack(b"modified")
    assert "Retained JEDI source differs from upstream" in gate.check_retained_sources(directory)
