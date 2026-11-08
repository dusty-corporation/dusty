"""macOS: keep only the Qt platform plugins Dusty uses, before dependency analysis."""

from pathlib import Path

from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
# cocoa is the real platform; offscreen and minimal serve headless checks, as on
# Windows. Image format, icon engine, TUIO touch and virtual keyboard plugins are
# unused (Dusty draws its own icons; the Dock icon is the bundle .icns) and some
# of them link QtNetwork, QML, PDF or SVG frameworks.
KEEP = {"libqcocoa.dylib", "libqoffscreen.dylib", "libqminimal.dylib"}
binaries = [(source, destination) for source, destination in binaries if Path(source).name in KEEP]
