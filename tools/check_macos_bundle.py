"""Audit a built Dusty.app for macOS arm64 and exit nonzero on any finding.

Checks: every Mach-O file is thin arm64; every linked library and LC_RPATH is a
system path or resolves inside the bundle (no Homebrew, /usr/local, venv or
checkout paths); the offline GUI has no networking Python modules, Qt network or
web frameworks, while ssl is present only in the dusty-fetch helper; the
required resources and executables exist and no model weights are bundled; the
Info.plist values are honest (minimum OS covers every binary, no usage
descriptions); the bundled native programs match their verified sources apart
from the code signature; every Mach-O carries a hardened runtime signature;
codesign --verify --deep --strict passes; and the bundled THIRD_PARTY_NOTICES.md
lists every shipped Mach-O file with its component, every Qt module and plugin,
the native pins, the exact ffmpeg -buildconf output and only license texts that
are present.

Pure helpers here (Mach-O parsing, dependency classification, plist checks) are
shared with tools/build_macos_app.py and unit tested without macOS tools.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import re
import struct
import subprocess
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from tools.helper_programs import Program, gui_module_findings, load_programs

ROOT = Path(__file__).resolve().parents[1]
TOOL_ENV = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "C", "LC_ALL": "C"}

# Layout inside Dusty.app, relative to the bundle root (the .app folder).
# The downloader is a PyInstaller onedir tool: code in Helpers/dusty-fetch, its
# data files moved to Resources/dusty-fetch and linked back (codesign refuses
# plain data files in a code location).
FETCH_DIR = "Contents/Helpers/dusty-fetch"
FETCH_DATA = "Contents/Resources/dusty-fetch"
FETCH_EXECUTABLE = FETCH_DIR + "/dusty-fetch"
TLS_DIR = "Contents/Resources/tls"
GUI_EXECUTABLE = "Contents/MacOS/Dusty"
RESOURCES = "Contents/Resources"
BIN_DIRS = {"helpers": "Contents/Helpers/bin", "resources": "Contents/Resources/bin"}
NATIVE_PROGRAMS = (
    "ffmpeg/ffmpeg",
    "ffmpeg/ffprobe",
    "cpu/whisper-cli",
    "metal/whisper-cli",
    "metal/libggml-metal.0.dylib",
    "lifeline/dusty-lifeline",
)
REQUIRED_RESOURCES = (
    "models.json",
    "selftest.wav",
    "THIRD_PARTY_NOTICES.md",
    "Dusty.icns",
    "licenses/dusty-LICENSE.txt",
    "licenses/dusty-NOTICE.txt",
    "licenses/whisper.cpp-LICENSE.txt",
    "licenses/ffmpeg-LGPL-2.1.txt",
    "licenses/qt-LGPL-3.0.txt",
)
TLS_FILES = ("isrg-x1.pem", "isrg-x2.pem", "usertrust-ecc.pem", "usertrust-rsa.pem")
ALLOWED_QT_FRAMEWORKS = {"QtCore", "QtGui", "QtWidgets", "QtDBus"}
# Top-level packages the offline GUI must not embed (Windows parity) ...
GUI_FORBIDDEN_MODULES = {
    "dusty_fetch",
    "socket",
    "ssl",
    "asyncio",
    "multiprocessing",
    "docx",
    "lxml",
}
# ... and standard library network clients. Without socket they cannot import
# anyway; the spec excludes them so no client code ships at all. urllib.parse
# and the http package's status enum are plain data helpers and stay.
GUI_FORBIDDEN_EXACT = {
    "http.client",
    "http.cookiejar",
    "http.server",
    "urllib.request",
    "urllib.response",
    "ftplib",
    "smtplib",
    "imaplib",
    "poplib",
    "nntplib",
    "telnetlib",
    "socketserver",
    "xmlrpc.client",
    "xmlrpc.server",
    "webbrowser",
}
FETCH_FORBIDDEN_MODULES = {"dusty", "PySide6", "shiboken6"}
FORBIDDEN_GUI_FILE = re.compile(
    r"^(?:_ssl|_socket|_hashlib|select|_multiprocessing|_asyncio|_scproxy)\..*\.so$"
    r"|^lib(?:ssl|crypto)[.-]|^Qt(?:Network|WebEngine|Qml|Quick|Pdf|Svg)",
    re.IGNORECASE,
)
PLIST_FORBIDDEN_KEYS = {"NSAppTransportSecurity", "NSBonjourServices"}

# Mach-O constants (mach-o/loader.h, mach-o/fat.h).
MH_MAGIC_64 = 0xFEEDFACF
FAT_MAGICS = {0xCAFEBABE, 0xCAFEBABF}
CPU_TYPES = {0x0100000C: "arm64", 0x01000007: "x86_64"}
MH_EXECUTE = 0x2
LC_SEGMENT_64 = 0x19
LC_CODE_SIGNATURE = 0x1D
LC_ID_DYLIB = 0xD
LC_RPATH = 0x8000001C
LC_BUILD_VERSION = 0x32
LC_VERSION_MIN_MACOSX = 0x24
LC_DYLIBS = {0xC, 0x80000018, 0x8000001F, 0x20, 0x80000023}
SYSTEM_PREFIXES = ("/usr/lib/", "/System/Library/")
RELATIVE_PREFIXES = ("@rpath/", "@loader_path/", "@executable_path/")


class MachOError(ValueError):
    """The file is not a Mach-O image this audit can read."""


@dataclass
class MachO:
    arches: list[str]
    filetype: int = 0
    dylibs: list[str] = field(default_factory=list)
    dylib_id: str | None = None
    rpaths: list[str] = field(default_factory=list)
    minos: tuple[int, int, int] | None = None
    signature: tuple[int, int] | None = None  # LC_CODE_SIGNATURE dataoff, datasize
    signature_command: int | None = None  # file offset of that load command
    linkedit_fields: list[int] = field(default_factory=list)  # offsets of vmsize/filesize

    @property
    def thin_arm64(self) -> bool:
        return self.arches == ["arm64"]


def macho_magic(head: bytes) -> str | None:
    """'thin' for a 64-bit little-endian image, 'fat' for a universal file."""
    if len(head) < 4:
        return None
    if struct.unpack_from("<I", head)[0] == MH_MAGIC_64:
        return "thin"
    if struct.unpack_from(">I", head)[0] in FAT_MAGICS and len(head) >= 8:
        # Java class files share 0xCAFEBABE; a fat header has a small arch count.
        return "fat" if 0 < struct.unpack_from(">I", head, 4)[0] < 20 else None
    return None


def _cstring(data: bytes, offset: int) -> str:
    end = data.index(b"\0", offset)
    return data[offset:end].decode("utf-8", "surrogateescape")


def _version(value: int) -> tuple[int, int, int]:
    return value >> 16, (value >> 8) & 0xFF, value & 0xFF


def parse_macho(data: bytes) -> MachO:
    kind = macho_magic(data[:8])
    if kind == "fat":
        count = struct.unpack_from(">I", data, 4)[0]
        step = 32 if struct.unpack_from(">I", data)[0] == 0xCAFEBABF else 20
        arches = [
            CPU_TYPES.get(struct.unpack_from(">I", data, 8 + step * index)[0], "unknown")
            for index in range(count)
        ]
        return MachO(arches=arches)
    if kind != "thin" or len(data) < 32:
        raise MachOError("Not a 64-bit Mach-O image")
    cputype, _, filetype, ncmds, sizeofcmds = struct.unpack_from("<iiIII", data, 4)
    image = MachO(arches=[CPU_TYPES.get(cputype & 0xFFFFFFFF, "unknown")], filetype=filetype)
    offset = 32
    if 32 + sizeofcmds > len(data):
        raise MachOError("Truncated load commands")
    for _ in range(ncmds):
        cmd, cmdsize = struct.unpack_from("<II", data, offset)
        if cmdsize < 8 or offset + cmdsize > 32 + sizeofcmds:
            raise MachOError("Malformed load command")
        if cmd in LC_DYLIBS:
            image.dylibs.append(
                _cstring(data, offset + struct.unpack_from("<I", data, offset + 8)[0])
            )
        elif cmd == LC_ID_DYLIB:
            image.dylib_id = _cstring(data, offset + struct.unpack_from("<I", data, offset + 8)[0])
        elif cmd == LC_RPATH:
            image.rpaths.append(
                _cstring(data, offset + struct.unpack_from("<I", data, offset + 8)[0])
            )
        elif cmd == LC_BUILD_VERSION:
            image.minos = _version(struct.unpack_from("<I", data, offset + 12)[0])
        elif cmd == LC_VERSION_MIN_MACOSX and image.minos is None:
            image.minos = _version(struct.unpack_from("<I", data, offset + 8)[0])
        elif cmd == LC_CODE_SIGNATURE:
            image.signature = struct.unpack_from("<II", data, offset + 8)
            image.signature_command = offset
        elif cmd == LC_SEGMENT_64 and data[offset + 8 : offset + 24].rstrip(b"\0") == b"__LINKEDIT":
            image.linkedit_fields += [offset + 32, offset + 48]
        offset += cmdsize
    return image


def signature_neutral_digest(data: bytes) -> str:
    """SHA-256 of a thin Mach-O with its code signature and the sizes it changes removed.

    Re-signing (for example ad hoc with the hardened runtime) replaces only the
    signature blob at the end of __LINKEDIT and the sizes that record it, so two
    files with equal digests carry identical code, data and load commands.
    """
    image = parse_macho(data)
    if len(image.arches) != 1:
        raise MachOError("Universal files must be thinned before comparison")
    if image.signature is None or image.signature_command is None:
        return hashlib.sha256(data).hexdigest()
    buffer = bytearray(data[: image.signature[0]])
    for position in image.linkedit_fields:
        buffer[position : position + 8] = bytes(8)
    datasize = image.signature_command + 12
    buffer[datasize : datasize + 4] = bytes(4)
    return hashlib.sha256(bytes(buffer)).hexdigest()


def version_text(version: tuple[int, int, int]) -> str:
    major, minor, patch = version
    return f"{major}.{minor}" if patch == 0 else f"{major}.{minor}.{patch}"


def parse_version(text: str) -> tuple[int, int, int]:
    parts = [int(part) for part in text.split(".")]
    if not 1 <= len(parts) <= 3:
        raise ValueError("Version must have one to three numeric parts")
    major, minor, patch = parts + [0] * (3 - len(parts))
    return major, minor, patch


def classify_dependency(name: str) -> str:
    """'system', 'relative' (resolved inside the bundle later) or 'outside'."""
    if name.startswith(SYSTEM_PREFIXES) and ".." not in name.split("/"):
        return "system"
    if name.startswith(RELATIVE_PREFIXES):
        return "relative"
    return "outside"


def _expand(token: str, loader: Path, executable_dir: Path) -> Path | None:
    if token.startswith("@loader_path"):
        return Path(os.path.normpath(str(loader.parent) + token[len("@loader_path") :]))
    if token.startswith("@executable_path"):
        return Path(os.path.normpath(str(executable_dir) + token[len("@executable_path") :]))
    return None


def resolve_dependency(
    name: str, loader: Path, rpaths: Iterable[str], executable_dir: Path
) -> Path | None:
    """Return the existing file a relative install name loads, without following
    it outside the candidate list; None when nothing matches."""
    candidates: list[Path] = []
    if name.startswith("@rpath/"):
        for entry in rpaths:
            base = _expand(entry, loader, executable_dir)
            if base is not None:
                candidates.append(base / name[len("@rpath/") :])
    else:
        expanded = _expand(name, loader, executable_dir)
        if expanded is not None:
            candidates.append(expanded)
    return next((path for path in candidates if path.is_file()), None)


def executable_dir_for(path: Path, image: MachO) -> Path:
    """Folder dyld uses for @executable_path when this image is loaded."""
    if image.filetype == MH_EXECUTE:
        return path.parent
    for parent in path.parents:
        if parent.name == "Contents" and parent.parent.suffix == ".app":
            return parent / "MacOS"
    return path.parent


def iter_files(root: Path) -> Iterator[Path]:
    """Regular files and symlinks under root, without following directory links."""
    for directory, folders, files in os.walk(root, followlinks=False):
        base = Path(directory)
        for name in sorted(files):
            yield base / name
        for name in sorted(folders):
            if (base / name).is_symlink():
                yield base / name


def iter_macho(root: Path) -> Iterator[tuple[Path, MachO]]:
    for path in iter_files(root):
        if path.is_symlink() or not path.is_file():
            continue
        with path.open("rb") as stream:
            if macho_magic(stream.read(8)) is None:
                continue
        yield path, parse_macho(path.read_bytes())


def is_inside(path: Path, root: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def dependency_findings(app: Path) -> list[str]:
    findings = []
    for path, image in iter_macho(app):
        relative = path.relative_to(app).as_posix()
        if not image.thin_arm64:
            findings.append(f"Not thin arm64 ({'+'.join(image.arches)}): {relative}")
            continue
        executable_dir = executable_dir_for(path, image)
        for entry in image.rpaths:
            if not entry.startswith(("@loader_path", "@executable_path")):
                findings.append(f"Absolute LC_RPATH {entry}: {relative}")
            else:
                base = _expand(entry, path, executable_dir)
                if base is None or not is_inside(base, app):
                    findings.append(f"LC_RPATH leaves the bundle ({entry}): {relative}")
        for name in image.dylibs:
            kind = classify_dependency(name)
            if kind == "outside":
                findings.append(f"Non-system absolute dependency {name}: {relative}")
            elif kind == "relative":
                if name == image.dylib_id:
                    continue
                target = resolve_dependency(name, path, image.rpaths, executable_dir)
                if target is None:
                    findings.append(f"Unresolved dependency {name}: {relative}")
                elif not is_inside(target, app):
                    findings.append(f"Dependency resolves outside the bundle {name}: {relative}")
    return findings


def symlink_findings(app: Path) -> list[str]:
    findings = []
    for path in iter_files(app):
        if path.is_symlink():
            target = os.readlink(path)
            relative = path.relative_to(app).as_posix()
            if os.path.isabs(target):
                findings.append(f"Absolute symlink: {relative}")
            elif not is_inside(path, app) or not path.exists():
                findings.append(f"Symlink leaves the bundle or is broken: {relative}")
    return findings


def plist_findings(
    info: dict,
    *,
    version: str,
    minimum: tuple[int, int, int] | None,
    bundle_id: str = "org.dusty.Dusty",
) -> list[str]:
    """``bundle_id`` is the one the build recorded; public Dusty's by default."""
    findings = []
    expected = {
        "CFBundleIdentifier": bundle_id,
        "CFBundleExecutable": "Dusty",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": version,
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.productivity",
    }
    for key, value in expected.items():
        if info.get(key) != value:
            findings.append(f"Info.plist {key} is {info.get(key)!r}, expected {value!r}")
    declared = info.get("LSMinimumSystemVersion")
    if not isinstance(declared, str):
        findings.append("Info.plist LSMinimumSystemVersion is missing")
    elif minimum is not None and parse_version(declared) < minimum:
        findings.append(
            f"Info.plist LSMinimumSystemVersion {declared} is below the binaries' "
            f"minimum {version_text(minimum)}"
        )
    for key in info:
        if key.endswith("UsageDescription") or key in PLIST_FORBIDDEN_KEYS:
            findings.append(f"Info.plist declares {key}; Dusty needs no such permission")
    return findings


