"""Build Dusty.app for macOS arm64 into a new folder and sign it ad hoc.

    python -m tools.build_macos_app build/mac-app-1 --native-root <dir>

One command: renders the app icon, runs PyInstaller with packaging/dusty-macos.spec,
places the dusty-fetch onedir under Contents/Helpers, copies and hash-verifies the native
programs into bin_dir, builds the lifeline helper, copies resources and licenses,
sets LSMinimumSystemVersion from the binaries actually shipped, signs every piece
inside-out with the hardened runtime and verifies with codesign --deep --strict.

--native-root holds the native builds. When native-v3 is present (whisper-cpu,
whisper-metal and ffmpeg, each a package folder plus SHA256SUMS.txt, built by
native/macos/build_whisper.sh and build_ffmpeg.sh with an explicit deployment
target and no embedded build paths) every native program comes from it.
Otherwise the older pair is used: runtime-v1 (ffmpeg, ffprobe and
native-runtime-v1.json) and native-v2/whisper-{cpu,metal}. Nothing is
downloaded. Models are never bundled; they live in the user data folder.

Signing defaults to ad hoc ("-") with the hardened runtime. Ad hoc signatures have
no Team ID, so library validation would stop the executables that load bundled
libraries (the two PyInstaller bootloaders and both whisper-cli builds); only
those get packaging/macos/adhoc.entitlements (disable-library-validation), and
only in ad hoc builds. A Developer ID identity can be passed later with
--identity; it uses no entitlements unless --entitlements is given. Notarization
is out of scope here.

Layout inside Dusty.app/Contents (see docs in the MAC10-PACKAGE report):
    MacOS/Dusty                      PyInstaller bootloader for the offline GUI
    Frameworks/                      Python, PySide6 and Qt (code only)
    Resources/                       models.json, selftest.wav, tls/, notices,
                                     licenses, icons and PyInstaller data
    Helpers/bin/ffmpeg/{ffmpeg,ffprobe}
    Helpers/bin/cpu/whisper-cli and its dylibs
    Helpers/bin/metal/whisper-cli and its dylibs
    Helpers/bin/lifeline/dusty-lifeline
    Helpers/dusty-fetch/dusty-fetch  the isolated downloader (PyInstaller onedir);
                                     its data files live in Resources/dusty-fetch
                                     and are linked back by relative symlinks
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

from tools.check_macos_bundle import (
    BIN_DIRS,
    FETCH_DATA,
    FETCH_DIR,
    MH_EXECUTE,
    RESOURCES,
    TLS_DIR,
    TOOL_ENV,
    iter_files,
    iter_macho,
    macho_magic,
    minimum_os,
    parse_macho,
    version_text,
)
from tools.extension_files import extension_catalogs, extension_model_files
from tools.helper_programs import ADDON_MODULES, load_programs
from tools.macos_notices import NoticesError, write_notices

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ID = "org.dusty.Dusty"
DISPLAY_NAME = "Dusty"
SPEC = ROOT / "packaging/dusty-macos.spec"
ADHOC_ENTITLEMENTS = ROOT / "packaging/macos/adhoc.entitlements"
BOOTLOADERS = {"Contents/MacOS/Dusty", FETCH_DIR + "/dusty-fetch"}
BACKENDS = ("cpu", "metal")
NATIVE_V3 = "native-v3"
NATIVE_V3_PACKAGES = ("whisper-cpu", "whisper-metal", "ffmpeg")
ICON_SIZES = {  # iconset file name: pixel size
    "icon_16x16.png": 16,
    "icon_16x16@2x.png": 32,
    "icon_32x32.png": 32,
    "icon_32x32@2x.png": 64,
    "icon_128x128.png": 128,
    "icon_128x128@2x.png": 256,
    "icon_256x256.png": 256,
    "icon_256x256@2x.png": 512,
    "icon_512x512.png": 512,
    "icon_512x512@2x.png": 1024,
}
LICENSES = {  # destination under Resources/licenses: source relative to ROOT
    "dusty-LICENSE.txt": "LICENSE",
    "dusty-NOTICE.txt": "NOTICE",
    "ffmpeg-LGPL-2.1.txt": "packaging/licenses/ffmpeg-LGPL-2.1.txt",
    "qt-LGPL-3.0.txt": "packaging/licenses/qt-LGPL-3.0.txt",
    "qt-GPL-3.0-reference.txt": "packaging/licenses/qt-GPL-3.0-reference.txt",
    "libffi-MIT.txt": "packaging/licenses/libffi-MIT.txt",
    "openssl-Apache-2.0.txt": "packaging/licenses/openssl-Apache-2.0.txt",
    "public-ca-NOTICE.txt": "resources/tls/NOTICE.txt",
    "public-ca-sources.json": "resources/tls/sources.json",
}


class BuildError(RuntimeError):
    """The bundle could not be built safely; the output folder is left for inspection."""


@dataclass(frozen=True)
class Native:
    """One native file to place under bin_dir, with the trust hash of its source."""

    destination: str  # relative to bin_dir
    source: Path
    sha256: str
    trust: str


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def project_version(root: Path = ROOT) -> str:
    version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    match = re.search(
        r'^__version__ = "([^"]+)"$',
        (root / "src/dusty/__init__.py").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if match is None or match.group(1) != version:
        raise BuildError("pyproject.toml and dusty.__version__ disagree")
    return version


def validate_output(output: Path, root: Path = ROOT) -> Path:
    """A new folder whose parent exists; inside the repository only under build/."""
    if output.exists() or output.is_symlink():
        raise BuildError(f"Refusing existing output folder: {output}")
    parent = output.parent.resolve(strict=False)
    if not parent.is_dir():
        raise BuildError("The output folder's parent must already exist")
    resolved = parent / output.name
    if resolved.is_relative_to(root.resolve()) and not resolved.is_relative_to(
        root.resolve() / "build"
    ):
        raise BuildError("Inside the repository the output must be under build/")
    return resolved


def layout(bin_choice: str) -> dict[str, str]:
    """Bundle-relative locations for a bin_dir choice ('helpers' is the shipped layout)."""
    if bin_choice not in BIN_DIRS:
        raise BuildError(f"Unknown bin_dir choice: {bin_choice}")
    return {
        "bin_dir": BIN_DIRS[bin_choice],
        "fetch_dir": FETCH_DIR,
        "fetch_data": FETCH_DATA,
        "tls_dir": TLS_DIR,
        "resources": RESOURCES,
        "gui_executable": "Contents/MacOS/Dusty",
    }


def read_sums(path: Path) -> dict[str, str]:
    sums = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(maxsplit=1)
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise BuildError(f"Invalid hash line in {path}")
        sums[name.strip().lstrip("*")] = digest
    return sums


def native_generation(native_root: Path) -> str:
    """'native-v3' when that folder exists, otherwise the older runtime-v1 plus native-v2.

    A present but incomplete native-v3 is an error rather than a silent mix of builds.
    """
    folder = native_root / NATIVE_V3
    if not folder.exists() and not folder.is_symlink():
        return "native-v2"
    if folder.is_symlink() or not folder.is_dir():
        raise BuildError(f"{folder} is not a plain folder")
    missing = [
        name
        for name in NATIVE_V3_PACKAGES
        if not (folder / name / "package").is_dir()
        or not (folder / name / "SHA256SUMS.txt").is_file()
    ]
    if missing:
        raise BuildError(f"{NATIVE_V3} is incomplete, missing: {', '.join(missing)}")
    return NATIVE_V3


def package_ffmpeg_natives(package: Path) -> list[Native]:
    """ffmpeg and ffprobe from a build_ffmpeg.sh package, matched against SHA256SUMS.txt."""
    sums_path = package.parent / "SHA256SUMS.txt"
    sums = read_sums(sums_path)
    natives = []
    for role in ("ffmpeg", "ffprobe"):
        source = package / role
        if source.is_symlink() or not source.is_file() or role not in sums:
            raise BuildError(f"{role} is missing from the package or SHA256SUMS.txt")
        natives.append(Native(f"ffmpeg/{role}", source, sums[role], str(sums_path)))
    return natives


def ffmpeg_natives(native_root: Path) -> list[Native]:
    if native_generation(native_root) == NATIVE_V3:
        return package_ffmpeg_natives(native_root / NATIVE_V3 / "ffmpeg/package")
    runtime = native_root / "runtime-v1/Contents"
    trust = runtime / "Resources/native-runtime-v1.json"
    artifacts = {
        item["role"]: item for item in json.loads(trust.read_text(encoding="utf-8"))["artifacts"]
    }
    natives = []
    for role in ("ffmpeg", "ffprobe"):
        item = artifacts.get(role)
        if item is None or item["path"] != f"Helpers/{role}":
            raise BuildError(f"{role} is not listed as expected in native-runtime-v1.json")
        source = runtime / item["path"]
        if source.is_symlink() or source.stat().st_size != item["size_bytes"]:
            raise BuildError(f"{role} source is linked or has the wrong size")
        natives.append(Native(f"ffmpeg/{role}", source, item["sha256"], str(trust)))
    return natives


def whisper_natives(native_root: Path, backend: str) -> list[Native]:
    """whisper-cli plus the closure of @rpath dylibs it loads, stored under the exact
    install names (real files, no symlinks), each matched against SHA256SUMS.txt."""
    package = native_root / f"{native_generation(native_root)}/whisper-{backend}/package"
    sums_path = package.parent / "SHA256SUMS.txt"
    sums = read_sums(sums_path)
    pending, seen, natives = ["whisper-cli"], set(), []
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        source = package / name
        if not source.exists() or name not in sums:
            raise BuildError(f"{backend}/{name} is missing from the package or SHA256SUMS.txt")
        real = source.resolve(strict=True)
        if not real.is_relative_to(package.resolve()):
            raise BuildError(f"{backend}/{name} links outside its package")
        natives.append(Native(f"{backend}/{name}", real, sums[name], str(sums_path)))
        image = parse_macho(real.read_bytes())
        if image.rpaths != ["@loader_path"]:
            raise BuildError(f"{backend}/{name} is not relocatable with @loader_path")
        for dependency in image.dylibs:
            if dependency.startswith("@rpath/") and dependency != image.dylib_id:
                pending.append(dependency.removeprefix("@rpath/"))
    return sorted(natives, key=lambda item: item.destination)


def whisper_license(native_root: Path) -> Native:
    package = native_root / f"{native_generation(native_root)}/whisper-cpu/package"
    sums_path = package.parent / "SHA256SUMS.txt"
    return Native(
        "whisper.cpp-LICENSE.txt",
        package / "LICENSE.txt",
        read_sums(sums_path)["LICENSE.txt"],
        str(sums_path),
    )


def verify_source(native: Native) -> None:
    if sha256(native.source) != native.sha256:
        raise BuildError(f"{native.destination} source does not match {native.trust}")


def build_lifeline(work: Path) -> Native:
    out = work / "lifeline"
    run(["/bin/bash", str(ROOT / "native/macos/build_lifeline.sh"), str(out)], cwd=ROOT)
    sums = read_sums(out / "SHA256SUMS")
    source = out / "lifeline/dusty-lifeline"
    return Native(
        "lifeline/dusty-lifeline", source, sums["lifeline/dusty-lifeline"], str(out / "SHA256SUMS")
    )


def run(
    args: list[str], *, cwd: Path, env: dict[str, str] | None = None, log: Path | None = None
) -> str:
    result = subprocess.run(
        args, cwd=cwd, env=env or TOOL_ENV, capture_output=True, text=True, check=False
    )
    if log is not None:
        log.write_text(result.stdout + result.stderr, encoding="utf-8")
    if result.returncode:
        detail = (result.stderr or result.stdout).strip().splitlines()[-3:]
        raise BuildError(f"{Path(args[0]).name} failed ({result.returncode}): {' | '.join(detail)}")
    return result.stdout + result.stderr


def make_icns(work: Path) -> Path:
    """Render the waveform mark at every Dock size and pack it with iconutil.

    The drawing matches dusty.app.theme.application_icon; the 64 pixel result is
    compared with it so the two cannot drift apart silently.
    """
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter

    application = QGuiApplication.instance() or QGuiApplication([])

    def render(size: int) -> QImage:
        image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#256847"))
        painter.drawRoundedRect(QRectF(0, 0, size, size), size / 4, size / 4)
        painter.setBrush(QColor("#eff5e7"))
        for x, height in ((0.24, 0.25), (0.41, 0.58), (0.58, 0.40), (0.75, 0.18)):
            painter.drawRoundedRect(
                QRectF(size * (x - 0.045), size * (1 - height) / 2, size * 0.09, size * height),
                size * 0.04,
                size * 0.04,
            )
        painter.end()
        return image

    from dusty.app.theme import application_icon

    reference = (
        application_icon()
        .pixmap(64, 64)
        .toImage()
        .convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    )
    if reference != render(64):
        raise BuildError("The Dock icon drawing no longer matches application_icon")
    iconset = work / "icon/Dusty.iconset"
    iconset.mkdir(parents=True)
    for name, size in ICON_SIZES.items():
        if not render(size).save(str(iconset / name), "PNG"):  # type: ignore[call-overload]
            raise BuildError("Icon export failed")
    target = work / "icon/Dusty.icns"
    run(["/usr/bin/iconutil", "-c", "icns", "-o", str(target), str(iconset)], cwd=work)
    del application
    return target


def run_pyinstaller(
    work: Path,
    audit: Path,
    icon: Path,
    bundle_id: str = BUNDLE_ID,
    display_name: str = DISPLAY_NAME,
) -> tuple[Path, Path, dict[str, Path]]:
    """The built app, dusty-fetch and each add-on helper program by name."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("DUSTY_")}
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYINSTALLER_STRICT_BUNDLE_CODESIGN_ERROR"] = "1"
    # Keep PyInstaller's binary cache inside this build instead of the user folder.
    env["PYINSTALLER_CONFIG_DIR"] = str(work / "pyinstaller/config")
    dist = work / "pyinstaller/dist"
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--workpath",
            str(work / "pyinstaller/work"),
            "--distpath",
            str(dist),
            str(SPEC),
            "--",
            "--icon",
            str(icon),
            "--audit",
            str(audit),
            "--bundle-id",
            bundle_id,
            "--display-name",
            display_name,
        ],
        cwd=ROOT,
        env=env,
        log=audit / "pyinstaller.log",
    )
    helpers = {program.name: dist / program.name for program in load_programs()}
    return dist / "Dusty.app", dist / "dusty-fetch", helpers


