# PyInstaller 6.16.0 macOS spec: Dusty.app (offline GUI) and the dusty-fetch onedir
# (isolated downloader), built as two separate analyses like packaging/dusty.spec.
# Run it through tools/build_macos_app.py, which places dusty-fetch under
# Dusty.app/Contents/Helpers, moves its data files into Contents/Resources,
# stages the native programs and TLS roots, sets the minimum OS from the actual
# binaries and signs the whole bundle inside-out.
#
# Spec arguments (after "--"): --icon <Dusty.icns> --audit <new audit folder>
import argparse
import json
import re
import shutil
import tomllib
from importlib.util import find_spec
from pathlib import Path

root = Path(SPECPATH).parent
options = argparse.ArgumentParser(prog="dusty-macos.spec")
options.add_argument("--icon", type=Path, required=True)
options.add_argument("--audit", type=Path, required=True)
spec_args = options.parse_args()
audit = spec_args.audit
audit.mkdir(parents=True, exist_ok=True)

version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
source_version = re.search(
    r'^__version__ = "([^"]+)"$',
    (root / "src/dusty/__init__.py").read_text(encoding="utf-8"),
    re.MULTILINE,
)
if source_version is None or source_version.group(1) != version:
    raise SystemExit("pyproject.toml and dusty.__version__ disagree")

BUNDLE_ID = "org.dusty.Dusty"
# The interpreter running PyInstaller decides which PySide6 is analysed; on macOS
# its extensions are <site-packages>/PySide6/Qt*.abi3.so.
qt = Path(find_spec("PySide6").submodule_search_locations[0])
KEEP_QT = {"QtCore", "QtGui", "QtWidgets"}
unused_qt = sorted(
    {"PySide6." + path.name.split(".")[0] for path in qt.glob("Qt*.so")}
    - {"PySide6." + name for name in KEEP_QT}
)
if not unused_qt:
    raise SystemExit("PySide6 extension modules were not found")

gui = Analysis(
    [str(root / "packaging/dusty_entry.py")],
    pathex=[str(root / "src")],
    hookspath=[str(root / "packaging/macos/hooks")],
    excludes=[
        "dusty_fetch", "docx", "lxml", "socket", "ssl", "_socket", "_ssl", "_hashlib",
        "select", "_overlapped", "_multiprocessing", "asyncio", "multiprocessing",
        "_scproxy", "http.client", "http.cookiejar", "http.server", "urllib.request",
        "urllib.response", "ftplib", "smtplib", "imaplib", "poplib", "nntplib", "telnetlib",
        "socketserver", "xmlrpc", "webbrowser", *unused_qt, "PySide6.QtNetwork", "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    ],
    # User runtime hooks run before PyInstaller's standard ones: the guard is first.
    runtime_hooks=[str(root / "packaging/runtime_guard.py")],
)
shutil.copyfile(WARNFILE, audit / "warn-gui.txt")
fetch = Analysis(
    [str(root / "packaging/fetch_entry.py")],
    pathex=[str(root / "src")],
    excludes=["dusty", "PySide6", "shiboken6"],
    runtime_hooks=[str(root / "packaging/runtime_fetch_crash.py")],
)
shutil.copyfile(WARNFILE, audit / "warn-fetch.txt")
(audit / "analysis.json").write_text(
    json.dumps(
        {
            "version": version,
            "gui_pure": gui.pure,
            "fetch_pure": fetch.pure,
            "gui_binaries": gui.binaries,
            "fetch_binaries": fetch.binaries,
            "gui_datas": gui.datas,
            "fetch_datas": fetch.datas,
            "gui_scripts": gui.scripts,
            "fetch_scripts": fetch.scripts,
        },
        indent=2,
    ),
    encoding="utf-8",
)

app = EXE(
    PYZ(gui.pure), gui.scripts, [], exclude_binaries=True, name="Dusty", console=False,
    target_arch="arm64", argv_emulation=False,
)
downloader = EXE(
    PYZ(fetch.pure), fetch.scripts, [], exclude_binaries=True, name="dusty-fetch",
    console=True, target_arch="arm64", argv_emulation=False,
)
gui_files = COLLECT(app, gui.binaries, gui.datas, name="Dusty")
fetch_files = COLLECT(downloader, fetch.binaries, fetch.datas, name="dusty-fetch")
# No usage descriptions: the GUI needs no network, camera, microphone or other
# protected resource. The downloader is a plain onedir tool, not a bundle: the
# app's runtime_paths and dusty_fetch.tls expect Contents/Helpers/dusty-fetch/
# dusty-fetch. LSMinimumSystemVersion is set by the build tool from the
# highest minos of every Mach-O file actually shipped.
BUNDLE(
    gui_files,
    name="Dusty.app",
    icon=str(spec_args.icon),
    bundle_identifier=BUNDLE_ID,
    version=version,
    info_plist={
        "CFBundleDevelopmentRegion": "en",
        "CFBundleVersion": version,
        "CFBundleShortVersionString": version,
        "NSHumanReadableCopyright": "Copyright 2026 Dusty contributors. Apache License 2.0.",
        "CFBundleName": "Dusty",
        "CFBundleDisplayName": "Dusty",
        "LSApplicationCategoryType": "public.app-category.productivity",
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
        "NSSupportsAutomaticGraphicsSwitching": True,
    },
)
