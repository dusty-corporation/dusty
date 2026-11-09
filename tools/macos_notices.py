"""Generate THIRD_PARTY_NOTICES.md for Dusty.app from the files actually shipped.

Called by tools/build_macos_app.py after every program and resource is in place
and before signing. Every regular file in the bundle is attributed to a
component by its location; the embedded Python modules of the two PyInstaller
executables are attributed by their analysed origin (audit/analysis.json). An
unattributed file or module stops the build (fail closed, as on Windows).

Inputs are real build inputs, never a hand-written list:
- CPython: the build interpreter's LICENSE.txt and BUILD stamp, and the
  third-party libraries python-build-standalone links statically into
  libpython3.12.dylib, detected by markers in the shipped copy and versioned
  from the build interpreter where it exposes a version (OpenSSL, SQLite,
  mpdecimal, Expat) or from a version string in the binary (bzip2).
- Qt and PySide6: the frameworks, platform plugins and translations present,
  with Qt's version from each framework's Info.plist and package metadata.
- whisper.cpp, ggml and FFmpeg: native/versions.toml, the bundled LICENSE, the
  bundled ffmpeg's own -version banner and -buildconf configure line, and the
  pinned corresponding-source archive in packaging/licenses/ffmpeg-source.json.
- Downloaded model data: resources/models.json and native/versions.toml.

The Windows notices (tools/inventory_bundle.py, tools/installer_notices.py) are
not touched; the Qt/FFmpeg replaceability sentence is reused word for word.
"""

from __future__ import annotations

import hashlib
import importlib.metadata as metadata
import json
import plistlib
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTICES = "THIRD_PARTY_NOTICES.md"
INVENTORY = "notices-inventory.json"
SECTION_FILES = "## Shipped native files"
SECTION_QT = "## Qt modules shipped"
# Reused from the Windows notice (tools/inventory_bundle.py) word for word.
WINDOWS_SOURCE_SENTENCE = (
    "Qt remains replaceable; corresponding source links\n"
    "and the exact FFmpeg revision/configuration follow below."
)
MACHO_MAGICS = (b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf")
TOOL_ENV = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "C", "LC_ALL": "C"}


class NoticesError(RuntimeError):
    """A shipped file or module has no known component; the build must stop."""


@dataclass
class Component:
    key: str
    name: str
    version: str
    license: str
    copyright: str
    source: str
    texts: list[str] = field(default_factory=list)  # under Resources/licenses
    linkage: str = ""
    note: str = ""


@dataclass(frozen=True)
class StaticLibrary:
    """A library python-build-standalone links into libpython3.12.dylib."""

    name: str
    markers: tuple[bytes, ...]
    license: str
    text: str | None  # file under Resources/licenses, None while not retained


MAC_TEXTS = ROOT / "packaging/macos/licenses"  # pinned upstream texts, see sources.json
LIBPYTHON_TEXTS = "macos/libpython/"
STATIC_LIBRARIES = (
    StaticLibrary("OpenSSL", (b"OpenSSL ",), "Apache-2.0", "openssl-Apache-2.0.txt"),
    StaticLibrary(
        "libffi",
        (b"ffi_prep_cif", b"ffi_call"),
        "MIT",
        LIBPYTHON_TEXTS + "libffi-3.4.6-LICENSE.txt",
    ),
    StaticLibrary("SQLite", (b"SQLite format 3",), "blessing (public domain)", None),
    StaticLibrary(
        "bzip2", (b"BZ2_bzCompress",), "bzip2-1.0.6", LIBPYTHON_TEXTS + "bzip2-1.0.8-LICENSE.txt"
    ),
    StaticLibrary(
        "XZ Utils liblzma",
        (b"\xfd7zXZ", b"lzma_code"),
        "LicenseRef-Public-Domain",
        LIBPYTHON_TEXTS + "xz-5.2.12-COPYING.txt",
    ),
    StaticLibrary(
        "mpdecimal",
        (b"libmpdec",),
        "BSD-2-Clause",
        LIBPYTHON_TEXTS + "mpdecimal-4.0.0-COPYRIGHT.txt",
    ),
    StaticLibrary(
        "Expat", (b"XML_ParserCreate",), "MIT", LIBPYTHON_TEXTS + "expat-2.6.3-COPYING.txt"
    ),
    StaticLibrary(
        "HACL* (vendored in CPython)", (b"Hacl_",), "MIT", LIBPYTHON_TEXTS + "hacl-star-MIT.txt"
    ),
)
# Versions python-build-standalone 20250902 pins (pythonbuild/downloads.py) for
# libraries whose version no API exposes; a version string in the binary, when
# present, must agree.
PBS_PINS = {"libffi": ("3.4.6", None), "XZ Utils liblzma": ("5.2.12", b"\x005.2.12\x00")}
QT_ATTRIBUTIONS = "macos/qt/qt-6.9.2-attributions.json"
MODEL_TEXTS = {
    "whisper": "macos/models/openai-whisper-LICENSE.txt",
    "silero": "macos/models/silero-vad-LICENSE.txt",
}
# A license text is not required for these terms.
NO_TEXT_NEEDED = {"SQLite"}
QT_THIRD_PARTY_MARKERS = {  # name: (binary, marker)
    "PCRE2": ("QtCore", b"PCRE2"),
    "SHA-3 / Keccak": ("QtCore", b"Keccak"),
    "BLAKE2": ("QtCore", b"Blake2"),
    "Easing equations": ("QtCore", b"Easing"),
    "HarfBuzz": ("QtGui", b"harfbuzz"),
    "FreeType": ("QtGui", b"FreeType"),
    "libpng": ("QtGui", b"libpng version"),
    "D-Bus interface code (libdbus is not bundled)": ("QtDBus", b"libdbus"),
}


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def is_macho(path: Path) -> bool:
    with path.open("rb") as stream:
        return stream.read(4) in MACHO_MAGICS