def check_analysis_origins(audit: Path, root: Path = ROOT) -> None:
    """Dusty modules must come from this checkout's src, never another checkout."""
    analysis = json.loads((audit / "analysis.json").read_text(encoding="utf-8"))
    source = (root / "src").resolve()
    groups = ["gui_pure", "fetch_pure", *(f"{item.group}_pure" for item in load_programs(root))]
    for group in groups:
        for name, path, _ in analysis[group]:
            if name.split(".")[0] in {"dusty", "dusty_fetch", *ADDON_MODULES} and not Path(
                path
            ).resolve().is_relative_to(source):
                raise BuildError(f"{name} was analysed from outside {source}")


def relocate_data_files(app: Path, code_dir: str, data_dir: str) -> list[str]:
    """Move every non-Mach-O file out of a code location and link it back.

    codesign refuses plain data files in Contents/Helpers ("code object is not
    signed at all"), so they live under Contents/Resources as sealed resources,
    the same cross-link scheme PyInstaller's BUNDLE uses for the GUI.
    """
    code_root, moved = app / code_dir, []
    for path in list(iter_files(code_root)):
        if path.is_symlink() or not path.is_file():
            continue
        with path.open("rb") as stream:
            if macho_magic(stream.read(8)) is not None:
                continue
        relative = path.relative_to(code_root)
        target = app / data_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(path, target)
        path.symlink_to(os.path.relpath(target, path.parent))
        moved.append(relative.as_posix())
    return sorted(moved)


