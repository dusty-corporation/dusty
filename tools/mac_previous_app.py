"""Take Dusty.app out of a published release's Mac disk image, after checking it.

    python -m tools.mac_previous_app --release build/mac-previous --tag v1.1.3 \\
        --out build/mac-previous/Dusty.app

--release holds the files `gh release download` saved for that tag: the disk
image Dusty-<version>-macos-arm64.dmg and the release's SHA256SUMS.txt. The image
must match its line in SHA256SUMS.txt (which may have Windows line endings)
before it is opened. It is attached read-only and without Finder, Dusty.app is
copied out with ditto, and the image is detached again. The copied app must
report the release's version. This is the Dusty that the Mac upgrade scenario
installs first, so a release proves its upgrade from what users have.
"""

from __future__ import annotations

import argparse
import plistlib
import subprocess
import sys
import tempfile
from pathlib import Path

from tools.release_assets import verify_checksum
from tools.release_version import public_version, versions


def disk_image(release: Path, tag: str) -> Path:
    """The release's one Mac disk image, checked against its SHA256SUMS.txt."""
    if public_version(tag) is None:
        raise ValueError("Expected a public release tag such as v1.1.3")
    _, display, _ = versions(tag)
    name = f"Dusty-{display}-macos-arm64.dmg"
    images = [path for path in release.rglob("*.dmg") if not path.is_symlink()]
    if len(images) != 1 or images[0].name != name:
        raise ValueError(f"Expected exactly one disk image named {name}")
    sums = [path for path in release.rglob("SHA256SUMS.txt") if not path.is_symlink()]
    if len(sums) != 1:
        raise ValueError("Expected the release's SHA256SUMS.txt")
    verify_checksum(images[0], sums[0])
    return images[0]


def bundle_version(app: Path) -> str:
    with (app / "Contents/Info.plist").open("rb") as stream:
        return str(plistlib.load(stream).get("CFBundleShortVersionString", ""))


def extract(image: Path, out: Path, display: str) -> None:
    if out.exists():
        raise ValueError("The destination for the previous Dusty.app must be new")
    with tempfile.TemporaryDirectory(prefix="dusty-previous-") as mount:
        subprocess.run(
            [
                "hdiutil",
                "attach",
                "-readonly",
                "-nobrowse",
                "-noautoopen",
                "-mountpoint",
                mount,
                str(image),
            ],
            check=True,
            capture_output=True,
        )
        try:
            app = Path(mount) / "Dusty.app"
            if not app.is_dir() or app.is_symlink():
                raise ValueError("The disk image has no Dusty.app")
            out.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["ditto", str(app), str(out)], check=True)
        finally:
            subprocess.run(["hdiutil", "detach", mount], check=False, capture_output=True)
    if bundle_version(out) != display:
        raise ValueError(f"The previous Dusty.app does not report version {display}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--release", type=Path, required=True, help="Downloaded release files")
    parser.add_argument("--tag", required=True, help="The release's tag, such as v1.1.3")
    parser.add_argument("--out", type=Path, required=True, help="Where to put Dusty.app")
    args = parser.parse_args(argv)
    if sys.platform != "darwin":
        print("This needs macOS", file=sys.stderr)
        return 2
    image = disk_image(args.release, args.tag)
    _, display, _ = versions(args.tag)
    extract(image, args.out, display)
    print(f"Dusty {display} from {image.name}, checked against SHA256SUMS.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