def regular_files(app: Path) -> list[Path]:
    return sorted(
        path
        for path in app.rglob("*")
        if path.is_file() and not path.is_symlink() and "_CodeSignature" not in path.parts
    )


def cpython_copyright(license_text: str) -> str:
    match = re.search(r"Copyright \(c\) 2001.*?Reserved", license_text, re.DOTALL)
    return " ".join(match.group(0).split()) if match else "See retained upstream notices"


def first_copyright(text: str) -> str:
    return next(
        (line.strip() for line in text.splitlines() if "Copyright" in line),
        "See retained upstream notices",
    )


def static_libraries(libpython: bytes) -> list[dict]:
    """Detected libraries inside the shipped libpython, with verified versions."""
    import decimal
    import pyexpat
    import sqlite3
    import ssl

    exposed = {
        "OpenSSL": ssl.OPENSSL_VERSION.split()[1],
        "SQLite": sqlite3.sqlite_version,
        "mpdecimal": decimal.__libmpdec_version__,  # type: ignore[attr-defined]
        "Expat": pyexpat.EXPAT_VERSION.removeprefix("expat_"),
    }
    bzip2 = re.search(rb"(\d+\.\d+\.\d+), \d{1,2}-[A-Z][a-z]{2}-\d{4}", libpython)
    if bzip2:
        exposed["bzip2"] = bzip2.group(1).decode()
    proofs = {
        "OpenSSL": f"OpenSSL {exposed['OpenSSL']} ".encode(),
        "SQLite": exposed["SQLite"].encode(),
        "Expat": f"expat_{exposed['Expat']}".encode(),
    }
    found = []
    for library in STATIC_LIBRARIES:
        if not all(marker in libpython for marker in library.markers):
            continue
        default = "not exposed by the build"
        if library.name.startswith("HACL*"):
            default = f"as vendored in CPython {sys.version.split()[0]}"
        version = exposed.get(library.name, default)
        if library.name in PBS_PINS:
            pinned, marker = PBS_PINS[library.name]
            if marker is not None and marker not in libpython:
                raise NoticesError(f"{library.name} {pinned} is not the copy inside libpython")
            version = pinned + (
                " (version string in the binary)"
                if marker
                else " (python-build-standalone pin; not exposed in the binary)"
            )
        proof = proofs.get(library.name)
        if proof is not None and proof not in libpython:
            raise NoticesError(f"{library.name} {version} is not the copy inside libpython")
        text = library.text
        number = version.split()[0]
        if text and text.startswith(LIBPYTHON_TEXTS) and number[0].isdigit():
            if f"-{number}-" not in text:
                raise NoticesError(f"Retained {library.name} text is for another version")
        found.append(
            {
                "name": library.name,
                "version": version,
                "license": library.license,
                "text": text,
            }
        )
    return found


