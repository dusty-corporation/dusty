"""Package a built Dusty.app into a drag-to-install disk image (DMG) for macOS.

    python -m tools.build_macos_dmg build/mac-app/Dusty.app build/dmg

Takes a Dusty.app made by tools/build_macos_app.py and writes
Dusty-<version>-macos-arm64.dmg (the name ADR 0029 reserves) into a new output
folder. The image holds exactly two visible items: Dusty.app and a link to
/Applications, so a person installs Dusty by dragging one onto the other.

Before packaging, the app's signature must verify (codesign --deep --strict)
and its bundle id and version must match this checkout. The app is copied with
ditto, which keeps signatures and extended attributes. The image is compressed
read-only (ULMO, macOS 10.15 or later; Dusty needs 13.3) and checked after it
is made: hdiutil verify, then a read-only mount in the output folder that must
show the same two items, the same file hashes as the source app and a
signature that still verifies. A SHA-256 sum file and a small JSON manifest
sit beside the image.

With --identity the image itself is signed with that codesign identity (for a
Developer ID build). Ad hoc builds leave the image unsigned. Notarization and
stapling are Owner steps and are out of scope here. Nothing is downloaded and
no models are included; models live in the user data folder.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from tools.build_macos_app import BUNDLE_ID, BuildError, project_version, validate_output
from tools.check_macos_bundle import TOOL_ENV

ROOT = Path(__file__).resolve().parents[1]
HDIUTIL = "/usr/bin/hdiutil"
CODESIGN = "/usr/bin/codesign"
DITTO = "/usr/bin/ditto"
APPLICATIONS = "/Applications"
VOLUME_NAME = "Dusty"
IMAGE_FORMAT = "ULMO"
EXPECTED_ITEMS = frozenset({"Dusty.app", "Applications"})


def image_name(version: str) -> str:
    return f"Dusty-{version}-macos-arm64.dmg"


def run(args: list[str]) -> str:
    result = subprocess.run(args, env=TOOL_ENV, capture_output=True, text=True, check=False)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip().splitlines()[-3:]
        raise BuildError(f"{Path(args[0]).name} failed ({result.returncode}): {' | '.join(detail)}")
    return result.stdout + result.stderr


def check_app(app: Path, version: str) -> None:
    """The source must be a signed Dusty.app of this checkout's version."""
    if app.name != "Dusty.app" or app.is_symlink() or not app.is_dir():
        raise BuildError("The source must be a Dusty.app folder, not a link")
    info_path = app / "Contents/Info.plist"
    if not info_path.is_file():
        raise BuildError("Dusty.app has no Contents/Info.plist")
    info = plistlib.loads(info_path.read_bytes())
    if info.get("CFBundleIdentifier") != BUNDLE_ID:
        raise BuildError("Dusty.app has an unexpected bundle id")
    if info.get("CFBundleShortVersionString") != version:
        raise BuildError("Dusty.app was built from a different version than this checkout")
    run([CODESIGN, "--verify", "--deep", "--strict", str(app)])


def visible_items(folder: Path) -> set[str]:
    return {entry.name for entry in folder.iterdir() if not entry.name.startswith(".")}


def tree_hashes(app: Path) -> dict[str, str]:
    """Relative path to a SHA-256 of regular files, or to the target of links."""
    hashes = {}
    for current, folders, files in os.walk(app):
        for name in sorted(folders + files):
            path = Path(current, name)
            relative = path.relative_to(app).as_posix()
            if path.is_symlink():
                hashes[relative] = "link:" + os.readlink(path)
            elif path.is_file():
                with path.open("rb") as stream:
                    hashes[relative] = hashlib.file_digest(stream, "sha256").hexdigest()
    return hashes


def check_mounted(mount: Path, expected: dict[str, str]) -> None:
    items = visible_items(mount)
    if items != EXPECTED_ITEMS:
        raise BuildError(f"The image shows unexpected items: {sorted(items)}")
    link = mount / "Applications"
    if not link.is_symlink() or os.readlink(link) != APPLICATIONS:
        raise BuildError("The Applications item is not a link to /Applications")
    if tree_hashes(mount / "Dusty.app") != expected:
        raise BuildError("Dusty.app inside the image differs from the source app")
    run([CODESIGN, "--verify", "--deep", "--strict", str(mount / "Dusty.app")])


def stage(app: Path, folder: Path) -> None:
    run([DITTO, str(app), str(folder / "Dusty.app")])
    (folder / "Applications").symlink_to(APPLICATIONS)


def verify_image(image: Path, scratch: Path, expected: dict[str, str]) -> None:
    run([HDIUTIL, "verify", "-quiet", str(image)])
    mount = scratch / "mount"
    mount.mkdir()
    run(
        [
            HDIUTIL,
            "attach",
            "-quiet",
            "-readonly",
            "-nobrowse",
            "-noautoopen",
            "-mountpoint",
            str(mount),
            str(image),
        ]
    )
    try:
        check_mounted(mount, expected)
    finally:
        subprocess.run(
            [HDIUTIL, "detach", "-quiet", "-force", str(mount)],
            env=TOOL_ENV,
            capture_output=True,
            check=False,
        )


def build_dmg(app: Path, output: Path, *, identity: str = "-", root: Path = ROOT) -> dict:
    if sys.platform != "darwin":
        raise BuildError("Building the disk image needs macOS")
    started = time.monotonic()
    output = validate_output(output, root)
    app = app.absolute()
    version = project_version()
    check_app(app, version)
    expected = tree_hashes(app)
    output.mkdir()
    image = output / image_name(version)
    with tempfile.TemporaryDirectory(dir=output, prefix=".work-") as scratch_name:
        scratch = Path(scratch_name)
        source = scratch / "image"
        source.mkdir()
        stage(app, source)
        run(
            [
                HDIUTIL,
                "create",
                "-quiet",
                "-volname",
                VOLUME_NAME,
                "-srcfolder",
                str(source),
                "-fs",
                "HFS+",
                "-format",
                IMAGE_FORMAT,
                str(image),
            ]
        )
        if identity != "-":
            run([CODESIGN, "--force", "--sign", identity, "--timestamp", str(image)])
            run([CODESIGN, "--verify", "--strict", str(image)])
        verify_image(image, scratch, expected)
    with image.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    (output / (image.name + ".sha256")).write_text(f"{digest}  {image.name}\n", encoding="ascii")
    manifest = {
        "image": image.name,
        "version": version,
        "bundle_id": BUNDLE_ID,
        "format": IMAGE_FORMAT,
        "items": sorted(EXPECTED_ITEMS),
        "app_files": len(expected),
        "image_signed": identity != "-",
        "bytes": image.stat().st_size,
        "sha256": digest,
        "seconds": round(time.monotonic() - started, 1),
    }
    (output / "dmg-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("app", type=Path, help="Dusty.app made by tools/build_macos_app.py")
    parser.add_argument("output", type=Path, help="New folder to create (must not exist)")
    parser.add_argument(
        "--identity", default="-", help="codesign identity for the image (default: unsigned)"
    )
    args = parser.parse_args(argv)
    try:
        manifest = build_dmg(args.app, args.output, identity=args.identity)
    except BuildError as error:
        print(f"Disk image failed: {error}", file=sys.stderr)
        return 1
    print(
        f"Built {args.output / manifest['image']} in {manifest['seconds']} s, "
        f"{manifest['bytes']} bytes, contents and signature verified after mounting"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
