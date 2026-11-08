"""The drag-to-install disk image tool (tools/build_macos_dmg.py)."""

import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools import build_macos_dmg as dmg
from tools.build_macos_app import BUNDLE_ID, BuildError, project_version

darwin_only = pytest.mark.skipif(
    sys.platform != "darwin" or not Path(dmg.HDIUTIL).exists() or not Path(dmg.CODESIGN).exists(),
    reason="needs macOS hdiutil and codesign",
)


def fake_app(folder: Path, *, bundle_id=BUNDLE_ID, version=None, sign=False) -> Path:
    """A minimal Dusty.app: Info.plist, one executable, one resource and one link."""
    app = folder / "Dusty.app"
    (app / "Contents/MacOS").mkdir(parents=True)
    (app / "Contents/Resources").mkdir()
    info = {
        "CFBundleIdentifier": bundle_id,
        "CFBundleShortVersionString": version or project_version(),
        "CFBundleExecutable": "Dusty",
        "CFBundlePackageType": "APPL",
        "CFBundleName": "Dusty",
    }
    (app / "Contents/Info.plist").write_bytes(plistlib.dumps(info))
    executable = app / "Contents/MacOS/Dusty"
    if sign:
        shutil.copyfile("/usr/bin/true", executable)
    else:
        executable.write_bytes(b"#!/bin/sh\n")
    executable.chmod(0o755)
    (app / "Contents/Resources/models.json").write_text("{}", encoding="utf-8")
    (app / "Contents/Resources/alias.json").symlink_to("models.json")
    if sign:
        subprocess.run(
            [dmg.CODESIGN, "--force", "--sign", "-", str(app)],
            env=dmg.TOOL_ENV,
            capture_output=True,
            check=True,
        )
    return app


def test_image_name_follows_the_release_naming():
    assert dmg.image_name("1.2.3") == "Dusty-1.2.3-macos-arm64.dmg"


def test_source_must_be_a_real_dusty_app(tmp_path):
    other = tmp_path / "Other.app"
    other.mkdir()
    with pytest.raises(BuildError, match="Dusty.app folder"):
        dmg.check_app(other, "1.0.0")
    real = fake_app(tmp_path / "real")
    linked = tmp_path / "link" / "Dusty.app"
    linked.parent.mkdir()
    linked.symlink_to(real)
    with pytest.raises(BuildError, match="not a link"):
        dmg.check_app(linked, project_version())
    empty = tmp_path / "empty" / "Dusty.app"
    empty.mkdir(parents=True)
    with pytest.raises(BuildError, match="Info.plist"):
        dmg.check_app(empty, project_version())


def test_source_must_have_dustys_bundle_id_and_this_version(tmp_path):
    wrong_id = fake_app(tmp_path / "a", bundle_id="org.example.Other")
    with pytest.raises(BuildError, match="bundle id"):
        dmg.check_app(wrong_id, project_version())
    old = fake_app(tmp_path / "b", version="0.0.1")
    with pytest.raises(BuildError, match="different version"):
        dmg.check_app(old, project_version())


def test_tree_hashes_cover_files_and_links(tmp_path):
    app = fake_app(tmp_path)
    hashes = dmg.tree_hashes(app)
    assert hashes["Contents/Resources/alias.json"] == "link:models.json"
    assert len(hashes["Contents/Resources/models.json"]) == 64
    (app / "Contents/Resources/models.json").write_text("[]", encoding="utf-8")
    assert dmg.tree_hashes(app) != hashes


def mounted(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    mount = tmp_path / "mount"
    mount.mkdir()
    app = fake_app(mount)
    (mount / "Applications").symlink_to(dmg.APPLICATIONS)
    (mount / ".fseventsd").mkdir()  # hidden volume folders are ignored
    return mount, dmg.tree_hashes(app)


def test_mounted_image_must_hold_exactly_the_app_and_the_link(tmp_path):
    mount, expected = mounted(tmp_path)
    (mount / "README.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(BuildError, match="unexpected items"):
        dmg.check_mounted(mount, expected)


def test_applications_item_must_link_to_applications(tmp_path):
    mount, expected = mounted(tmp_path)
    (mount / "Applications").unlink()
    (mount / "Applications").symlink_to("/tmp")
    with pytest.raises(BuildError, match="link to /Applications"):
        dmg.check_mounted(mount, expected)


def test_mounted_app_must_match_the_source(tmp_path):
    mount, expected = mounted(tmp_path)
    (mount / "Dusty.app/Contents/Resources/models.json").write_text("[]", encoding="utf-8")
    with pytest.raises(BuildError, match="differs from the source"):
        dmg.check_mounted(mount, expected)


@pytest.mark.skipif(
    sys.platform != "darwin",
    reason="build_dmg stops on other hosts before it checks the output folder",
)
def test_refuses_an_existing_output_folder(tmp_path):
    app = fake_app(tmp_path / "src")
    (tmp_path / "out").mkdir()
    with pytest.raises(BuildError, match="existing output"):
        dmg.build_dmg(app, tmp_path / "out", root=tmp_path / "elsewhere")


@darwin_only
def test_unsigned_app_is_refused_before_any_image_is_made(tmp_path):
    app = fake_app(tmp_path / "src")
    with pytest.raises(BuildError, match="codesign failed"):
        dmg.build_dmg(app, tmp_path / "out", root=tmp_path / "elsewhere")
    assert not (tmp_path / "out").exists()


@darwin_only
def test_builds_and_verifies_a_drag_to_install_image(tmp_path):
    app = fake_app(tmp_path / "src", sign=True)
    manifest = dmg.build_dmg(app, tmp_path / "out", root=tmp_path / "elsewhere")
    image = tmp_path / "out" / dmg.image_name(project_version())
    assert manifest["image"] == image.name and image.is_file()
    assert manifest["items"] == ["Applications", "Dusty.app"]
    assert manifest["image_signed"] is False
    assert (tmp_path / "out" / (image.name + ".sha256")).read_text().split()[0] == (
        manifest["sha256"]
    )
    # The scratch folder and its mount point are gone; only the three outputs stay.
    assert sorted(os.listdir(tmp_path / "out")) == sorted(
        [image.name, image.name + ".sha256", "dmg-manifest.json"]
    )
    # Mount it again and install by copying, as a drag from Finder would.
    mount = tmp_path / "check"
    mount.mkdir()
    subprocess.run(
        [dmg.HDIUTIL, "attach", "-quiet", "-readonly", "-nobrowse", "-noautoopen"]
        + ["-mountpoint", str(mount), str(image)],
        env=dmg.TOOL_ENV,
        check=True,
        capture_output=True,
    )
    try:
        installed = tmp_path / "Applications"
        installed.mkdir()
        subprocess.run(
            [dmg.DITTO, str(mount / "Dusty.app"), str(installed / "Dusty.app")],
            env=dmg.TOOL_ENV,
            check=True,
            capture_output=True,
        )
    finally:
        subprocess.run(
            [dmg.HDIUTIL, "detach", "-quiet", "-force", str(mount)],
            env=dmg.TOOL_ENV,
            capture_output=True,
            check=False,
        )
    assert dmg.tree_hashes(installed / "Dusty.app") == dmg.tree_hashes(app)
    subprocess.run(
        [dmg.CODESIGN, "--verify", "--deep", "--strict", str(installed / "Dusty.app")],
        env=dmg.TOOL_ENV,
        check=True,
        capture_output=True,
    )
