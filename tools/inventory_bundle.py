"""Inventory actual COLLECT files and embedded modules, not the dev environment.

This is a draft audit, not a redistribution approval. Unknown native subcomponents
remain findings. Build-time dependency metadata alone cannot clear a binary.
"""

import argparse
import hashlib
import importlib.metadata as metadata
import json
import shutil
import ssl
import sys
import tomllib
import uuid
from pathlib import Path

import pefile  # type: ignore[import-untyped]
from cyclonedx.schema import SchemaVersion
from cyclonedx.validation.json import JsonStrictValidator

from tools.check_licenses import PYINSTALLER_BOOTLOADER, normalized
from tools.stage_microsoft_runtime import is_crt

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def component(name: str, version: str, license_text: str, source: str, **extra) -> dict:
    return {"name": name, "version": version, "license": license_text, "source": source, **extra}


def copyright_from_pe(path: Path) -> str:
    with pefile.PE(str(path)) as executable:
        for group in getattr(executable, "FileInfo", []):
            for info in group:
                for table in getattr(info, "StringTable", []):
                    value = table.entries.get(b"LegalCopyright")
                    if value:
                        return value.decode("utf-8", "replace")
    return "See retained upstream copyright notices"


def clean_buildconf(text: str) -> str:
    """Retain the native banner/configuration, never the Wine bootstrap preamble."""
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("ffmpeg version ")), None)
    if start is None:
        raise ValueError("FFmpeg version banner missing")
    return "\n".join(lines[start:]).strip()