def stage_natives(app: Path, bin_dir: str, natives: list[Native]) -> list[dict]:
    records = []
    for native in natives:
        target = app / bin_dir / native.destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(native.source, target)
        os.chmod(target, 0o755)
        if sha256(target) != native.sha256:
            raise BuildError(f"Copy of {native.destination} does not match its source")
        records.append(
            {
                "path": f"{bin_dir}/{native.destination}",
                "source": str(native.source),
                "source_sha256": native.sha256,
                "trust": native.trust,
            }
        )
    return records


def stage_resources(app: Path, native_root: Path, version: str, bin_dir: str) -> None:
    resources = app / RESOURCES
    for name in ("models.json", "selftest.wav", *extension_catalogs()):
        (resources / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "resources" / name, resources / name)
    # dusty_fetch.tls reads the pinned roots from the app's Contents/Resources/tls.
    shutil.copytree(ROOT / "resources/tls", app / TLS_DIR)
    shutil.copytree(ROOT / "resources/icons", resources / "icons")
    licenses = resources / "licenses"
    licenses.mkdir()
    for destination, source in LICENSES.items():
        shutil.copyfile(ROOT / source, licenses / destination)
    shutil.copyfile(
        Path(sys.base_prefix) / "lib/python3.12/LICENSE.txt", licenses / "cpython-LICENSE.txt"
    )
    import importlib.metadata as metadata

    copying = next(
        Path(str(file.locate()))
        for file in metadata.files("pyinstaller") or []
        if file.name == "COPYING.txt"
    )
    shutil.copyfile(copying, licenses / "pyinstaller-COPYING.txt")
    whisper = whisper_license(native_root)
    verify_source(whisper)
    shutil.copyfile(whisper.source, licenses / whisper.destination)
    # Generated from the shipped files (P33); fails closed on anything unattributed.
    try:
        write_notices(app, bin_dir=bin_dir, version=version, audit=app.parent / "audit")
    except NoticesError as error:
        raise BuildError(f"Notices: {error}") from error
    # The notices dialog currently reads Contents/THIRD_PARTY_NOTICES.md
    # (resources_dir.parent). A plain file there cannot be sealed; a relative
    # symlink can. Remove it once the dialog reads from resources_dir.
    (app / "Contents/THIRD_PARTY_NOTICES.md").symlink_to("Resources/THIRD_PARTY_NOTICES.md")
    manifest = json.loads((resources / "models.json").read_text(encoding="utf-8"))
    forbidden = {item["file_name"] for group in ("models", "vad") for item in manifest[group]}
    forbidden |= extension_model_files(resources)
    if any(path.name in forbidden or path.suffix == ".bin" for path in iter_files(app)):
        raise BuildError("Model weights must not be bundled")


