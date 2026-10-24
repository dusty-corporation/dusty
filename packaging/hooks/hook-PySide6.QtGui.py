"""Keep only the GUI plugins Dusty uses, before dependency analysis."""

from pathlib import Path

from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
# PDF image loading and virtual keyboard plugins otherwise pull in QML/Network.
# Widgets use native Windows input and the Fusion style; icons are ICO/PNG.
binaries = [
    (source, destination)
    for source, destination in binaries
    if Path(source).name.lower() in {"qwindows.dll", "qoffscreen.dll", "qminimal.dll", "qico.dll"}
]
