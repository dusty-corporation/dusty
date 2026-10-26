"""Release versions, asset closure, and upload order must fail closed."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.release_assets import stage, verify_checksum
from tools.release_version import apply, versions

ROOT = Path(__file__).resolve().parents[2]


def test_version_mapping_and_metadata(tmp_path):
    assert versions("v1.0.0") == ("1.0.0", "1.0.0", "1.0.0.0")
    assert versions("v0.5.0-m5.2") == ("0.5.0.dev2", "0.5.0-m5.2", "0.5.0.2")
    for name in ("pyproject.toml", "src/dusty/__init__.py", "uv.lock"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / name).read_bytes())
    apply(tmp_path, "v0.5.0-m5.2")
    for name in ("pyproject.toml", "src/dusty/__init__.py", "uv.lock"):
        assert '"0.5.0.dev2"' in (tmp_path / name).read_text()


def test_version_cli_requires_apply_to_modify_a_checkout(tmp_path):
    tool = tmp_path / "tools/release_version.py"
    tool.parent.mkdir()
    tool.write_bytes((ROOT / "tools/release_version.py").read_bytes())
    files = {}
    for name in ("pyproject.toml", "src/dusty/__init__.py", "uv.lock"):
        file = tmp_path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes((ROOT / name).read_bytes())
        files[file] = file.read_bytes()
    subprocess.run([sys.executable, str(tool), "v0.5.0-m5.2"], check=True, timeout=10)
    assert all(file.read_bytes() == content for file, content in files.items())
    subprocess.run([sys.executable, str(tool), "v0.5.0-m5.2", "--apply"], check=True, timeout=10)
    assert all(b"0.5.0.dev2" in file.read_bytes() for file in files)


@pytest.mark.parametrize("tag", ["v1.1.0", "v0.5.0-m5.0", "v0.5.0-m5.1x", "v0.5.0-m5.65536"])
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
    ffmpeg_sources(source)
    output = tmp_path / "release"
    stage(tmp_path / "input", output, "v0.5.0-m5.1")
    assert len(list(output.iterdir())) == 7
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
    assert "--verify-tag --draft" in text
    assert "--prerelease" not in text
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
    text = (ROOT / "tools/test_installer.ps1").read_text(encoding="utf-8")
    before, after = text.split("$Installer = $currentInstaller", 1)
    for gate in ("check_installed_payload.py", "test_network_isolation.ps1", "check_pe_imports.py"):
        assert gate not in before
        assert after.index(gate) < after.index("test_uninstall_ui.ps1")
    final = after.split("# A two-version upgrade", 1)[1]
    assert final.index("Install-App") < final.index("Complete-InstallerAudit")
    assert "current_installer_fresh_download_wfp='passed'" in final


@pytest.mark.parametrize("tag", ["v0.5.0-m5.6", "v1.0.0", "v1.0.1"])
def test_final_release_rejects_missing_or_false_upgrade_and_wfp_evidence(tmp_path, tag):
    source = tmp_path / "input/installer"
    (source / "output").mkdir(parents=True)
    for name in ("output/setup.exe", "THIRD_PARTY_NOTICES.md", "installer-jedi-source.zip"):
        (source / name).write_bytes(b"gated asset")
    (source / "sbom.cdx.json").write_text('{"bomFormat":"CycloneDX"}')
    with pytest.raises(ValueError, match="receipts"):
        stage(tmp_path / "input", tmp_path / "missing", tag)
    (source / "acceptance").mkdir()
    receipt = {
        "previous_tag": ""
        if tag == "v1.0.0"
        else ("v1.0.0" if tag == "v1.0.1" else "v0.5.0-m5.14"),
        "silent_per_user_install": "passed",
        "same_version_reinstall_models_preserved": "passed",
        "two_distinct_versions": tag != "v1.0.0",
        "current_installer_fresh_download_wfp": "passed",
        "installed_wfp": "passed",
        "upgrade_models_preserved_with_downloader_blocked": "passed",
        "uninstall_keep_models": "passed",
        "uninstall_remove_models": "passed",
        "normal_cancel_removes_partial": "passed",
        "preserved_legacy_destination": "passed",
        "protected_install_destination": "passed",
        "user_outputs_unchanged": True,
    }
    audit = dict(installer=0, gui=0, native=0, fetch_allowed=4, fetch_blocked=0)
    audit["calibration_blocked_event"] = True
    summary = source / "acceptance/summary.json"
    wfp = source / "acceptance/download-wfp.json"
    summary.write_text(json.dumps(receipt))
    wfp.write_text(json.dumps(audit))
    ffmpeg_sources(source)
    stage(tmp_path / "input", tmp_path / "accepted", tag)
    if tag == "v1.0.0":
        assert (tmp_path / "accepted/Dusty-1.0.0-Setup.exe").is_file()
    receipt["same_version_reinstall_models_preserved"] = "failed"
    receipt["two_distinct_versions"] = False
    summary.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="reinstall|true upgrade"):
        stage(tmp_path / "input", tmp_path / "same-build", tag)
    receipt["same_version_reinstall_models_preserved"] = "passed"
    receipt["two_distinct_versions"] = tag != "v1.0.0"
    receipt["normal_cancel_removes_partial"] = "failed"
    summary.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        stage(tmp_path / "input", tmp_path / "cancel-failed", tag)
    receipt["normal_cancel_removes_partial"] = "passed"
    receipt["preserved_legacy_destination"] = "failed"
    summary.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        stage(tmp_path / "input", tmp_path / "legacy-destination-failed", tag)
    receipt["preserved_legacy_destination"] = "passed"
    receipt["protected_install_destination"] = "failed"
    summary.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        stage(tmp_path / "input", tmp_path / "protected-install-failed", tag)
    receipt["protected_install_destination"] = "passed"
    summary.write_text(json.dumps(receipt))
    audit["installer"] = 1
    wfp.write_text(json.dumps(audit))
    with pytest.raises(ValueError, match="zero-event"):
        stage(tmp_path / "input", tmp_path / "network-event", tag)


@pytest.mark.parametrize("version", ["1.0.0", "1.0.1"])
def test_executable_version_resource_uses_project_metadata(tmp_path, monkeypatch, version):
    from PyInstaller.utils.win32.versioninfo import load_version_info_from_text_file

    from tools import bundle_version
    from tools.bundle_version import write_version

    monkeypatch.setattr(bundle_version, "__version__", version)
    file = tmp_path / "version.txt"
    write_version(file)
    resource = load_version_info_from_text_file(str(file))
    assert resource.ffi.fileVersionMS == (1 << 16)
    assert resource.ffi.fileVersionLS == int(version.rsplit(".", 1)[1]) << 16
    assert version in file.read_text()
    spec = (ROOT / "packaging/dusty.spec").read_text()
    assert spec.count("version=str(audit / 'version.txt')") == 2


def test_public_release_validation_requires_preceding_published_release():
    from tools.release_policy import needs_receipts, validate

    assert validate("v1.0.0", []) == ("", "")
    assert versions("v1.0.1") == ("1.0.1", "1.0.1", "1.0.1.0")
    prior = {"tagName": "v1.0.0", "isDraft": False, "isPrerelease": False}
    assert validate("v1.0.1", [prior]) == ("v1.0.0", "")
    with pytest.raises(ValueError, match="previous public"):
        validate("v1.0.1", [])
    for key in ("isDraft", "isPrerelease"):
        with pytest.raises(ValueError, match="previous public"):
            validate("v1.0.1", [{**prior, key: True}])
    assert needs_receipts("v1.0.0") and needs_receipts("v1.0.1")
    assert not needs_receipts("v0.5.0-m5.1")
    assert not needs_receipts("v0.5.0-m5.2")
    assert needs_receipts("v0.5.0-m5.3")


def test_release_refuses_missing_ffmpeg_corresponding_source(tmp_path):
    source = tmp_path / "input/installer"
    source.mkdir(parents=True)
    for name in ("setup.exe", "THIRD_PARTY_NOTICES.md", "installer-jedi-source.zip"):
        (source / name).write_bytes(b"gated asset")
    (source / "sbom.cdx.json").write_text('{"bomFormat":"CycloneDX"}')
    with pytest.raises((ValueError, FileNotFoundError), match="ffmpeg|FFmpeg"):
        stage(tmp_path / "input", tmp_path / "release", "v0.5.0-m5.1")


@pytest.fixture(autouse=True)
def synthetic_source_pin(monkeypatch):
    from tools import ffmpeg_source

    monkeypatch.setitem(
        ffmpeg_source.PIN, "sha256", hashlib.sha256(b"synthetic source archive").hexdigest()
    )


def ffmpeg_sources(source):
    from tools.ffmpeg_source import PIN

    (source / PIN["name"]).write_bytes(b"synthetic source archive")
    (source / "build_ffmpeg.sh").write_bytes((ROOT / "native/build_ffmpeg.sh").read_bytes())