def module_findings(gui_modules: Iterable[str], fetch_modules: Iterable[str]) -> list[str]:
    findings = []
    gui = set(gui_modules)
    fetch = set(fetch_modules)
    for name in sorted(gui):
        top = name.split(".")[0]
        if (
            top in GUI_FORBIDDEN_MODULES
            or name in GUI_FORBIDDEN_EXACT
            or name.startswith(("PySide6.QtNetwork", "PySide6.QtWeb"))
        ):
            findings.append(f"Offline GUI embeds prohibited module {name}")
    for name in sorted(fetch):
        if name.split(".")[0] in FETCH_FORBIDDEN_MODULES:
            findings.append(f"Downloader embeds GUI module {name}")
    for required in ("ssl", "dusty_fetch"):
        if required not in fetch:
            findings.append(f"Downloader is missing module {required}")
    return findings


def gui_file_findings(app: Path) -> list[str]:
    findings = []
    fetch_parts = (app / FETCH_DIR, app / FETCH_DATA)
    everything = [*iter_files(app)]
    for directory, folders, _ in os.walk(app, followlinks=False):
        everything += [Path(directory) / name for name in folders]
    for path in sorted(set(everything)):
        if any(path.is_relative_to(part) for part in fetch_parts):
            continue
        name = path.name
        if FORBIDDEN_GUI_FILE.search(name):
            findings.append(
                f"Prohibited file in the offline GUI: {path.relative_to(app).as_posix()}"
            )
        if name.endswith(".framework") and name.removesuffix(".framework").startswith("Qt"):
            if name.removesuffix(".framework") not in ALLOWED_QT_FRAMEWORKS:
                findings.append(f"Unexpected Qt framework: {path.relative_to(app).as_posix()}")
    for part in fetch_parts:
        for path in iter_files(part):
            if re.search(r"PySide6|shiboken6|^Qt", path.name):
                findings.append(
                    f"Downloader contains Qt or PySide6: {path.relative_to(app).as_posix()}"
                )
    return findings