def qt_inventory(app: Path) -> dict:
    lib = app / "Contents/Frameworks/PySide6/Qt/lib"
    modules = []
    for framework in sorted(lib.glob("Qt*.framework")):
        info = framework / "Versions/A/Resources/Info.plist"
        version = plistlib.loads(info.read_bytes()).get("CFBundleVersion", "unknown")
        modules.append({"module": framework.stem, "version": version})
    plugins = sorted(
        str(path.relative_to(app / "Contents/Frameworks/PySide6/Qt/plugins"))
        for path in (app / "Contents/Frameworks/PySide6/Qt/plugins").rglob("*.dylib")
        if not path.is_symlink()
    )
    translations = sorted(
        path.name for path in (app / "Contents/Resources/PySide6/Qt/translations").glob("*.qm")
    )
    detected = []
    for name, (binary, marker) in QT_THIRD_PARTY_MARKERS.items():
        image = lib / f"{binary}.framework/Versions/A/{binary}"
        if image.is_file() and marker in image.read_bytes():
            detected.append(name)
    return {
        "modules": modules,
        "plugins": plugins,
        "translations": len(translations),
        "third_party_detected": detected,
    }


def module_owner(source: str, root: Path = ROOT) -> str:
    path = Path(source)
    text = path.as_posix()
    if path.is_relative_to(root / "src") or path.is_relative_to(root / "packaging"):
        return "dusty"
    if "/site-packages/PySide6/" in text:
        return "pyside6"
    if "/site-packages/shiboken6/" in text:
        return "shiboken6"
    if "/site-packages/PyInstaller/" in text:
        return "pyinstaller-bootloader"
    if path.is_relative_to(Path(sys.base_prefix)):
        return "cpython"
    raise NoticesError(f"Embedded module from an unknown provider: {path.name}")


def embedded_owners(analysis: dict, group: str) -> set[str]:
    owners = {"pyinstaller-bootloader"}
    for name, source, _ in analysis[f"{group}_pure"] + analysis[f"{group}_scripts"]:
        if name.startswith(("pyi_rth_", "_pyi_rth_utils", "pyiboot", "pyimod")):
            owners.add("pyinstaller-bootloader")
        else:
            owners.add(module_owner(source))
    return owners


def attribute(relative: str, bin_dir: str, analysis: dict) -> list[str]:
    """Component keys for one bundle-relative file; raises when unknown."""
    if relative == "Contents/MacOS/Dusty":
        return sorted(embedded_owners(analysis, "gui"))
    if relative == "Contents/Helpers/dusty-fetch/dusty-fetch":
        return sorted(embedded_owners(analysis, "fetch"))
    name = relative.rsplit("/", 1)[-1]
    if name == "libpython3.12.dylib":
        return ["cpython", "cpython-static-libraries"]
    if name == "base_library.zip":
        return ["cpython"]
    if relative.startswith(bin_dir + "/"):
        inner = relative.removeprefix(bin_dir + "/")
        folder = inner.split("/")[0]
        if inner in ("ffmpeg/ffmpeg", "ffmpeg/ffprobe"):
            return ["ffmpeg"]
        if inner == "lifeline/dusty-lifeline":
            return ["dusty"]
        if folder in ("cpu", "metal") and inner.count("/") == 1:
            if name.startswith("libggml") and name.endswith(".dylib"):
                return ["ggml"]
            if name == "whisper-cli" or (
                name.startswith("libwhisper.") and name.endswith(".dylib")
            ):
                return ["whisper.cpp"]
    if relative.startswith(
        ("Contents/Frameworks/PySide6/Qt/", "Contents/Resources/PySide6/Qt/translations/")
    ):
        return ["qt"]
    if relative.startswith("Contents/Frameworks/PySide6/"):
        return ["pyside6"]
    if relative.startswith("Contents/Frameworks/shiboken6/"):
        return ["shiboken6"]
    if relative == "Contents/Resources/selftest.wav":
        return ["jfk-fixture"]
    if relative.startswith("Contents/Resources/tls/") and relative.endswith(".pem"):
        return ["public-ca-certificates"]
    if relative in ("Contents/Info.plist", "Contents/PkgInfo") or relative.startswith(
        (
            "Contents/Resources/licenses/",
            "Contents/Resources/icons/",
            "Contents/Resources/tls/",
            "Contents/Resources/" + NOTICES,
            "Contents/Resources/models.json",
            "Contents/Resources/Dusty.icns",
        )
    ):
        return ["dusty"]
    raise NoticesError(f"Bundle file has no known component: {relative}")


