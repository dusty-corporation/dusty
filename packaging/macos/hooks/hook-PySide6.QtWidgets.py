"""macOS: collect QtWidgets without style plugins, before dependency analysis."""

from pathlib import Path

from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
# Dusty applies the built-in Fusion style (dusty.app.theme), so the macOS style
# plugin is never loaded. Fusion is compiled into QtWidgets itself.
binaries = [
    (source, destination)
    for source, destination in binaries
    if Path(source).parent.name != "styles"
]
