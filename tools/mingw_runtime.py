"""ADR 0026: exact existing FFmpeg runtime bytes, never a general license grant."""

import hashlib
from pathlib import Path

COMPONENT = "mingw-w64-runtime"
LICENSE = "LicenseRef-MinGW-w64-runtime"
BINARY_SHA256 = {
    "bin/ffmpeg/ffmpeg.exe": "c7632b3043595244e4d5b27099701b88eab86c6bebaea9547d471105824e2fa3",
    "bin/ffmpeg/ffprobe.exe": "8913237fd8e69fb568836249d31680822d19ff503f93c4cb163e6942c98e9a14",
}
NOTICE_SHA256 = "e9b2dc02451ea29092a1f25fa0f3c07207ed421f1807dffb0c4e6dce69dee7bd"
NOTICES = ("licenses/mingw-w64-runtime.txt", "bin/ffmpeg/mingw-w64-runtime.txt")


def approved(bundle: Path, inventory: dict) -> bool:
    """Check independent PM pins even if a changed inventory records new hashes."""
    try:
        component = inventory["components"][COMPONENT]
        if (
            component["name"] != COMPONENT
            or component["license"] != LICENSE
            or component["version"] != "11.0.1"
            or component.get("linkage") != "static"
        ):
            return False
        attributed = {
            item["path"] for item in inventory["files"] if COMPONENT in item["components"]
        }
        if attributed != set(BINARY_SHA256):
            return False
        for name, digest in {**BINARY_SHA256, **dict.fromkeys(NOTICES, NOTICE_SHA256)}.items():
            path = bundle / name
            if path.is_symlink():
                return False
            with path.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                    return False
            recorded = [item for item in inventory["files"] if item["path"] == name]
            if len(recorded) != 1 or recorded[0]["sha256"] != digest:
                return False
        notice = (bundle / NOTICES[0]).read_text(encoding="utf-8")
        return notice in (bundle / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError):
        return False