def ggml_versions(app: Path) -> list[str]:
    """current_version of each shipped libggml image, as otool -L reports its own id."""
    versions = set()
    for path in sorted((app / "Contents/Helpers/bin").rglob("libggml*.dylib")):
        try:
            result = subprocess.run(
                ["/usr/bin/otool", "-L", str(path)],
                env=TOOL_ENV,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            continue
        lines = result.stdout.splitlines()
        match = re.search(r"current version (\d+\.\d+\.\d+)", lines[1]) if len(lines) > 1 else None
        if match:
            versions.add(match.group(1))
    return sorted(versions)


def components(
    app: Path, version: str, banner: str, qt: dict, statics: list[dict]
) -> dict[str, Component]:
    pins = tomllib.loads((ROOT / "native/versions.toml").read_text(encoding="utf-8"))
    licenses = app / "Contents/Resources/licenses"
    cpython_license = (licenses / "cpython-LICENSE.txt").read_text(encoding="utf-8")
    whisper_license = (licenses / "whisper.cpp-LICENSE.txt").read_text(encoding="utf-8")
    build_stamp = (Path(sys.base_prefix) / "BUILD").read_text(encoding="utf-8").strip()
    qt_version = qt["modules"][0]["version"] if qt["modules"] else "unknown"
    ggml = ggml_versions(app)
    items = [
        Component(
            "dusty",
            "Dusty",
            version,
            "Apache-2.0",
            first_copyright((ROOT / "NOTICE").read_text(encoding="utf-8")),
            "https://github.com/dusty-corporation/dusty",
            ["dusty-LICENSE.txt", "dusty-NOTICE.txt"],
        ),
        Component(
            "cpython",
            "CPython",
            f"{sys.version.split()[0]} (python-build-standalone {build_stamp})",
            "PSF-2.0",
            cpython_copyright(cpython_license),
            "https://github.com/python/cpython",
            ["cpython-LICENSE.txt", LIBPYTHON_TEXTS + "cpython-3.12.11-license.rst.txt"],
            "shared",
        ),
        Component(
            "cpython-static-libraries",
            "Libraries inside libpython3.12.dylib",
            "see the CPython section",
            "; ".join(sorted({item["license"] for item in statics})),
            "See the CPython section",
            "https://github.com/astral-sh/python-build-standalone",
            sorted({item["text"] for item in statics if item["text"]}),
            "static in libpython",
        ),
        Component(
            "pyinstaller-bootloader",
            "PyInstaller bootloader and runtime modules",
            metadata.version("pyinstaller"),
            "GPL-2.0-or-later WITH PyInstaller-bootloader-exception; runtime hooks Apache-2.0",
            "Copyright (c) 2010-2023, PyInstaller Development Team",
            "https://github.com/pyinstaller/pyinstaller",
            ["pyinstaller-COPYING.txt"],
        ),
        Component(
            "qt",
            "Qt (" + ", ".join(item["module"] for item in qt["modules"]) + ")",
            qt_version,
            "LGPL-3.0-only",
            "Copyright (C) The Qt Company Ltd. and other contributors.",
            f"https://code.qt.io/cgit/qt/qtbase.git/tag/?h=v{qt_version}",
            ["qt-LGPL-3.0.txt", "qt-GPL-3.0-reference.txt"],
            "shared (replaceable frameworks)",
        ),
        Component(
            "pyside6",
            "PySide6 (pyside6-essentials)",
            metadata.version("pyside6-essentials"),
            "LGPL-3.0-only",
            "Copyright (C) The Qt Company Ltd. and other contributors.",
            "https://code.qt.io/cgit/pyside/pyside-setup.git/",
            ["qt-LGPL-3.0.txt"],
            "shared",
        ),
        Component(
            "shiboken6",
            "shiboken6",
            metadata.version("shiboken6"),
            "LGPL-3.0-only",
            "Copyright (C) The Qt Company Ltd. and other contributors.",
            "https://code.qt.io/cgit/pyside/pyside-setup.git/",
            ["qt-LGPL-3.0.txt"],
            "shared",
        ),
        Component(
            "whisper.cpp",
            "whisper.cpp",
            f"{pins['whisper_cpp']['tag']} ({pins['whisper_cpp']['commit']})",
            "MIT",
            first_copyright(whisper_license),
            "https://github.com/ggml-org/whisper.cpp",
            ["whisper.cpp-LICENSE.txt"],
            "executable and shared libraries",
            f"approved patch sha256 {pins['whisper_cpp_macos']['patch_sha256']}",
        ),
        Component(
            "ggml",
            "ggml (built from the whisper.cpp tree)",
            ", ".join(ggml) or "unknown",
            "MIT",
            first_copyright(whisper_license),
            f"https://github.com/ggml-org/whisper.cpp/tree/{pins['whisper_cpp']['commit']}/ggml",
            ["whisper.cpp-LICENSE.txt"],
            "shared libraries",
        ),
        Component(
            "ffmpeg",
            "FFmpeg (ffmpeg and ffprobe)",
            f"{pins['ffmpeg']['tag']} ({pins['ffmpeg']['commit']})",
            "LGPL-2.1-or-later",
            re.sub(r"^.*?(Copyright)", r"\1", banner),
            "https://git.ffmpeg.org/ffmpeg.git",
            ["ffmpeg-LGPL-2.1.txt"],
            "executable",
        ),
        Component(
            "jfk-fixture",
            "JFK self-test recording",
            "1961",
            "LicenseRef-Public-Domain",
            "1961 US government work, President John F. Kennedy; public domain",
            "https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/samples/jfk.wav",
            [],
            "data",
        ),
        Component(
            "public-ca-certificates",
            "Public CA certificates (dusty-fetch only)",
            "2026-10-24",
            "LicenseRef-Public-CA-Certificate",
            "See retained upstream notices",
            "resources/tls/sources.json",
            ["public-ca-NOTICE.txt", "public-ca-sources.json"],
            "data",
        ),
    ]
    return {item.key: item for item in items}


def stage_texts(app: Path, texts: Path = MAC_TEXTS) -> dict:
    """Copy the pinned Mac license texts into Resources/licenses/macos after checking
    every file against sources.json; an unlisted or changed file stops the build."""
    sources = json.loads((texts / "sources.json").read_text(encoding="utf-8"))
    present = {
        path.relative_to(texts).as_posix()
        for path in texts.rglob("*")
        if path.is_file() and path.name != "sources.json"
    }
    if present != set(sources):
        raise NoticesError("packaging/macos/licenses differs from its sources.json")
    target = app / "Contents/Resources/licenses/macos"
    for relative, record in sorted(sources.items()):
        data = (texts / relative).read_bytes()
        if hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise NoticesError(f"Retained license text changed: {relative}")
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    return sources


def qt_attributions(app: Path, qt: dict) -> dict | None:
    path = app / "Contents/Resources/licenses" / QT_ATTRIBUTIONS
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    shipped = {module["version"] for module in qt["modules"]}
    if shipped and shipped != {data["qt"]}:
        raise NoticesError("Retained Qt attributions are for another Qt version")
    return data


def qt_attribution_lines(data: dict | None) -> list[str]:
    if data is None:
        return []
    lines = [
        "Third-party code in the shipped Qt modules, from every qt_attribution.json in",
        f"qtbase {data['qt']} for {', '.join(data['shipped_modules'])} (license texts retained):",
        "",
        "| Component | Version | License | Copyright | License texts |",
        "|---|---|---|---|---|",
    ]
    for entry in data["included"]:
        raw = entry.get("Copyright") or "see license text"
        holder = "; ".join(raw) if isinstance(raw, list) else str(raw)
        holder = " ".join(holder.replace("|", "/").split())
        if len(holder) > 160:
            holder = holder[:157] + "..."
        texts = ", ".join(f"licenses/macos/{name}" for name in entry["texts"])
        lines.append(
            f"| {entry['Name']} | {entry.get('Version') or 'qtbase ' + data['qt']} | "
            f"{entry['LicenseId']} | {holder} | {texts} |"
        )
    lines += [
        "",
        "Not in this bundle: "
        + "; ".join(f"{item['Id']} ({item['reason']})" for item in data["excluded"])
        + ".",
        "",
    ]
    return lines


def model_rows() -> list[str]:
    pins = tomllib.loads((ROOT / "native/versions.toml").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "resources/models.json").read_text(encoding="utf-8"))
    rows = []
    for item in manifest["models"]:
        rows.append(
            f"| {item['file_name']} | OpenAI Whisper weights ({item['id']}), converted with "
            f"whisper.cpp {item['source']['whisper_cpp_commit'][:8]} | MIT | "
            f"openai/whisper {pins['openai_whisper']['commit'][:8]} | "
            f"licenses/{MODEL_TEXTS['whisper']} |"
        )
    for item in manifest["vad"]:
        rows.append(
            f"| {item['file_name']} | Silero VAD {item['source']['silero_vad_version']}, converted "
            f"with whisper.cpp {item['source']['whisper_cpp_commit'][:8]} | MIT | "
            f"snakers4/silero-vad {pins['silero_vad']['commit'][:8]} | "
            f"licenses/{MODEL_TEXTS['silero']} |"
        )
    return rows