def model_findings(app: Path, manifest: dict | None) -> list[str]:
    names = set()
    if manifest:
        names = {item["file_name"] for group in ("models", "vad") for item in manifest[group]}
    return [
        f"Model weights must not be bundled: {path.relative_to(app).as_posix()}"
        for path in iter_files(app)
        if path.suffix == ".bin" or path.name in names
    ]


def required_findings(app: Path, bin_dir: str) -> list[str]:
    required = [GUI_EXECUTABLE, FETCH_EXECUTABLE, "Contents/Info.plist"]
    required += [f"{RESOURCES}/{name}" for name in REQUIRED_RESOURCES]
    required += [f"{TLS_DIR}/{name}" for name in TLS_FILES]
    required += [f"{bin_dir}/{name}" for name in NATIVE_PROGRAMS]
    findings = []
    for relative in required:
        path = app / relative
        if path.is_symlink() or not path.is_file():
            findings.append(f"Missing required bundle file: {relative}")
    for relative in [GUI_EXECUTABLE, FETCH_EXECUTABLE] + [
        f"{bin_dir}/{name}" for name in NATIVE_PROGRAMS if "/lib" not in name
    ]:
        path = app / relative
        if path.is_file() and not os.access(path, os.X_OK):
            findings.append(f"Not executable: {relative}")
    for parent in (app / bin_dir).parents:
        if parent == app.parent:
            break
        if parent.is_symlink():
            findings.append("A bin_dir ancestor is a symlink; launches would be refused")
    for path in iter_files(app / bin_dir):
        if path.is_symlink():
            findings.append(f"Symlink inside bin_dir: {path.relative_to(app).as_posix()}")
    return findings


