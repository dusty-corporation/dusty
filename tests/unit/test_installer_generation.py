"""The installer must preserve the catalog trust anchor and full protective terms."""

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from installer.generate_iss import generate

ROOT = Path(__file__).resolve().parents[2]


def test_installer_generator_script_entry_point():
    result = subprocess.run(
        [sys.executable, str(ROOT / "installer/generate_iss.py"), "--help"],
        capture_output=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr.decode()


def test_installer_uses_complete_licenses_and_unchanged_manifest(tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "resources").mkdir(parents=True)
    manifest = ROOT / "resources/models.json"
    shutil.copyfile(manifest, bundle / "resources/models.json")
    (bundle / "THIRD_PARTY_NOTICES.md").write_text("Audited app notices\n")
    output = tmp_path / "generated"
    script = generate(output, bundle)
    license_text = (output / "LICENSE.txt").read_text(encoding="utf-8")
    for source in (
        "LICENSE",
        "NOTICE",
        "packaging/licenses/microsoft/runtime-eula.txt",
        "packaging/licenses/inno/license.txt",
    ):
        assert (ROOT / source).read_text(encoding="utf-8") in license_text
    inputs = json.loads((output / "inputs.json").read_text())
    assert inputs["manifest_sha256"] == hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert (
        inputs["license_sha256"]
        == hashlib.sha256((output / "LICENSE.txt").read_bytes()).hexdigest()
    )
    assert inputs["draft_only"]
    text = script.read_text(encoding="utf-8")
    assert "@@" not in text
    assert "PrivilegesRequired=lowest" in text
    assert "DownloadTemporaryFile(" not in text
    assert "UninstallDelete" not in text  # No broad recursive deletion of user data.
    assert "--installer-test --backend " in text
    assert "Stage := 4" in text  # Smallest model's additional CPU-only check.
    assert "@@" not in text
    assert "{param:ACCEPTTERMS|}" in text
    assert "{param:ALLOWDOWNLOAD|}" in text
    assert "{param:REMOVEMODELS|}" in text
    assert "CurStep = ssPostInstall" in text
    code = text.split("[Code]", 1)[1]
    assert not re.search(r"(?m)^\s*\[", code), "Inno parses leading arrays as sections"
    for key in ("MODEL_BEST_FOR", "MODEL_NOTE"):
        from dusty.app import messages as M

        for value in getattr(M, key).values():
            assert value.replace("'", "''") in text
    assert "Finish without a model" in text
    assert "GraphicsCandidate" not in text
    assert "--probe-vulkan --out" in text
    assert "'.part'" in text


def test_installer_rejects_tampered_catalog(tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "resources").mkdir(parents=True)
    data = json.loads((ROOT / "resources/models.json").read_text())
    data["models"][0]["sha256"] = "invalid"
    (bundle / "resources/models.json").write_text(json.dumps(data))
    with pytest.raises(ValueError):
        generate(tmp_path / "generated", bundle)
