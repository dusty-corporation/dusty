"""The published Dusty that the Mac upgrade scenario installs first (tools/mac_previous_app.py)."""

import hashlib
import plistlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from dusty import __version__
from tools import mac_previous_app
from tools.release_policy import PUBLIC_REPOSITORY, source_tag

ROOT = Path(__file__).resolve().parents[2]


def release(folder: Path, image: bytes = b"published disk image", *, crlf: bool = True) -> Path:
    """A downloaded release as gh saves it: the image and SHA256SUMS.txt."""
    folder.mkdir(parents=True)
    (folder / "Dusty-1.1.3-macos-arm64.dmg").write_bytes(image)
    digest = hashlib.sha256(image).hexdigest()
    lines = [f"{'0' * 64}  Dusty-1.1.3-Setup.exe", f"{digest}  Dusty-1.1.3-macos-arm64.dmg"]
    ending = "\r\n" if crlf else "\n"
    (folder / "SHA256SUMS.txt").write_bytes((ending.join(lines) + ending).encode())
    return folder


@pytest.mark.parametrize("crlf", [True, False])
def test_disk_image_is_checked_against_the_release_checksums(tmp_path, crlf) -> None:
    folder = release(tmp_path / "release", crlf=crlf)
    image = mac_previous_app.disk_image(folder, "v1.1.3")
    assert image.name == "Dusty-1.1.3-macos-arm64.dmg"


@pytest.mark.parametrize(
    ("damage", "message"),
    [
        ("changed image", "checksum"),
        ("no sums", "SHA256SUMS"),
        ("other version", "exactly one disk image"),
        ("two images", "exactly one disk image"),
        ("draft tag", "public release tag"),
    ],
)
def test_disk_image_refuses_anything_unchecked(tmp_path, damage, message) -> None:
    folder = release(tmp_path / "release")
    tag = "v1.1.3"
    if damage == "changed image":
        (folder / "Dusty-1.1.3-macos-arm64.dmg").write_bytes(b"changed after publication")
    elif damage == "no sums":
        (folder / "SHA256SUMS.txt").unlink()
    elif damage == "other version":
        tag = "v1.1.2"
    elif damage == "two images":
        (folder / "extra.dmg").write_bytes(b"unreviewed")
    else:
        tag = "engine-v3"
    with pytest.raises(ValueError, match=message):
        mac_previous_app.disk_image(folder, tag)


@pytest.mark.skipif(sys.platform != "darwin", reason="hdiutil and ditto exist only on macOS")
def test_extract_copies_the_app_out_of_a_real_disk_image(tmp_path) -> None:
    content = tmp_path / "content"
    app = content / "Dusty.app/Contents"
    (app / "MacOS").mkdir(parents=True)
    (app / "MacOS/Dusty").write_text("#!/bin/sh\necho Dusty 1.1.3\n")
    with (app / "Info.plist").open("wb") as stream:
        plistlib.dump({"CFBundleShortVersionString": "1.1.3"}, stream)
    image = tmp_path / "Dusty-1.1.3-macos-arm64.dmg"
    subprocess.run(
        ["hdiutil", "create", "-quiet", "-srcfolder", str(content), "-format", "UDZO", str(image)],
        check=True,
    )
    out = tmp_path / "previous/Dusty.app"
    mac_previous_app.extract(image, out, "1.1.3")
    assert mac_previous_app.bundle_version(out) == "1.1.3"
    assert (out / "Contents/MacOS/Dusty").read_text().endswith("Dusty 1.1.3\n")
    attached = subprocess.run(["hdiutil", "info"], capture_output=True, text=True).stdout
    assert str(image) not in attached
    with pytest.raises(ValueError, match="must be new"):
        mac_previous_app.extract(image, out, "1.1.3")
    shutil.rmtree(out)
    with pytest.raises(ValueError, match="version 1.1.2"):
        mac_previous_app.extract(image, out, "1.1.2")


def test_source_tag_is_this_checkout_version() -> None:
    assert source_tag() == f"v{__version__}"


def test_ci_upgrades_both_platforms_from_the_published_release() -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    jobs = dict(re.findall(r"^  ([\w-]+):\n(.*?)(?=^  [\w-]+:|\Z)", ci, re.M | re.S))
    mac, windows = jobs["macos"], jobs["packaging-spike"]
    for job in (mac, windows):
        assert "tools.release_policy source" in job
        assert f"'{PUBLIC_REPOSITORY}'" in job or f"repo={PUBLIC_REPOSITORY}" in job
        assert "inputs.previous_tag" in job
    assert "tools.mac_previous_app --release build/mac-previous/release" in mac
    assert "--old build/mac-previous/Dusty.app --new build/mac-app/Dusty.app" in mac
    assert mac.index("tools.mac_previous_app") < mac.index("tools.mac_upgrade_check")
    assert "-PreviousInstaller" in windows
