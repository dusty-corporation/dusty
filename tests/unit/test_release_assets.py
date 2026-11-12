"""Release versions, asset closure, and upload order must fail closed."""

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from dusty import __version__
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


@pytest.mark.parametrize(
    "tag",
    ["v2.0.0", "v1.01.0", "v1.1", "v1.1.0-rc1", "v0.5.0-m5.0", "v0.5.0-m5.1x", "v0.5.0-m5.65536"],
)
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


@pytest.mark.parametrize("tag", ["v0.5.0-m5.6", "v1.0.0", "v1.0.1", "v1.1.0", "v1.2.0"])
def test_final_release_rejects_missing_or_false_upgrade_and_wfp_evidence(tmp_path, tag):
    previous = {"v1.0.0": "", "v1.0.1": "v1.0.0", "v1.1.0": "v1.0.1", "v1.2.0": "v1.1.3"}.get(
        tag, "v0.5.0-m5.14"
    )
    source = tmp_path / "input/installer"
    (source / "output").mkdir(parents=True)
    for name in ("output/setup.exe", "THIRD_PARTY_NOTICES.md", "installer-jedi-source.zip"):
        (source / name).write_bytes(b"gated asset")
    (source / "sbom.cdx.json").write_text('{"bomFormat":"CycloneDX"}')
    mac = (
        mac_inputs(tmp_path / "mac", tag[1:], previous[1:] if tag == "v1.2.0" else None)
        if tag in {"v1.1.0", "v1.2.0"}
        else None
    )
    with pytest.raises(ValueError, match="receipts"):
        stage(tmp_path / "input", tmp_path / "missing", tag, previous, mac)
    (source / "acceptance").mkdir()
    receipt = {
        "previous_tag": previous,
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
    stage(tmp_path / "input", tmp_path / "accepted", tag, previous, mac)
    if tag == "v1.0.0":
        assert (tmp_path / "accepted/Dusty-1.0.0-Setup.exe").is_file()
    if tag == "v1.2.0":
        assert (tmp_path / "accepted/Dusty-1.2.0-Setup.exe").is_file()
        assert (tmp_path / "accepted/Dusty-1.2.0-macos-arm64.dmg").is_file()
    if tag == "v1.1.0":
        assert (tmp_path / "accepted/Dusty-1.1.0-Setup.exe").is_file()
        # The previous tag comes from the release workflow's validate job.
        with pytest.raises(ValueError, match="previous public release tag"):
            stage(tmp_path / "input", tmp_path / "no-previous", tag, mac_source=mac)
        with pytest.raises(ValueError, match="true upgrade"):
            stage(tmp_path / "input", tmp_path / "wrong-previous", tag, "v1.0.0", mac)
    receipt["same_version_reinstall_models_preserved"] = "failed"
    receipt["two_distinct_versions"] = False
    summary.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="reinstall|true upgrade"):
        stage(tmp_path / "input", tmp_path / "same-build", tag, previous, mac)
    receipt["same_version_reinstall_models_preserved"] = "passed"
    receipt["two_distinct_versions"] = tag != "v1.0.0"
    receipt["normal_cancel_removes_partial"] = "failed"
    summary.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        stage(tmp_path / "input", tmp_path / "cancel-failed", tag, previous, mac)
    receipt["normal_cancel_removes_partial"] = "passed"
    receipt["preserved_legacy_destination"] = "failed"
    summary.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        stage(tmp_path / "input", tmp_path / "legacy-destination-failed", tag, previous, mac)
    receipt["preserved_legacy_destination"] = "passed"
    receipt["protected_install_destination"] = "failed"
    summary.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        stage(tmp_path / "input", tmp_path / "protected-install-failed", tag, previous, mac)
    receipt["protected_install_destination"] = "passed"
    summary.write_text(json.dumps(receipt))
    audit["installer"] = 1
    wfp.write_text(json.dumps(audit))
    with pytest.raises(ValueError, match="zero-event"):
        stage(tmp_path / "input", tmp_path / "network-event", tag, previous, mac)