def nested_code_findings(app: Path) -> list[str]:
    """codesign rejects plain data files where it expects nested code."""
    findings = []
    nested = [app / "Contents/MacOS", app / "Contents/Helpers"]
    for root in nested:
        for path in iter_files(root):
            if path.is_symlink():
                continue
            with path.open("rb") as stream:
                if macho_magic(stream.read(8)) is None:
                    findings.append(
                        f"Data file in a code location: {path.relative_to(app).as_posix()}"
                    )
    for path in (app / "Contents").iterdir():
        if path.is_file() and not path.is_symlink() and path.name not in {"Info.plist", "PkgInfo"}:
            findings.append(
                f"Unsealable file at the bundle root: {path.relative_to(app).as_posix()}"
            )
    return findings


def pyz_modules(executable: Path) -> tuple[list[str], list[str]]:
    """(scripts in run order, modules in the embedded PYZ) of a PyInstaller executable."""
    from PyInstaller.archive.readers import CArchiveReader  # type: ignore[import-untyped]

    archive = CArchiveReader(str(executable))
    scripts = [name for name, entry in archive.toc.items() if entry[-1] == "s"]
    pyz = archive.open_embedded_archive("PYZ.pyz")
    return scripts, sorted(pyz.toc)


def native_findings(app: Path, manifest: dict) -> list[str]:
    findings = []
    for record in manifest.get("natives", []):
        target = app / record["path"]
        source = Path(record["source"])
        if not target.is_file() or not source.is_file():
            findings.append(f"Native program or its source is missing: {record['path']}")
            continue
        if hashlib.sha256(source.read_bytes()).hexdigest() != record["source_sha256"]:
            findings.append(f"Native source no longer matches its trust hash: {record['path']}")
        if signature_neutral_digest(target.read_bytes()) != signature_neutral_digest(
            source.read_bytes()
        ):
            findings.append(f"Bundled native program differs from its source: {record['path']}")
    if not manifest.get("natives"):
        findings.append("Build manifest lists no native programs")
    return findings