def set_minimum_os(bundle: Path, scope: Path, exclude: tuple[Path, ...] = ()) -> str:
    minimum = minimum_os(scope, exclude)
    if minimum is None:
        raise BuildError(f"No Mach-O minimum OS found under {scope}")
    info_path = bundle / "Contents/Info.plist"
    info = plistlib.loads(info_path.read_bytes())
    info["LSMinimumSystemVersion"] = version_text(minimum)
    info_path.write_bytes(plistlib.dumps(info))
    return version_text(minimum)


def bundle_main_executables(root: Path) -> set[Path]:
    mains = set()
    for path in iter_files(root):
        if path.name == "Info.plist" and path.parent.name == "Contents":
            name = plistlib.loads(path.read_bytes()).get("CFBundleExecutable")
            if name:
                mains.add((path.parent / "MacOS" / name).resolve())
    return mains


def signing_order(app: Path) -> list[Path]:
    """Every loose Mach-O, framework version and app bundle, deepest first, app last.

    A container always has fewer path parts than anything inside it, so sorting by
    depth signs contents before the bundle that seals them.
    """
    mains = bundle_main_executables(app)
    targets: list[Path] = []
    frameworks: set[Path] = set()
    for directory, folders, _ in os.walk(app, followlinks=False):
        for folder in folders:
            path = Path(directory) / folder
            if path.is_symlink():
                continue
            if folder.endswith(".framework"):
                current = (path / "Versions/Current").resolve()
                frameworks.add(current)
                targets.append(current)
            elif folder.endswith(".app"):
                targets.append(path)
    for path, _ in iter_macho(app):
        resolved = path.resolve()
        framework_main = (
            resolved.parent in frameworks
            and resolved.parent.parent.parent.name == resolved.name + ".framework"
        )
        if resolved not in mains and not framework_main:
            targets.append(path)
    targets.append(app)
    return sorted(dict.fromkeys(targets), key=lambda path: len(path.parts), reverse=True)