def generate(bundle: Path, analysis_path: Path, output: Path) -> dict:
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    pins = tomllib.loads((ROOT / "native/versions.toml").read_text(encoding="utf-8"))
    crt_records = json.loads((output / "crt-provenance.json").read_text(encoding="utf-8"))["files"]
    components = {
        "dusty": component(
            "dusty",
            metadata.version("dusty"),
            "Apache-2.0",
            "https://github.com/dusty-corporation/dusty",
        ),
        "cpython": component(
            "cpython", sys.version.split()[0], "PSF-2.0", "https://github.com/python/cpython"
        ),
        "pyinstaller-bootloader": component(
            "pyinstaller-bootloader",
            metadata.version("pyinstaller"),
            PYINSTALLER_BOOTLOADER,
            "https://github.com/pyinstaller/pyinstaller",
        ),
        "pyinstaller-runtime-hooks": component(
            "pyinstaller-runtime-hooks",
            metadata.version("pyinstaller"),
            "Apache-2.0",
            "https://github.com/pyinstaller/pyinstaller",
        ),
        "whisper.cpp": component(
            "whisper.cpp",
            pins["whisper_cpp"]["tag"],
            "MIT",
            "https://github.com/ggml-org/whisper.cpp",
            linkage="shared",
        ),
        "ffmpeg": component(
            "ffmpeg",
            pins["ffmpeg"]["tag"],
            "LGPL-2.1-or-later",
            "https://git.ffmpeg.org/ffmpeg.git",
            linkage="executable",
        ),
        "jfk-fixture": component(
            "jfk-fixture",
            "1961",
            "LicenseRef-Public-Domain",
            "https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/samples/jfk.wav",
            kind="data",
        ),
    }
    components["public-ca-certificates"] = component(
        "public-ca-certificates",
        "2026-10-24",
        "LicenseRef-Public-CA-Certificate",
        "resources/tls/sources.json",
        kind="data",
    )
    file_owners = {}
    components["winpthreads"] = component(
        "winpthreads",
        "11.0.1",
        "MIT AND BSD-3-Clause",
        "https://github.com/mingw-w64/mingw-w64/tree/c3e587c067a00a561899d49d3e63a659e38802ec",
        linkage="static",
    )
    components["mingw-w64-runtime"] = component(
        "mingw-w64-runtime",
        "11.0.1",
        "LicenseRef-MinGW-w64-runtime",
        "https://github.com/mingw-w64/mingw-w64/tree/c3e587c067a00a561899d49d3e63a659e38802ec",
        linkage="static",
    )
    dists = {}
    for dist in metadata.distributions():
        name = normalized(dist.metadata["Name"])
        dists[name] = dist
        for package_file in dist.files or ():
            file_owners[str(Path(str(dist.locate_file(package_file))).resolve()).lower()] = name

    def owner(source: str) -> str:
        path = Path(source)
        name = path.name.lower()
        if is_crt(name):
            key = "microsoft-visual-cpp-runtime"
            components[key] = component(
                key,
                ",".join(sorted({item["version"] for item in crt_records})),
                "LicenseRef-Microsoft-Visual-Cpp-Runtime",
                "https://aka.ms/vs/17/redistribution",
                linkage="shared",
            )
            return key
        if name == "opengl32sw.dll":
            key = "qt-software-opengl"
            components[key] = component(
                key,
                "unresolved",
                "UNKNOWN",
                "https://code.qt.io/cgit/qt/qtbase.git/",
                note="Mesa/LLVM transitive notices unresolved",
            )
            return key
        if name.startswith(("libcrypto-", "libssl-")):
            key = "openssl"
            components[key] = component(
                key,
                ssl.OPENSSL_VERSION.split()[1],
                "Apache-2.0",
                "https://github.com/openssl/openssl",
            )
            return key
        if name.startswith("libffi"):
            key = "libffi"
            components[key] = component(
                key, "ABI-8 (CPython build 20250902)", "MIT", "https://github.com/libffi/libffi"
            )
            return key
        dist_name = file_owners.get(str(path.resolve()).lower())
        if dist_name and dist_name != "dusty":
            dist = dists[dist_name]
            components[dist_name] = component(
                dist_name,
                dist.version,
                dist.metadata.get("License-Expression")
                or dist.metadata.get("License")
                or "UNKNOWN",
                dist.metadata.get("Home-page")
                or next(iter(dist.metadata.get_all("Project-URL") or []), "UNKNOWN"),
                linkage="shared" if dist_name.startswith(("pyside6", "shiboken6")) else "embedded",
            )
            return dist_name
        if path.is_relative_to(ROOT / "src") or path.is_relative_to(ROOT / "packaging"):
            return "dusty"
        if path.is_relative_to(Path(sys.base_prefix)):
            return "cpython"
        key = "unresolved-" + name
        components[key] = component(key, "unresolved", "UNKNOWN", "UNKNOWN")
        return key

    origins = {}
    for runtime, prefix in (("gui", "dusty"), ("fetch", "dusty-fetch")):
        for group in ("binaries", "datas"):
            for destination, source, _ in analysis[f"{runtime}_{group}"]:
                origins[f"{prefix}/_internal/{destination}".replace("\\", "/").lower()] = source
    embedded: list[dict] = []
    for group in ("gui_pure", "fetch_pure", "gui_scripts", "fetch_scripts"):
        for name, source, _ in analysis[group]:
            if name.startswith(("pyi_rth_", "_pyi_rth_utils")):
                key = "pyinstaller-runtime-hooks"
            else:
                key = owner(source)
            embedded.append(
                {
                    "module": name,
                    "component": key,
                    "executable": "dusty/dusty.exe"
                    if group.startswith("gui_")
                    else "dusty-fetch/dusty-fetch.exe",
                }
            )

    if any(name in components for name in ("lxml", "python-docx")):
        raise ValueError("Test-only XML/DOCX providers must never be bundled")

    # Preserve available original copyright/license texts; absent texts stay gaps.
    licenses = bundle / "licenses"
    licenses.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "packaging/licenses", licenses, dirs_exist_ok=True)
    for name in list(components):
        included_dist = dists.get("pyinstaller" if name == "pyinstaller-bootloader" else name)
        if included_dist:
            for package_file in included_dist.files or ():
                if any(
                    token in str(package_file).lower() for token in ("license", "copying", "notice")
                ):
                    source = Path(str(included_dist.locate_file(package_file)))
                    if source.is_file():
                        target = licenses / name / str(package_file).replace("..", "_")
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source, target)
    for source, name in (
        (Path(sys.base_prefix) / "LICENSE.txt", "cpython.txt"),
        (ROOT / "LICENSE", "dusty.txt"),
        (ROOT / "NOTICE", "dusty-NOTICE.txt"),
        (ROOT / "tests/fixtures/AUDIO_SOURCES.md", "audio-sources.md"),
    ):
        if source.is_file():
            shutil.copy2(source, licenses / name)

    files: list[dict] = []
    for path in sorted(bundle.rglob("*")):
        if not path.is_file() or path == bundle / "THIRD_PARTY_NOTICES.md":
            continue
        relative = path.relative_to(bundle).as_posix()
        if relative in {"dusty/dusty.exe", "dusty-fetch/dusty-fetch.exe"}:
            keys = {"dusty", "cpython", "pyinstaller-bootloader", "pyinstaller-runtime-hooks"}
            keys.update(item["component"] for item in embedded if item["executable"] == relative)
        elif relative.startswith("bin/"):
            keys = {"ffmpeg" if relative.startswith("bin/ffmpeg/") else "whisper.cpp"}
            if relative in {"bin/ffmpeg/ffmpeg.exe", "bin/ffmpeg/ffprobe.exe"}:
                keys.update({"mingw-w64-runtime", "winpthreads"})
        elif relative == "resources/selftest.wav":
            keys = {"jfk-fixture"}
        elif relative.startswith("resources/tls/") and relative.endswith(".pem"):
            keys = {"public-ca-certificates"}
        elif relative.startswith(("resources/", "licenses/")):
            keys = {"dusty"}  # Documentation/data, original third-party attribution is retained.
        elif path.name == "base_library.zip":
            keys = {"cpython"}
        else:
            source = origins.get(relative.lower())
            keys = {owner(source or str(path))}
        files.append(
            {
                "path": relative,
                "size": path.stat().st_size,
                "sha256": digest(path),
                "components": sorted(keys),
            }
        )
    lines = [
        "# Third-party notices",
        "",
        "Generated from actual COLLECT files and embedded module origins.",
        "Component/provider attribution covers actual files and embedded modules, including",
        "the native runtime files. Unknown providers fail the license gate.",
        "",
        "Qt/PySide6 shared DLLs remain replaceable under LGPL-3.0-only; FFmpeg is",
        "a separate LGPL-2.1-or-later executable. Original available license and copyright",
        "texts are retained in licenses/. Qt remains replaceable; corresponding source links",
        "and the exact FFmpeg revision/configuration follow below.",
        "Copyright statements are preserved in those original texts; where no text is",
        "available, attribution and transitive notices are unresolved, not waived.",
        "",
        "| Component | Version | License | Copyright | Source/evidence |",
        "|---|---|---|---|---|",
    ]
    copyright_text = {
        "dusty": "Copyright 2026 Dusty contributors",
        "cpython": copyright_from_pe(bundle / "dusty/_internal/python312.dll"),
        "pyside6-essentials": copyright_from_pe(bundle / "dusty/_internal/PySide6/Qt6Core.dll"),
        "shiboken6": copyright_from_pe(bundle / "dusty/_internal/shiboken6/shiboken6.abi3.dll"),
        "microsoft-visual-cpp-runtime": copyright_from_pe(
            bundle / "dusty/_internal/VCRUNTIME140.dll"
        ),
        "pyinstaller-bootloader": (
            "Copyright 2010-2023 PyInstaller Development Team; additional notices in COPYING.txt"
        ),
        "pyinstaller-runtime-hooks": (
            "Copyright PyInstaller Development Team; original notice in COPYING.txt"
        ),
        "whisper.cpp": (bundle / "bin/cpu/LICENSE.txt").read_text(encoding="utf-8").splitlines()[2],
        "ffmpeg": "Copyright 2000-2026 the FFmpeg developers; exact build banner retained below",
        "libffi": (licenses / "libffi-MIT.txt").read_text(encoding="utf-8").splitlines()[0],
        "jfk-fixture": "1961 US government work, President John F. Kennedy; public domain",
    }
    crypto = next((bundle / "dusty-fetch").rglob("libcrypto*.dll"), None)
    if crypto:
        copyright_text["openssl"] = copyright_from_pe(crypto)
    for item in sorted(components.values(), key=lambda item: item["name"]):
        item["copyright"] = copyright_text.get(item["name"], "See retained upstream notices")
        lines.append(
            f"| {item['name']} | {item['version']} | {item['license']} | "
            f"{item['copyright']} | {item['source']} |"
        )
    lines += [
        "",
        "## Statically linked FFmpeg toolchain runtime notices",
        "",
        (licenses / "mingw-w64-runtime.txt").read_text(encoding="utf-8"),
        "",
        (licenses / "winpthreads-COPYING.txt").read_text(encoding="utf-8"),
        "",
        "## Public CA trust-anchor data",
        "",
        "PM-approved public certificate data, not Dusty-owned software or a new library.",
        "Only four fingerprint-pinned PEM files may use this data attribution.",
        "Official CA references, fingerprints and acquisition provenance are retained",
        "in resources/tls/sources.json. No CA update service is invoked.",
        "No Apache-2.0 license is claimed for these public certificate records.",
        "",
        "## Native pins",
        "",
        f"whisper.cpp: {pins['whisper_cpp']}",
        "",
        f"FFmpeg: {pins['ffmpeg']}",
        "",
        "Exact configuration and build output:",
        "",
        "```text",
        clean_buildconf((bundle / "bin/ffmpeg/buildconf.txt").read_text(encoding="utf-8")),
        "```",
        "",
    ]
    lines += [
        "## Microsoft Visual C++ runtime terms",
        "",
        "Redistribution basis: maintainer-held VS 2022 Community individual license, section 4.a.i",
        "and the Visual C++ Runtime Files redistribution list. The runtime EULA is protective",
        "end-user terms under section 4.b, not an independent redistribution grant.",
        "Only release VC/redist CRT files are copied unmodified; see crt-provenance.json",
        "in the audit artifact. UCRT/API-set and other Microsoft files are excluded.",
        "The M5 installer must present these terms alongside Dusty's Apache-2.0 license",
        "and require agreement. Originals and document source hashes: licenses/microsoft/.",
        "",
        (licenses / "microsoft/runtime-eula.txt").read_text(encoding="utf-8"),
        "",
    ]
    output.mkdir(parents=True, exist_ok=True)
    notice = "\n".join(lines)
    notice_path = bundle / "THIRD_PARTY_NOTICES.md"
    notice_path.write_text(notice, encoding="utf-8", newline="\n")
    files.append(
        {
            "path": "THIRD_PARTY_NOTICES.md",
            "size": notice_path.stat().st_size,
            "sha256": digest(notice_path),
            "components": ["dusty"],
        }
    )
    (output / "THIRD_PARTY_NOTICES.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    inventory = {
        "schema": 1,
        "components": components,
        "files": files,
        "embedded_modules": embedded,
        "total_bytes": sum(item["size"] for item in files),
        "microsoft_runtime": crt_records,
        "attribution_scope": (
            "Actual file/provider and embedded-module inventory; source notices retained"
        ),
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    sbom: dict = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "serialNumber": "urn:uuid:" + str(uuid.uuid4()),
        "components": [],
        "dependencies": [],
    }
    for key, item in components.items():
        license_text = item["license"]
        license_entry = (
            {"license": {"name": license_text}}
            if license_text == "UNKNOWN"
            else {"expression": license_text}
        )
        sbom["components"].append(
            {
                "type": "data" if item.get("kind") == "data" else "library",
                "bom-ref": key,
                "name": item["name"],
                "version": item["version"],
                "licenses": [license_entry],
                "copyright": item["copyright"],
            }
        )
    for item in files:
        ref = "file:" + item["path"]
        sbom["components"].append(
            {
                "type": "file",
                "bom-ref": ref,
                "name": item["path"],
                "hashes": [{"alg": "SHA-256", "content": item["sha256"]}],
            }
        )
        sbom["dependencies"].append({"ref": ref, "dependsOn": item["components"]})
    (output / "sbom.cdx.json").write_text(json.dumps(sbom, indent=2), encoding="utf-8")
    error = JsonStrictValidator(SchemaVersion.V1_6).validate_str(json.dumps(sbom))
    if error:
        raise ValueError(f"CycloneDX 1.6 validation failed: {error}")
    largest = sorted(files, key=lambda item: item["size"], reverse=True)[:20]
    report = [
        "# Bundle measurements",
        "",
        f"Files: {len(files)}; bytes: {inventory['total_bytes']}",
        "",
        "| File | Bytes |",
        "|---|---:|",
    ]
    report.extend(f"| {item['path']} | {item['size']} |" for item in largest)
    (output / "measurements.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return inventory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--analysis", type=Path, default=ROOT / "build/packaging/analysis.json")
    parser.add_argument("--output", type=Path, default=ROOT / "build/packaging/audit")
    args = parser.parse_args()
    result = generate(args.bundle.resolve(), args.analysis, args.output)
    print(f"Inventoried {len(result['files'])} files; {result['total_bytes']} bytes")


if __name__ == "__main__":
    main()