def _tool(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, env=TOOL_ENV, capture_output=True, text=True, check=False)


def otool_findings(app: Path) -> list[str]:
    """Cross-check the parser against otool -L for every Mach-O image."""
    findings = []
    for path, image in iter_macho(app):
        result = _tool(["/usr/bin/otool", "-L", str(path)])
        if result.returncode:
            findings.append(f"otool failed: {path.relative_to(app).as_posix()}")
            continue
        listed = {line.strip().split(" (")[0] for line in result.stdout.splitlines()[1:]}
        parsed = set(image.dylibs) | ({image.dylib_id} if image.dylib_id else set())
        if listed != parsed:
            findings.append(f"otool -L and the parser disagree: {path.relative_to(app).as_posix()}")
    return findings


def signature_findings(app: Path) -> list[str]:
    findings = []
    for path, _ in iter_macho(app):
        result = _tool(["/usr/bin/codesign", "--display", "--verbose=2", str(path)])
        flags = re.search(r"flags=0x([0-9a-f]+)", result.stderr)
        if result.returncode or not flags or not int(flags.group(1), 16) & 0x10000:
            findings.append(f"No hardened runtime signature: {path.relative_to(app).as_posix()}")
    result = _tool(["/usr/bin/codesign", "--verify", "--deep", "--strict", str(app)])
    if result.returncode:
        detail = result.stderr.strip().splitlines()[-1:] or ["unknown error"]
        findings.append(f"codesign verify failed for {app.name}: {detail[0]}")
    return findings


ADHOC_ENTITLEMENT = "com.apple.security.cs.disable-library-validation"


def entitlement_policy(found: dict, *, entitled: bool, adhoc: bool) -> list[str]:
    """Only ad hoc builds may relax library validation, and only where recorded."""
    if not found:
        return []
    if adhoc and entitled and found == {ADHOC_ENTITLEMENT: True}:
        return []
    return [f"unexpected entitlements {sorted(found)}"]


def entitlement_findings(app: Path, manifest: dict) -> list[str]:
    findings = []
    adhoc = manifest.get("identity") == "adhoc"
    entitled = {
        item.split("/", 1)[1] if "/" in item else "" for item in manifest.get("entitled", [])
    }
    targets = [
        (path, path.relative_to(app).as_posix())
        for path, image in iter_macho(app)
        if image.filetype == MH_EXECUTE and path != app / GUI_EXECUTABLE
    ]
    targets.append((app, ""))
    for path, relative in targets:
        result = _tool(
            ["/usr/bin/codesign", "--display", "--entitlements", "-", "--xml", str(path)]
        )
        found = plistlib.loads(result.stdout.encode()) if result.stdout.strip() else {}
        for problem in entitlement_policy(found, entitled=relative in entitled, adhoc=adhoc):
            findings.append(f"{relative or app.name}: {problem}")
    return findings


