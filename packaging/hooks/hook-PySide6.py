"""Collect the required bindings without Mesa/ANGLE fallback renderers."""

from PyInstaller.utils.hooks.qt import ensure_single_qt_bindings_package

ensure_single_qt_bindings_package("PySide6")
hiddenimports = ["shiboken6", "inspect", "PySide6.support.deprecated"]
# Required Qt/CRT DLLs are found by native dependency analysis. The app uses
# raster widgets, not OpenGL; the stock hook's optional Mesa/ANGLE are omitted.