# The macOS bundle version is covered by test_project_version_matches_package
# and test_plist_findings in test_macos_packaging.
@pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows-only: PE version resource read with PyInstaller's win32 versioninfo",
)
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
    # Every executable carries it: dusty, dusty-fetch and each helper program.
    assert spec.count("EXE(") == 3
    assert spec.count("version=str(audit / 'version.txt')") == spec.count("EXE(")


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
    # A minor release follows the newest published release, here 1.0.1.
    assert versions("v1.1.0") == ("1.1.0", "1.1.0", "1.1.0.0")
    v100 = prior
    v101 = {**prior, "tagName": "v1.0.1"}
    draft = {"tagName": "v1.0.2", "isDraft": True, "isPrerelease": False}
    engine = {"tagName": "engine-v3", "isDraft": False, "isPrerelease": True}
    assert validate("v1.1.0", [v101, v100, draft, engine]) == ("v1.0.1", "")
    assert validate("v1.1.0", [v100, v101]) == ("v1.0.1", "")
    for higher in ("v1.1.0", "v1.2.0", "v1.10.0"):
        with pytest.raises(ValueError, match="higher version"):
            validate("v1.1.0", [v101, {**prior, "tagName": higher}])
    with pytest.raises(ValueError, match="previous public"):
        validate("v1.1.0", [draft, engine])
    assert needs_receipts("v1.1.0")
    # 1.1.0, 1.1.1 and 1.1.2 were never released, so 1.1.3 also follows 1.0.1.
    assert validate("v1.1.3", [v101, v100, draft, engine]) == ("v1.0.1", "")
    # 1.2.0 follows the published 1.1.3 on both platforms.
    v113 = {**prior, "tagName": "v1.1.3"}
    assert validate("v1.2.0", [v113, v101, v100, draft, engine]) == ("v1.1.3", "")
    assert validate("v1.2.0", [v100, v113, v101]) == ("v1.1.3", "")
    with pytest.raises(ValueError, match="higher version"):
        validate("v1.2.0", [v113, {**prior, "tagName": "v1.2.0"}])
    with pytest.raises(ValueError, match="previous public"):
        validate("v1.2.0", [{**v113, "isDraft": True}])
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


def mac_inputs(folder: Path, display: str, previous: str | None = None) -> Path:
    """The release files the macos CI job keeps, as tools.release_assets expects them.

    previous is the version the upgrade scenario installed first, from 1.2.0 on;
    its rows have the shape tools/mac_upgrade_check.py writes, such as
    {"step": "old app --version", "observed": "exit 0, Dusty 1.1.3"}.
    """
    folder.mkdir(parents=True)
    name = f"Dusty-{display}-macos-arm64.dmg"
    image = folder / name
    image.write_bytes(b"audited disk image")
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    (folder / (name + ".sha256")).write_text(f"{digest}  {name}\n")
    manifest = {
        "image": name,
        "version": display,
        "bundle_id": "org.dusty.Dusty",
        "sha256": digest,
        "items": ["Applications", "Dusty.app"],
    }
    (folder / "dmg-manifest.json").write_text(json.dumps(manifest))
    (folder / "bundle-check.json").write_text(
        json.dumps({"findings": [], "summary": {"macho_files": 33}})
    )
    rows = [
        {"scenario": scenario, "step": "self-test", "result": "pass"}
        for scenario in ("1 first run", "2 upgrade", "3 remove and reinstall", "4 moved app")
    ] + [{"scenario": "4 moved app", "step": "quarantine", "result": "info"}]
    if previous is not None:
        rows += [
            {"scenario": "2 upgrade", "step": "old app --version", "result": "pass"}
            | {"observed": f"exit 0, Dusty {previous}"},
            {"scenario": "2 upgrade", "step": "new app --version", "result": "pass"}
            | {"observed": f"exit 0, Dusty {display}"},
        ]
    (folder / "results.json").write_text(json.dumps(rows))
    (folder / "sbom.cdx.json").write_text('{"bomFormat":"CycloneDX"}')
    (folder / "THIRD_PARTY_NOTICES.md").write_text("Mac notices")
    (folder / "build_ffmpeg-macos.sh").write_bytes(
        (ROOT / "native/macos/build_ffmpeg.sh").read_bytes()
    )
    return folder


def windows_inputs(folder: Path) -> Path:
    source = folder / "installer"
    (source / "output").mkdir(parents=True)
    for name in ("output/setup.exe", "THIRD_PARTY_NOTICES.md", "installer-jedi-source.zip"):
        (source / name).write_bytes(b"gated asset")
    (source / "sbom.cdx.json").write_text('{"bomFormat":"CycloneDX"}')
    ffmpeg_sources(source)
    return folder


