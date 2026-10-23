"""Release versions, asset closure, and upload order must fail closed."""

import hashlib
import json
from pathlib import Path

import pytest

from tools.release_assets import stage, verify_checksum
from tools.release_version import apply, versions

ROOT = Path(__file__).resolve().parents[2]


def test_version_mapping_and_metadata(tmp_path):
    assert versions("v0.5.0-m5.2") == ("0.5.0.dev2", "0.5.0-m5.2", "0.5.0.2")
    for name in ("pyproject.toml", "src/dusty/__init__.py", "uv.lock"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / name).read_bytes())
    apply(tmp_path, "v0.5.0-m5.2")
    for name in ("pyproject.toml", "src/dusty/__init__.py", "uv.lock"):
        assert '"0.5.0.dev2"' in (tmp_path / name).read_text()


@pytest.mark.parametrize("tag", ["v1.0.0", "v0.5.0-m5.0", "v0.5.0-m5.1x", "v0.5.0-m5.65536"])
def test_unapproved_tag_rejected(tag):
    with pytest.raises(ValueError):
        versions(tag)


def test_release_assets_exact_closure_and_hashes(tmp_path):
    source = tmp_path / "input/installer"
    source.mkdir(parents=True)
    for name, data in {
        "output/setup.exe": b"audited installer",
        "THIRD_PARTY_NOTICES.md": b"audited notices",
        "sbom.cdx.json": json.dumps({"bomFormat": "CycloneDX"}).encode(),
        "installer-jedi-source.zip": b"retained source",
    }.items():
        path = source / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(data)
    output = tmp_path / "release"
    stage(tmp_path / "input", output, "v0.5.0-m5.1")
    assert len(list(output.iterdir())) == 5
    for line in (output / "SHA256SUMS.txt").read_text().splitlines():
        sha, name = line.split("  ")
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == sha
    with pytest.raises(ValueError):
        stage(tmp_path / "input", output, "v0.5.0-m5.1")
    (source / "output/extra.exe").write_bytes(b"unreviewed")
    with pytest.raises(ValueError):
        stage(tmp_path / "input", tmp_path / "rejected", "v0.5.0-m5.1")


def test_draft_release_upload_requires_reusable_gates():
    text = (ROOT / ".github/workflows/release.yml").read_text()
    assert "needs: [validate, gates]" in text
    assert "uses: ./.github/workflows/ci.yml" in text
    assert "--verify-tag --draft --prerelease" in text
    assert "continue-on-error" not in text
    assert text.index("Stage approved assets") < text.index("gh release create")


def test_prior_installer_is_verified_before_execution(tmp_path):
    file = tmp_path / "setup.exe"
    file.write_bytes(b"gated installer")
    sums = tmp_path / "SHA256SUMS.txt"
    line = hashlib.sha256(file.read_bytes()).hexdigest() + "  setup.exe\n"
    sums.write_text(line)
    verify_checksum(file, sums)
    sums.write_text(line + line)
    with pytest.raises(ValueError):
        verify_checksum(file, sums)
    sums.write_text(line)
    file.write_bytes(b"changed installer")
    with pytest.raises(ValueError):
        verify_checksum(file, sums)


def test_upgrade_audits_the_new_installed_version():
    text = (ROOT / "tools/test_installer.ps1").read_text()
    before, after = text.split("$Installer = $currentInstaller", 1)
    for gate in ("check_installed_payload.py", "test_network_isolation.ps1", "check_pe_imports.py"):
        assert gate not in before
        assert after.index(gate) < after.index("Uninstall-App 'no'")
    final = after.split("# A two-version upgrade", 1)[1]
    assert final.index("Install-App") < final.index("Complete-InstallerAudit")
    assert "current_installer_fresh_download_wfp='passed'" in final


def test_final_release_rejects_missing_or_false_upgrade_and_wfp_evidence(tmp_path):
    source = tmp_path / "input/installer"
    (source / "output").mkdir(parents=True)
    for name in ("output/setup.exe", "THIRD_PARTY_NOTICES.md", "installer-jedi-source.zip"):
        (source / name).write_bytes(b"gated asset")
    (source / "sbom.cdx.json").write_text('{"bomFormat":"CycloneDX"}')
    with pytest.raises(ValueError, match="receipts"):
        stage(tmp_path / "input", tmp_path / "missing", "v0.5.0-m5.6")
    (source / "acceptance").mkdir()
    receipt = {
        "two_distinct_versions": True,
        "current_installer_fresh_download_wfp": "passed",
        "installed_wfp": "passed",
        "upgrade_models_preserved_with_downloader_blocked": "passed",
        "uninstall_keep_models": "passed",
        "uninstall_remove_models": "passed",
        "user_outputs_unchanged": True,
    }
    audit = dict(installer=0, gui=0, native=0, fetch_allowed=4, fetch_blocked=0)
    audit["calibration_blocked_event"] = True
    summary = source / "acceptance/summary.json"
    wfp = source / "acceptance/download-wfp.json"
    summary.write_text(json.dumps(receipt))
    wfp.write_text(json.dumps(audit))
    stage(tmp_path / "input", tmp_path / "accepted", "v0.5.0-m5.6")
    receipt["two_distinct_versions"] = False
    summary.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="true upgrade"):
        stage(tmp_path / "input", tmp_path / "same-build", "v0.5.0-m5.6")
    receipt["two_distinct_versions"] = True
    summary.write_text(json.dumps(receipt))
    audit["installer"] = 1
    wfp.write_text(json.dumps(audit))
    with pytest.raises(ValueError, match="zero-event"):
        stage(tmp_path / "input", tmp_path / "network-event", "v0.5.0-m5.6")