def codesign_args(
    identity: str,
    entitlements: Path | None,
    *,
    executable: bool,
    loose: bool,
    bundle_id: str = BUNDLE_ID,
) -> list[str]:
    args = ["/usr/bin/codesign", "--force", "--sign", identity, "--options", "runtime"]
    args.append("--timestamp=none" if identity == "-" else "--timestamp")
    if loose:
        args += ["--prefix", bundle_id + "."]
    if entitlements is not None and executable:
        args += ["--entitlements", str(entitlements)]
    return args


def loads_bundled_code(app: Path, target: Path) -> bool:
    """True for executables that load libraries from inside the bundle."""
    if target.suffix == ".app":
        return True  # its main executable is the GUI bootloader
    if target.is_dir():
        return False
    image = parse_macho(target.read_bytes())
    relative = target.relative_to(app).as_posix()
    bootloaders = BOOTLOADERS | {program.mac_executable for program in load_programs()}
    return image.filetype == MH_EXECUTE and (
        relative in bootloaders or any(name.startswith("@") for name in image.dylibs)
    )


def entitlements_for(
    app: Path, target: Path, identity: str, entitlements: Path | None
) -> Path | None:
    if entitlements is not None:
        return entitlements if loads_bundled_code(app, target) else None
    if identity == "-" and loads_bundled_code(app, target):
        return ADHOC_ENTITLEMENTS
    return None


