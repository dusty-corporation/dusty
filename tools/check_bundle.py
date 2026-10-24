"""Fail closed on prohibited Qt DLLs, models and incorrect executable types."""

import argparse
import json
import struct
from pathlib import Path


def check(bundle: Path) -> list[str]:
    findings = []
    for path in bundle.rglob("*"):
        name = path.name.lower()
        if path.is_file() and (
            name == "qt6network.dll" or (name.startswith("qt6webengine") and name.endswith(".dll"))
        ):
            findings.append(f"Prohibited Qt DLL: {path.relative_to(bundle).as_posix()}")
        if path.is_file() and path.suffix.lower() == ".bin":
            findings.append("Model weights found in application bundle")
        if (
            path.is_relative_to(bundle / "dusty")
            and path.is_file()
            and (
                name
                in {
                    "_socket.pyd",
                    "_ssl.pyd",
                    "_overlapped.pyd",
                    "_multiprocessing.pyd",
                    "select.pyd",
                }
                or name.startswith(("libssl", "libcrypto", "qt6network", "qt6webengine"))
                or "lxml" in path.parts
                or "docx" in path.parts
            )
        ):
            findings.append(f"Prohibited offline dependency: {path.relative_to(bundle).as_posix()}")
        if path.is_file() and (
            name.startswith("api-ms-win-") or name in {"ucrtbase.dll", "opengl32sw.dll"}
        ):
            findings.append(
                f"Prohibited Windows/Mesa runtime: {path.relative_to(bundle).as_posix()}"
            )
    for name, subsystem in (("dusty/dusty.exe", 2), ("dusty-fetch/dusty-fetch.exe", 3)):
        path = bundle / name
        if not path.is_file():
            findings.append(f"Missing executable: {name}")
        else:
            data = path.read_bytes()
            pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
            if data[pe_offset : pe_offset + 4] != b"PE\x00\x00":
                findings.append(f"Invalid executable: {name}")
            elif struct.unpack_from("<H", data, pe_offset + 24 + 68)[0] != subsystem:
                findings.append(f"Incorrect windowed/console subsystem: {name}")
    for relative in (
        "bin/cpu/whisper-cli.exe",
        "bin/vulkan/whisper-cli.exe",
        "bin/vulkan/ggml-vulkan.dll",
        "bin/ffmpeg/ffmpeg.exe",
        "bin/ffmpeg/ffprobe.exe",
        "resources/models.json",
        "resources/selftest.wav",
        "resources/icons/dusty.ico",
    ):
        if not (bundle / relative).is_file():
            findings.append(f"Missing required bundle file: {relative}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--analysis", type=Path, default=Path("build/packaging/analysis.json"))
    args = parser.parse_args()
    findings = check(args.bundle)
    analysis = json.loads(args.analysis.read_text(encoding="utf-8"))
    scripts = [item[0] for item in analysis["gui_scripts"]]
    if scripts[0] != "runtime_guard":
        findings.append("Offline guard is not the first user/runtime script")
    if any("runtime_guard" == item[0] for item in analysis["fetch_scripts"]):
        findings.append("Downloader unexpectedly installs the offline guard")
    if any(
        item[0].startswith(("dusty.", "PySide6")) or item[0] == "dusty"
        for item in analysis["fetch_pure"]
    ):
        findings.append("Downloader unexpectedly embeds the offline GUI package")
    if any(
        item[0].split(".")[0]
        in {"dusty_fetch", "docx", "lxml", "socket", "ssl", "asyncio", "multiprocessing"}
        for item in analysis["gui_pure"]
    ):
        findings.append("Offline GUI unexpectedly embeds a prohibited package")
    if findings:
        print("\n".join(findings))
        return 1
    print("Bundle check passed: windowed GUI, console fetch, no prohibited Qt DLLs or models")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