@pytest.fixture
def no_receipts(monkeypatch):
    """The Windows receipts have their own test; these cases check the Mac inputs."""
    from tools import release_assets

    monkeypatch.setattr(release_assets, "needs_receipts", lambda _tag: False)


def test_combined_release_needs_mac_from_1_1_0_only():
    from tools.release_assets import needs_mac

    assert needs_mac("v1.1.0") and needs_mac("v1.2.3") and needs_mac("v1.10.0")
    assert not needs_mac("v1.0.1") and not needs_mac("v1.0.2") and not needs_mac("v0.5.0-m5.6")


def test_combined_release_has_both_platforms_under_one_checksum_file(tmp_path, no_receipts):
    windows = windows_inputs(tmp_path / "windows")
    mac = mac_inputs(tmp_path / "mac", "1.1.0")
    output = tmp_path / "release"
    stage(windows, output, "v1.1.0", "v1.0.1", mac)
    names = sorted(path.name for path in output.iterdir())
    assert names == sorted(
        [
            "Dusty-1.1.0-Setup.exe",
            "Dusty-1.1.0-macos-arm64.dmg",
            "THIRD_PARTY_NOTICES.md",
            "THIRD_PARTY_NOTICES-macos.md",
            "dusty-1.1.0-sbom.json",
            "dusty-1.1.0-macos-arm64-sbom.json",
            "installer-jedi-source.zip",
            "ffmpeg-n9.0.2-946fcce.tar.gz",
            "build_ffmpeg.sh",
            "build_ffmpeg-macos.sh",
            "SHA256SUMS.txt",
        ]
    )
    sums = (output / "SHA256SUMS.txt").read_text().splitlines()
    assert len(sums) == len(names) - 1
    for line in sums:
        sha, name = line.split("  ")
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == sha
    assert (output / "THIRD_PARTY_NOTICES-macos.md").read_text() == "Mac notices"


def test_combined_release_without_mac_inputs_fails_closed(tmp_path, no_receipts):
    windows = windows_inputs(tmp_path / "windows")
    with pytest.raises(ValueError, match="Mac disk image inputs"):
        stage(windows, tmp_path / "release", "v1.1.0", "v1.0.1")
    assert not (tmp_path / "release").exists()


def test_windows_servicing_release_takes_no_mac_inputs(tmp_path, no_receipts):
    windows = windows_inputs(tmp_path / "windows")
    mac = mac_inputs(tmp_path / "mac", "1.0.2")
    with pytest.raises(ValueError, match="from 1.1.0"):
        stage(windows, tmp_path / "release", "v1.0.2", "v1.0.1", mac)
    stage(windows, tmp_path / "servicing", "v1.0.2", "v1.0.1")
    assert not list((tmp_path / "servicing").glob("*.dmg"))


