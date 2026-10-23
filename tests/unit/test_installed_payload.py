"""The installed payload must be byte-identical to the audited app bundle."""

import shutil
from pathlib import Path

from tools.check_installed_payload import check

ROOT = Path(__file__).resolve().parents[2]


def test_installed_inventory_rejects_changes_and_extra_files(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "app.exe").write_bytes(b"audited app")
    installed = tmp_path / "installed"
    shutil.copytree(bundle, installed)
    (installed / "licenses").mkdir()
    shutil.copyfile(
        ROOT / "packaging/licenses/inno/license.txt", installed / "licenses/inno-setup.txt"
    )
    (installed / "unins001.exe").write_bytes(b"generated uninstaller")
    assert check(installed, bundle)[0] == []
    (installed / "app.exe").write_bytes(b"changed app")
    (installed / "surprise.dll").write_bytes(b"unexpected")
    findings, checked = check(installed, bundle)
    assert len(checked) == 4
    assert any("payload changed" in item for item in findings)
    assert any("Uninventoried" in item for item in findings)