def sign_bundle(
    app: Path,
    identity: str = "-",
    entitlements: Path | None = None,
    bundle_id: str = BUNDLE_ID,
) -> list[str]:
    """Sign inside-out; return the bundle paths that received entitlements."""
    entitled = []
    for target in signing_order(app):
        chosen = entitlements_for(app, target, identity, entitlements)
        args = codesign_args(
            identity,
            chosen,
            executable=chosen is not None,
            loose=target.is_file(),
            bundle_id=bundle_id,
        )
        run([*args, str(target)], cwd=app.parent)
        if chosen is not None:
            entitled.append(target.relative_to(app.parent).as_posix())
    return entitled


def verify_signature(app: Path, log: Path) -> None:
    output = run(
        ["/usr/bin/codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app)],
        cwd=app.parent,
    )
    log.write_text(output, encoding="utf-8")


def bundle_bytes(app: Path) -> int:
    return sum(path.stat().st_size for path in iter_files(app) if not path.is_symlink())


def build(
    output: Path,
    native_root: Path,
    *,
    bin_choice: str = "helpers",
    identity: str = "-",
    entitlements: Path | None = None,
    bundle_id: str = BUNDLE_ID,
    display_name: str = DISPLAY_NAME,
) -> dict:
    """The bundle id and name default to Dusty's; another build may pass its own."""
    if sys.platform != "darwin" or os.uname().machine != "arm64":
        raise BuildError("Building Dusty.app needs macOS on Apple Silicon")
    started = time.monotonic()
    output = validate_output(output)
    places = layout(bin_choice)
    version = project_version()
    natives = ffmpeg_natives(native_root)
    for backend in BACKENDS:
        natives += whisper_natives(native_root, backend)
    for native in natives:  # Fail before the long PyInstaller run.
        verify_source(native)
    output.mkdir()
    work, audit = output / "work", output / "audit"
    work.mkdir()
    audit.mkdir()
    natives.append(build_lifeline(work))
    verify_source(natives[-1])
    icon = make_icns(work)
    built_app, built_fetch, built_helpers = run_pyinstaller(
        work, audit, icon, bundle_id, display_name
    )
    check_analysis_origins(audit)
    app = output / "Dusty.app"
    shutil.move(built_app, app)
    (app / "Contents/Helpers").mkdir()
    shutil.copytree(built_fetch, app / places["fetch_dir"], symlinks=True)
    relocated = relocate_data_files(app, places["fetch_dir"], places["fetch_data"])
    # Add-on helper programs are placed like dusty-fetch (tools/helper_programs.py).
    programs = load_programs()
    helper_places: dict[str, dict] = {}
    for program in programs:
        shutil.copytree(built_helpers[program.name], app / program.mac_dir, symlinks=True)
        helper_places[program.name] = {
            "dir": program.mac_dir,
            "data": program.mac_data,
            "relocated_data": relocate_data_files(app, program.mac_dir, program.mac_data),
        }
    if plistlib.loads((app / "Contents/Info.plist").read_bytes()).get("CFBundleIconFile") != (
        "Dusty.icns"
    ):
        raise BuildError("Unexpected bundle icon name")
    records = stage_natives(app, places["bin_dir"], natives)
    stage_resources(app, native_root, version, places["bin_dir"])
    # A helper program that needs a later macOS is gated by its add-on at run time
    # instead of raising the app's own minimum.
    minimum = set_minimum_os(
        app, app, tuple(app / item.mac_dir for item in programs if item.macos_minimum)
    )
    order = signing_order(app)
    entitled = sign_bundle(app, identity, entitlements, bundle_id)
    verify_signature(app, audit / "codesign-verify.txt")
    manifest = {
        "version": version,
        "bundle_id": bundle_id,
        "display_name": display_name,
        "native_generation": native_generation(native_root),
        "layout": places,
        "bin_dir": places["bin_dir"],
        "natives": records,
        "minimum_os": minimum,
        "fetch_relocated_data": relocated,
        "programs": helper_places,
        "identity": "adhoc" if identity == "-" else "identity",
        "entitlements": str(entitlements or ADHOC_ENTITLEMENTS) if entitled else None,
        "entitled": entitled,
        "signed_items": len(order),
        "bytes": bundle_bytes(app),
        "seconds": round(time.monotonic() - started, 1),
    }
    (audit / "build-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output", type=Path, help="New folder to create (must not exist)")
    parser.add_argument(
        "--native-root",
        type=Path,
        default=ROOT / "build/macos-arm64",
        help="Folder with native-v3, or with runtime-v1 and native-v2 (default: build/macos-arm64)",
    )
    parser.add_argument(
        "--bin-dir",
        choices=sorted(BIN_DIRS),
        default="helpers",
        help="helpers: Contents/Helpers/bin (shipped layout); resources: Contents/Resources/bin "
        "(testing only, matches the current runtime_paths)",
    )
    parser.add_argument("--identity", default="-", help="codesign identity (default: ad hoc)")
    parser.add_argument("--entitlements", type=Path, help="Entitlements plist (default: none)")
    parser.add_argument("--bundle-id", default=BUNDLE_ID, help="app identity (default: Dusty's)")
    parser.add_argument("--display-name", default=DISPLAY_NAME, help="app name shown by macOS")
    args = parser.parse_args(argv)
    try:
        manifest = build(
            args.output,
            args.native_root.resolve(),
            bin_choice=args.bin_dir,
            identity=args.identity,
            entitlements=args.entitlements,
            bundle_id=args.bundle_id,
            display_name=args.display_name,
        )
    except BuildError as error:
        print(f"Build failed: {error}", file=sys.stderr)
        return 1
    print(
        f"Built {args.output / 'Dusty.app'} in {manifest['seconds']} s, "
        f"{manifest['bytes']} bytes, minimum macOS {manifest['minimum_os']}, "
        f"{manifest['signed_items']} items signed, codesign verify passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