@pytest.mark.parametrize(
    ("damage", "message"),
    [
        ("no image", "one Mac disk image"),
        ("wrong version", "one Mac disk image"),
        ("two images", "one Mac disk image"),
        ("image changed", "checksum file"),
        ("manifest version", "manifest"),
        ("bundle finding", "bundle check"),
        ("failed row", "scenarios did not pass"),
        ("missing scenario", "scenarios did not pass"),
        ("no sbom", "sbom.cdx.json"),
        ("bad sbom", "CycloneDX"),
        ("script changed", "FFmpeg build script"),
        ("no notices", "THIRD_PARTY_NOTICES.md"),
    ],
)
def test_mac_inputs_are_checked_before_any_output(tmp_path, no_receipts, damage, message):
    windows = windows_inputs(tmp_path / "windows")
    mac = mac_inputs(tmp_path / "mac", "1.1.0")
    image = mac / "Dusty-1.1.0-macos-arm64.dmg"
    rows = json.loads((mac / "results.json").read_text())
    if damage == "no image":
        image.unlink()
    elif damage == "wrong version":
        image.rename(mac / "Dusty-1.0.1-macos-arm64.dmg")
    elif damage == "two images":
        (mac / "extra.dmg").write_bytes(b"unreviewed")
    elif damage == "image changed":
        image.write_bytes(b"changed after the checks")
    elif damage == "manifest version":
        manifest = json.loads((mac / "dmg-manifest.json").read_text())
        (mac / "dmg-manifest.json").write_text(json.dumps({**manifest, "version": "1.0.1"}))
    elif damage == "bundle finding":
        (mac / "bundle-check.json").write_text(
            json.dumps({"findings": ["unsigned file"], "summary": {"macho_files": 33}})
        )
    elif damage == "failed row":
        rows[1]["result"] = "fail"
        (mac / "results.json").write_text(json.dumps(rows))
    elif damage == "missing scenario":
        (mac / "results.json").write_text(json.dumps(rows[:2]))
    elif damage == "no sbom":
        (mac / "sbom.cdx.json").unlink()
    elif damage == "bad sbom":
        (mac / "sbom.cdx.json").write_text('{"bomFormat":"SPDX"}')
    elif damage == "script changed":
        (mac / "build_ffmpeg-macos.sh").write_text("echo different")
    else:
        (mac / "THIRD_PARTY_NOTICES.md").unlink()
    with pytest.raises(ValueError, match=message):
        stage(windows, tmp_path / "release", "v1.1.0", "v1.0.1", mac)
    assert not (tmp_path / "release").exists()


def test_release_workflow_stages_windows_and_mac_with_notes():
    text = (ROOT / ".github/workflows/release.yml").read_text()
    assert "name: m5-installer-draft-unsigned" in text and "name: mac-dmg-draft-unsigned" in text
    assert "--mac-source build/release-input/mac" in text
    assert "--notes-file $notes" in text
    ci = (ROOT / ".github/workflows/ci.yml").read_text()
    assert "name: mac-dmg-draft-unsigned" in ci and "tools.macos_sbom" in ci
    # The draft's text is the current version's notes, naming its own files.
    notes = (ROOT / f"docs/release-notes/v{__version__}.md").read_text(encoding="utf-8")
    for name in (
        f"Dusty-{__version__}-Setup.exe",
        f"Dusty-{__version__}-macos-arm64.dmg",
        f"dusty-{__version__}-sbom.json",
        f"dusty-{__version__}-macos-arm64-sbom.json",
        "SHA256SUMS.txt",
    ):
        assert name in notes
    assert set(re.findall(r"[Dd]usty-([0-9.]+)-", notes)) == {__version__}


@pytest.mark.parametrize(
    "damage",
    ["same build", "no previous rows", "old row failed", "new version wrong", "no previous tag"],
)
def test_mac_upgrade_must_start_from_the_published_previous_release(tmp_path, no_receipts, damage):
    windows = windows_inputs(tmp_path / "windows")
    mac = mac_inputs(tmp_path / "mac", "1.2.0", "1.1.3")
    stage(windows, tmp_path / "accepted", "v1.2.0", "v1.1.3", mac)
    rows = json.loads((mac / "results.json").read_text())
    old = next(row for row in rows if row["step"] == "old app --version")
    new = next(row for row in rows if row["step"] == "new app --version")
    previous = "v1.1.3"
    if damage == "same build":
        old["observed"] = "exit 0, Dusty 1.2.0"
    elif damage == "no previous rows":
        rows = [row for row in rows if "app --version" not in row["step"]]
    elif damage == "old row failed":
        old["result"] = "fail"
    elif damage == "new version wrong":
        new["observed"] = "exit 0, Dusty 1.1.3"
    else:
        previous = ""
    (mac / "results.json").write_text(json.dumps(rows))
    with pytest.raises(
        ValueError, match="previous public release tag|published Dusty 1.1.3|did not pass"
    ):
        stage(windows, tmp_path / "release", "v1.2.0", previous, mac)
    assert not (tmp_path / "release").exists()


def test_the_first_mac_release_could_upgrade_only_from_itself(tmp_path, no_receipts):
    # 1.1.3 had no earlier Mac release, so its receipts need no previous Mac version.
    windows = windows_inputs(tmp_path / "windows")
    stage(windows, tmp_path / "release", "v1.1.3", "v1.0.1", mac_inputs(tmp_path / "mac", "1.1.3"))
    assert (tmp_path / "release/Dusty-1.1.3-macos-arm64.dmg").is_file()
