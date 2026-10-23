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
from importlib import import_module
from pathlib import Path

from cyclonedx.schema import SchemaVersion
from cyclonedx.validation.json import JsonStrictValidator

from tools.check_licenses import PYINSTALLER_BOOTLOADER, normalized

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def component(name: str, version: str, license_text: str, source: str, **extra) -> dict:
    return {"name": name, "version": version, "license": license_text, "source": source, **extra}


def generate(bundle: Path, analysis_path: Path, output: Path) -> dict:
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    pins = tomllib.loads((ROOT / "native/versions.toml").read_text(encoding="utf-8"))
    components = {
        "dusty": component(
            "dusty", metadata.version("dusty"), "MIT", "https://github.com/dusty-corporation/dusty"
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
    file_owners = {}
    dists = {}
    for dist in metadata.distributions():
        name = normalized(dist.metadata["Name"])
        dists[name] = dist
        for package_file in dist.files or ():
            file_owners[str(Path(str(dist.locate_file(package_file))).resolve()).lower()] = name

    def owner(source: str) -> str:
        path = Path(source)
        name = path.name.lower()
        if "isoschematron/resources" in path.as_posix().lower():
            key = "lxml-schematron-data"
            components[key] = component(
                key,
                "unresolved",
                "UNKNOWN",
                "https://github.com/lxml/lxml",
                note=(
                    "Wheel LICENSES.txt identifies unlicensed transforms "
                    "and separate ISO/skeleton terms"
                ),
            )
            return key
        if name.startswith(("vcruntime", "msvcp", "api-ms-win-")) or name == "ucrtbase.dll":
            key = "microsoft-runtime"
            components[key] = component(
                key,
                "unresolved",
                "LicenseRef-Microsoft-EULA",
                "https://learn.microsoft.com/cpp/windows/redistributing-visual-cpp-files",
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
                key, "unresolved", "UNKNOWN", "https://github.com/libffi/libffi"
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

    origins = {
        item[0].replace("\\", "/").lower(): item[1]
        for group in ("binaries", "datas")
        for item in analysis[group]
    }
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
                    "executable": "dusty.exe" if group.startswith("gui_") else "dusty-fetch.exe",
                }
            )

    # Record statically linked libraries disclosed by the actual lxml wheel.
    if "lxml" in components:
        etree = import_module("lxml.etree")

        for name, version in (
            ("libxml2", etree.LIBXML_COMPILED_VERSION),
            ("libxslt", etree.LIBXSLT_COMPILED_VERSION),
        ):
            components[name] = component(
                name,
                ".".join(map(str, version)),
                "MIT",
                "https://gitlab.gnome.org/GNOME/" + name,
                linkage="static",
            )
        components["lxml-iconv"] = component(
            "lxml-iconv",
            "unresolved",
            "LGPL-2.1-or-later",
            "https://www.gnu.org/software/libiconv/",
            linkage="static",
            note="Wheel LICENSES.txt discloses bundled iconv; static linkage not allowlisted",
        )
        components["lxml-zlib"] = component(
            "lxml-zlib", "unresolved", "Zlib", "https://zlib.net", linkage="static"
        )
    # Do not infer licenses of all native code inside CPython/Qt from their wrappers.
    components["embedded-native-review"] = component(
        "embedded-native-review",
        "unresolved",
        "UNKNOWN",
        "UNKNOWN",
        note=(
            "CPython extension, Qt third-party and FFmpeg static subcomponent notices "
            "still require source-level reconciliation"
        ),
    )

    # Preserve available original copyright/license texts; absent texts stay gaps.
    licenses = bundle / "licenses"
    licenses.mkdir(exist_ok=True)
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
        (ROOT / "tests/fixtures/AUDIO_SOURCES.md", "audio-sources.md"),
    ):
        if source.is_file():
            shutil.copy2(source, licenses / name)

    files: list[dict] = []
    for path in sorted(bundle.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(bundle).as_posix()
        if relative in {"dusty.exe", "dusty-fetch.exe"}:
            keys = {"dusty", "cpython", "pyinstaller-bootloader", "pyinstaller-runtime-hooks"}
            keys.update(item["component"] for item in embedded if item["executable"] == relative)
            keys.add("embedded-native-review")
        elif relative.startswith("bin/"):
            keys = {"ffmpeg" if relative.startswith("bin/ffmpeg/") else "whisper.cpp"}
        elif relative == "resources/selftest.wav":
            keys = {"jfk-fixture"}
        elif relative.startswith(("resources/", "licenses/")):
            keys = {"dusty"}  # Documentation/data, original third-party attribution is retained.
        elif path.name == "base_library.zip":
            keys = {"cpython"}
        else:
            source = origins.get(relative.removeprefix("_internal/").lower())
            keys = {owner(source or str(path))}
            if "lxml" in keys:
                keys.update({"libxml2", "libxslt", "lxml-iconv", "lxml-zlib"})
        files.append(
            {
                "path": relative,
                "size": path.stat().st_size,
                "sha256": digest(path),
                "components": sorted(keys),
            }
        )
    inventory = {
        "schema": 1,
        "components": components,
        "files": files,
        "embedded_modules": embedded,
        "total_bytes": sum(item["size"] for item in files),
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
    lines = [
        "# Third-party notices (draft)",
        "",
        "Generated from actual COLLECT files and embedded module origins.",
        "This audit bundle is not approved for redistribution. UNKNOWN and static LGPL",
        "findings need PM review; metadata is not a complete native license audit.",
        "",
        "Qt/PySide6 shared DLLs remain replaceable under LGPL-3.0-only; FFmpeg is",
        "a separate LGPL-2.1-or-later executable. Original available license and copyright",
        "texts are retained in licenses/. Missing source offers/notices remain release blockers.",
        "Copyright statements are preserved in those original texts; where no text is",
        "available, attribution and transitive notices are unresolved, not waived.",
        "",
        "| Component | Version | License | Source/evidence |",
        "|---|---|---|---|",
    ]
    for item in sorted(components.values(), key=lambda item: item["name"]):
        lines.append(
            f"| {item['name']} | {item['version']} | {item['license']} | {item['source']} |"
        )
    lines += [
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
        (bundle / "bin/ffmpeg/buildconf.txt").read_text(encoding="utf-8").strip(),
        "```",
        "",
    ]
    (output / "THIRD_PARTY_NOTICES.md").write_text("\n".join(lines), encoding="utf-8")
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