def render(
    app: Path,
    items: dict[str, Component],
    files: dict[str, list[str]],
    statics: list[dict],
    qt: dict,
    banner: str,
    buildconf: str,
) -> tuple[str, list[str]]:
    pins = tomllib.loads((ROOT / "native/versions.toml").read_text(encoding="utf-8"))
    source = json.loads(
        (ROOT / "packaging/licenses/ffmpeg-source.json").read_text(encoding="utf-8")
    )
    recipe = ROOT / "native/macos/build_ffmpeg.sh"
    gaps = [
        f"{item['name']} {item['version']} inside libpython3.12.dylib: license text not retained"
        for item in statics
        if item["text"] is None and item["name"] not in NO_TEXT_NEEDED
    ]
    licenses = app / "Contents/Resources/licenses"
    attributions = qt_attributions(app, qt)
    if attributions is None:
        gaps.append(
            "Qt third-party code detected in the shipped Qt binaries ("
            + ", ".join(qt["third_party_detected"])
            + "): qtbase qt_attribution notices are not retained"
        )
    if not all((licenses / name).is_file() for name in MODEL_TEXTS.values()):
        gaps.append("Downloaded model data (Whisper weights, Silero VAD): MIT texts not retained")
    lines = [
        "# Third-party notices (macOS arm64)",
        "",
        "Generated by tools/macos_notices.py from the files actually shipped in this",
        "Dusty.app: every regular file and every embedded Python module is attributed to",
        "a component below, and an unattributed file stops the build.",
        "",
        "Qt frameworks stay replaceable dynamic libraries under LGPL-3.0-only; FFmpeg is",
        "a separate LGPL-2.1-or-later executable. Original available license and copyright",
        "texts are retained in the licenses folder next to this file. " + WINDOWS_SOURCE_SENTENCE,
        "Where no text is available yet, the item is listed under Open items: unresolved,",
        "not waived.",
        "",
        "## Components",
        "",
        "| Component | Version | License | Copyright | Source | License texts |",
        "|---|---|---|---|---|---|",
    ]
    for item in items.values():
        texts = ", ".join(f"licenses/{name}" for name in item.texts) or "none required"
        lines.append(
            f"| {item.name} | {item.version} | {item.license} | {item.copyright} | "
            f"{item.source} | {texts} |"
        )
    lines += [
        "",
        "## CPython and the libraries inside libpython3.12.dylib",
        "",
        "python-build-standalone links these libraries statically into libpython3.12.dylib;",
        "the GUI and dusty-fetch each ship one copy. Detected in the shipped file:",
        "",
        "| Library | Version | License | License text |",
        "|---|---|---|---|",
    ]
    for library in statics:
        retained = library["text"]
        cell = f"licenses/{retained}" if retained else "not yet retained (open item)"
        if library["name"] in NO_TEXT_NEEDED:
            cell = "none required"
        lines.append(
            f"| {library['name']} | {library['version']} | {library['license']} | {cell} |"
        )
    lines += [
        "",
        "zlib, ncurses and libedit are macOS system libraries, not shipped. Tcl/Tk is not",
        "shipped.",
        "",
        SECTION_QT,
        "",
    ]
    for module in qt["modules"]:
        lines.append(f"- {module['module']} {module['version']}")
    for plugin in qt["plugins"]:
        lines.append(f"- plugin {plugin}")
    lines += [
        f"- {qt['translations']} Qt translation files (.qm)",
        "",
        "Qt third-party code detected in the shipped binaries: "
        + ", ".join(qt["third_party_detected"])
        + ".",
        "",
        *qt_attribution_lines(attributions),
        "## Native pins",
        "",
        f"whisper.cpp: {pins['whisper_cpp']['tag']} commit {pins['whisper_cpp']['commit']} "
        f"with the approved patch {pins['whisper_cpp_macos']['patch']} "
        f"(sha256 {pins['whisper_cpp_macos']['patch_sha256']}).",
        f"ggml: {items['ggml'].version}, from the same whisper.cpp tree.",
        "",
        f"FFmpeg: {pins['ffmpeg']['tag']} commit {pins['ffmpeg']['commit']}.",
        f"Banner reported by the bundled ffmpeg: {banner}",
        "",
        "FFmpeg build configuration reported by the bundled binary (-buildconf):",
        "",
        "```text",
        buildconf,
        "```",
        "",
        "## FFmpeg corresponding source",
        "",
        f"Archive: {source['name']}, sha256 {source['sha256']},",
        f"from {source['url']}",
        f"(commit {source['commit']}). Build recipe: native/macos/build_ffmpeg.sh,",
        f"sha256 {sha256(recipe)}. The configure line above is the exact configuration.",
        "",
        "## Downloaded model data (not in this bundle)",
        "",
        "Dusty downloads these only on explicit request, into the user data folder.",
        "",
        "| File | Content | License | Upstream | License text |",
        "|---|---|---|---|---|",
        *model_rows(),
        "",
        SECTION_FILES,
        "",
        "| File | Components |",
        "|---|---|",
    ]
    for relative, keys in files.items():
        if is_macho(app / relative):
            lines.append(f"| {relative} | {', '.join(keys)} |")
    lines += ["", "## Open items", ""]
    lines += [f"- {gap}" for gap in gaps] or ["None. Every listed component has its license text."]
    lines.append("")
    return "\n".join(lines), gaps