def tls_findings(app: Path) -> list[str]:
    """The bundled roots must be the exact files dusty_fetch.tls pins."""
    try:
        from dusty_fetch.tls import ROOTS
    except ImportError:
        return ["dusty_fetch.tls is not importable; set PYTHONPATH to the checkout src"]
    findings = []
    for name, (pem_hash, _) in ROOTS.items():
        path = app / TLS_DIR / name
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() != pem_hash:
            findings.append(f"TLS root differs from its pin: {TLS_DIR}/{name}")
    if set(ROOTS) != set(TLS_FILES):
        findings.append("The checker's TLS file list differs from dusty_fetch.tls.ROOTS")
    return findings


# Notices coverage (P33). Deliberately independent of tools/macos_notices.py: the
# shipped files are enumerated here and each must appear in the bundled notices.
NOTICES_FILE = f"{RESOURCES}/THIRD_PARTY_NOTICES.md"
NOTICES_FILES_SECTION = "## Shipped native files"
NOTICES_QT_SECTION = "## Qt modules shipped"
NATIVE_COMPONENTS = (  # bin_dir prefix or file name start: component that must be named
    ("ffmpeg/", "ffmpeg"),
    ("cpu/whisper-cli", "whisper.cpp"),
    ("metal/whisper-cli", "whisper.cpp"),
    ("cpu/libwhisper", "whisper.cpp"),
    ("metal/libwhisper", "whisper.cpp"),
    ("cpu/libggml", "ggml"),
    ("metal/libggml", "ggml"),
    ("lifeline/", "dusty"),
)


def notices_section(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    if heading not in lines:
        return []
    start = lines.index(heading) + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return lines[start:end]


def notices_file_rows(text: str) -> dict[str, list[str]]:
    rows = {}
    for line in notices_section(text, NOTICES_FILES_SECTION):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 2 and cells[0] not in ("File", "---"):
            rows[cells[0]] = [item.strip() for item in cells[1].split(",") if item.strip()]
    return rows


def notices_findings(app: Path, bin_dir: str, buildconf: str | None = None) -> list[str]:
    """Every shipped Mach-O, native component and Qt module is in the bundled notices."""
    path = app / NOTICES_FILE
    if path.is_symlink() or not path.is_file():
        return [f"Notices missing: {NOTICES_FILE}"]
    text = path.read_text(encoding="utf-8")
    findings = []
    rows = notices_file_rows(text)
    if not rows:
        findings.append(f"Notices have no '{NOTICES_FILES_SECTION}' table")
    shipped = {
        image.relative_to(app).as_posix()
        for image, _ in iter_macho(app)
        if "_CodeSignature" not in image.parts
    }
    for relative in sorted(shipped - rows.keys()):
        findings.append(f"Shipped file not listed in the notices: {relative}")
    for relative in sorted(rows.keys() - shipped):
        findings.append(f"Notices list a file that is not shipped: {relative}")
    for relative, keys in sorted(rows.items()):
        if not keys:
            findings.append(f"Notices give no component for {relative}")
        inner = relative.removeprefix(bin_dir + "/")
        for prefix, component in NATIVE_COMPONENTS:
            if relative.startswith(bin_dir + "/") and inner.startswith(prefix):
                if component not in keys:
                    findings.append(f"Notices attribute {relative} without {component}")
    qt_lines = notices_section(text, NOTICES_QT_SECTION)
    qt_root = app / "Contents/Frameworks/PySide6/Qt"
    for framework in sorted((qt_root / "lib").glob("Qt*.framework")):
        if not any(line.startswith(f"- {framework.stem} ") for line in qt_lines):
            findings.append(f"Qt module not listed in the notices: {framework.stem}")
    for plugin in sorted((qt_root / "plugins").rglob("*.dylib")):
        name = plugin.relative_to(qt_root / "plugins").as_posix()
        if f"- plugin {name}" not in qt_lines:
            findings.append(f"Qt plugin not listed in the notices: {name}")
    for name in sorted(set(re.findall(r"licenses/([A-Za-z0-9_.+/-]+\.(?:txt|json))", text))):
        if not (app / RESOURCES / "licenses" / name).is_file():
            findings.append(f"Notices reference a missing license text: licenses/{name}")
    try:
        import tomllib

        pins = tomllib.loads((ROOT / "native/versions.toml").read_text(encoding="utf-8"))
        for value in (
            pins["whisper_cpp"]["commit"],
            pins["whisper_cpp_macos"]["patch_sha256"],
            pins["ffmpeg"]["commit"],
        ):
            if value not in text:
                findings.append(f"Notices omit the native pin {value[:12]}")
    except (OSError, KeyError, ValueError):
        findings.append("native/versions.toml is unreadable; native pins not checked")
    if buildconf is not None and buildconf.strip() not in text:
        findings.append("Notices do not carry the bundled ffmpeg's exact -buildconf output")
    return findings


def bundled_buildconf(app: Path, bin_dir: str) -> str | None:
    ffmpeg = app / bin_dir / "ffmpeg/ffmpeg"
    if not ffmpeg.is_file():
        return None
    result = _tool([str(ffmpeg), "-hide_banner", "-buildconf"])
    return result.stdout.strip() if result.returncode == 0 else None


def host_path_tokens() -> list[bytes]:
    """Build-host locations that must never be referenced by bundled code."""
    tokens = {str(ROOT), sys.prefix, sys.base_prefix, str(Path.home())}
    return sorted({token.encode() for token in tokens if len(token) > 1})


def embedded_path_report(app: Path, tokens: list[bytes]) -> tuple[list[str], list[str]]:
    """(findings, notes). Host paths inside data or Python code are findings; inside
    native Mach-O images they are compile-time strings (for example __FILE__ in
    assertions), reported as notes."""
    findings, notes = [], []
    for path in iter_files(app):
        if path.is_symlink() or not path.is_file():
            continue
        data = path.read_bytes()
        hit = max((token for token in tokens if token in data), key=len, default=None)
        if hit is None:
            continue
        relative = path.relative_to(app).as_posix()
        if macho_magic(data[:8]) is not None:
            notes.append(f"{relative} embeds build path {hit.decode(errors='replace')}")
        else:
            findings.append(f"Build-host path in bundled data: {relative}")
    return findings, notes


def pyz_path_findings(executable: Path, tokens: list[bytes]) -> list[str]:
    from PyInstaller.archive.readers import CArchiveReader  # type: ignore[import-untyped]

    archive = CArchiveReader(str(executable))
    pyz = archive.open_embedded_archive("PYZ.pyz")
    findings = []

    def walk(code) -> Iterator[str]:
        yield code.co_filename
        for constant in code.co_consts:
            if hasattr(constant, "co_filename"):
                yield from walk(constant)

    for name in sorted(pyz.toc):
        code = pyz.extract(name)
        if code is None or not hasattr(code, "co_filename"):
            continue
        if any(token.decode() in filename for filename in walk(code) for token in tokens):
            findings.append(f"Build-host path in embedded module {name} ({executable.name})")
    return findings


def minimum_os(root: Path, exclude: tuple[Path, ...] = ()) -> tuple[int, int, int] | None:
    versions = [
        image.minos
        for path, image in iter_macho(root)
        if image.minos and not any(is_inside(path, part) for part in exclude)
    ]
    return max(versions) if versions else None


def program_findings(app: Path, program: Program, modules: Iterable[str]) -> list[str]:
    """An add-on helper program: present, executable, only its own modules, its macOS."""
    findings = []
    executable = app / program.mac_executable
    label = f"Helper program {program.name}"
    if executable.is_symlink() or not executable.is_file():
        findings.append(f"Missing required bundle file: {program.mac_executable}")
    elif not os.access(executable, os.X_OK):
        findings.append(f"Not executable: {program.mac_executable}")
    for name in sorted(set(modules)):
        if name.split(".")[0] in program.forbidden_modules or name in GUI_FORBIDDEN_EXACT:
            findings.append(f"{label} embeds prohibited module {name}")
    for required in program.required_modules:
        if required not in set(modules):
            findings.append(f"{label} is missing module {required}")
    helper = minimum_os(app / program.mac_dir)
    if program.macos_minimum and helper is not None and helper > program.macos_minimum:
        findings.append(
            f"{label} needs macOS {version_text(helper)}, above "
            f"{version_text(program.macos_minimum)}"
        )
    for path in iter_files(app / program.mac_dir):
        if program.drops(path.name, "darwin"):
            findings.append(f"{label} ships an unused file: {path.relative_to(app).as_posix()}")
    return findings


def helper_folder_findings(app: Path, bin_dir: str, programs: tuple[Program, ...]) -> list[str]:
    """Contents/Helpers holds the downloader, the natives and the add-on programs only."""
    helpers = app / "Contents/Helpers"
    if not helpers.is_dir():
        return []
    known = {FETCH_DIR, bin_dir, *(program.mac_dir for program in programs)}
    return [
        f"Unexpected helper folder: {path.relative_to(app).as_posix()}"
        for path in sorted(helpers.iterdir())
        if path.relative_to(app).as_posix() not in known
    ]


def check(app: Path, audit: Path) -> tuple[list[str], dict]:
    app = app.resolve()
    if not (app / "Contents/Info.plist").is_file():
        return [f"Not an app bundle: {app}"], {
            "app": str(app),
            "macho_files": 0,
            "bytes": 0,
            "minimum_os": None,
            "bin_dir": None,
            "gui_runtime_scripts": [],
            "build_path_notes": [],
        }
    manifest_path = audit / "build-manifest.json"
    findings: list[str] = []
    manifest: dict = {}
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        findings.append(f"Build manifest missing: {manifest_path}")
    bin_dir = manifest.get("bin_dir", BIN_DIRS["helpers"])
    findings += required_findings(app, bin_dir)
    findings += nested_code_findings(app)
    findings += symlink_findings(app)
    findings += dependency_findings(app)
    findings += gui_file_findings(app)
    models_json = app / RESOURCES / "models.json"
    findings += model_findings(
        app, json.loads(models_json.read_text(encoding="utf-8")) if models_json.is_file() else None
    )
    programs = load_programs()
    findings += helper_folder_findings(app, bin_dir, programs)
    # A helper program gated by its add-on at run time does not raise the app's minimum.
    minimum = minimum_os(app, tuple(app / item.mac_dir for item in programs if item.macos_minimum))
    info_path = app / "Contents/Info.plist"
    version = manifest.get("version", "")
    if info_path.is_file():
        findings += plist_findings(
            plistlib.loads(info_path.read_bytes()),
            version=version,
            minimum=minimum,
            bundle_id=manifest.get("bundle_id", "org.dusty.Dusty"),
        )
    findings += tls_findings(app)
    tokens = host_path_tokens()
    gui_scripts: list[str] = []
    if (app / GUI_EXECUTABLE).is_file() and (app / FETCH_EXECUTABLE).is_file():
        gui_scripts, gui_modules = pyz_modules(app / GUI_EXECUTABLE)
        fetch_scripts, fetch_modules = pyz_modules(app / FETCH_EXECUTABLE)
        findings += module_findings(gui_modules, fetch_modules)
        # Public Dusty's GUI holds no add-on module; no GUI holds a helper's own modules.
        findings += gui_module_findings(gui_modules, programs)
        hooks = [name for name in gui_scripts if name != "pyiboot01_bootstrap"]
        if not hooks or hooks[0] != "runtime_guard":
            findings.append("Offline guard is not the first runtime hook of the GUI")
        if "runtime_guard" in fetch_scripts:
            findings.append("Downloader unexpectedly installs the offline guard")
        for executable in (app / GUI_EXECUTABLE, app / FETCH_EXECUTABLE):
            findings += pyz_path_findings(executable, tokens)
    for program in programs:
        executable = app / program.mac_executable
        if not executable.is_file():
            findings += program_findings(app, program, ())
            continue
        program_scripts, program_modules = pyz_modules(executable)
        findings += program_findings(app, program, program_modules)
        hooks = [name for name in program_scripts if name != "pyiboot01_bootstrap"]
        if not hooks or hooks[0] != "runtime_guard":
            findings.append(f"Offline guard is not the first runtime hook of {program.name}")
        findings += pyz_path_findings(executable, tokens)
    data_findings, notes = embedded_path_report(app, tokens)
    findings += data_findings
    if manifest:
        findings += native_findings(app, manifest)
    findings += notices_findings(
        app, bin_dir, bundled_buildconf(app, bin_dir) if sys.platform == "darwin" else None
    )
    if sys.platform == "darwin":
        findings += otool_findings(app)
        findings += signature_findings(app)
        findings += entitlement_findings(app, manifest)
    else:
        findings.append("otool and codesign checks need macOS")
    machos = list(iter_macho(app))
    summary = {
        "app": str(app),
        "macho_files": len(machos),
        "bytes": sum(path.stat().st_size for path in iter_files(app) if not path.is_symlink()),
        "minimum_os": version_text(minimum) if minimum else None,
        "bin_dir": bin_dir,
        "gui_runtime_scripts": gui_scripts,
        "build_path_notes": notes,
    }
    return findings, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("app", type=Path, help="Path to Dusty.app")
    parser.add_argument(
        "--audit", type=Path, help="Build audit folder (default: <app folder>/audit)"
    )
    parser.add_argument("--json", type=Path, help="Also write findings and summary here")
    args = parser.parse_args(argv)
    audit = args.audit or args.app.resolve().parent / "audit"
    findings, summary = check(args.app, audit)
    print(
        f"Mach-O files: {summary['macho_files']}, size: {summary['bytes']} bytes, "
        f"minimum macOS: {summary['minimum_os']}, bin_dir: {summary['bin_dir']}"
    )
    if summary["build_path_notes"]:
        print(f"Notes: {len(summary['build_path_notes'])} native images embed build paths")
        for note in summary["build_path_notes"]:
            print("  note: " + note)
    if args.json:
        args.json.write_text(
            json.dumps({"findings": findings, "summary": summary}, indent=2), encoding="utf-8"
        )
    if findings:
        print(f"{len(findings)} finding(s):")
        print("\n".join("  " + item for item in findings))
        return 1
    print("macOS bundle check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