def ffmpeg_report(app: Path, bin_dir: str) -> tuple[str, str]:
    """(first -version line, -buildconf output) of the bundled ffmpeg itself."""
    executable = app / bin_dir / "ffmpeg/ffmpeg"
    outputs = []
    for args in (["-version"], ["-hide_banner", "-buildconf"]):
        result = subprocess.run(
            [str(executable), *args],
            cwd=executable.parent,
            env=TOOL_ENV,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise NoticesError(f"Bundled ffmpeg {args[-1]} failed ({result.returncode})")
        outputs.append(result.stdout.strip())
    return outputs[0].splitlines()[0], outputs[1]


def generate(app: Path, *, bin_dir: str, version: str, banner: str, buildconf: str, audit: Path):
    """Return (notices text, inventory) for a staged, not yet signed Dusty.app."""
    analysis = json.loads((audit / "analysis.json").read_text(encoding="utf-8"))
    libpython = (app / "Contents/Frameworks/libpython3.12.dylib").read_bytes()
    statics = static_libraries(libpython)
    qt = qt_inventory(app)
    items = components(app, version, banner, qt, statics)
    files = {
        path.relative_to(app).as_posix(): attribute(
            path.relative_to(app).as_posix(), bin_dir, analysis
        )
        for path in regular_files(app)
    }
    unknown = {key for keys in files.values() for key in keys} - set(items)
    if unknown:
        raise NoticesError(f"Attributed to undefined components: {sorted(unknown)}")
    for item in items.values():
        for name in item.texts:
            if not (app / "Contents/Resources/licenses" / name).is_file():
                raise NoticesError(f"Referenced license text is missing: {name}")
    text, gaps = render(app, items, files, statics, qt, banner, buildconf)
    inventory = {
        "schema": 1,
        "components": {key: vars(item) for key, item in items.items()},
        "libpython_static_libraries": statics,
        "qt": qt,
        "files": files,
        "open_items": gaps,
    }
    return text, inventory


def write_notices(app: Path, *, bin_dir: str, version: str, audit: Path) -> dict:
    """Write Resources/THIRD_PARTY_NOTICES.md and audit/notices-inventory.json."""
    stage_texts(app)
    banner, buildconf = ffmpeg_report(app, bin_dir)
    text, inventory = generate(
        app, bin_dir=bin_dir, version=version, banner=banner, buildconf=buildconf, audit=audit
    )
    (app / "Contents/Resources" / NOTICES).write_text(text, encoding="utf-8")
    (audit / INVENTORY).write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    return inventory
