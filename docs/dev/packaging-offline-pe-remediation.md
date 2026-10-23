# Split offline bundle PE evidence

Local candidate build after ADR 0021, 2026-10-22.

Gate result: 35 checked, no findings. This is local evidence; final CI is pending.
The two platform pins are in packaging/platform-socket-imports.json.
All other checked PEs have no imports from the five prohibited networking DLLs.

## Every checked PE

```text
_internal/_bz2.pyd
_internal/_ctypes.pyd
_internal/_decimal.pyd
_internal/_lzma.pyd
_internal/_uuid.pyd
_internal/_wmi.pyd
_internal/libffi-8.dll
_internal/PySide6/MSVCP140.dll
_internal/PySide6/MSVCP140_1.dll
_internal/PySide6/MSVCP140_2.dll
_internal/PySide6/plugins/imageformats/qico.dll
_internal/PySide6/plugins/platforms/qminimal.dll
_internal/PySide6/plugins/platforms/qoffscreen.dll
_internal/PySide6/plugins/platforms/qwindows.dll
_internal/PySide6/plugins/styles/qmodernwindowsstyle.dll
_internal/PySide6/pyside6.abi3.dll
_internal/PySide6/Qt6Core.dll
_internal/PySide6/Qt6Gui.dll
_internal/PySide6/Qt6Widgets.dll
_internal/PySide6/QtCore.pyd
_internal/PySide6/QtGui.pyd
_internal/PySide6/QtWidgets.pyd
_internal/PySide6/VCRUNTIME140.dll
_internal/PySide6/VCRUNTIME140_1.dll
_internal/python3.dll
_internal/python312.dll
_internal/shiboken6/MSVCP140.dll
_internal/shiboken6/Shiboken.pyd
_internal/shiboken6/shiboken6.abi3.dll
_internal/shiboken6/VCRUNTIME140.dll
_internal/shiboken6/VCRUNTIME140_1.dll
_internal/unicodedata.pyd
_internal/VCRUNTIME140.dll
_internal/VCRUNTIME140_1.dll
dusty.exe
```

The generated JSON contains hashes and all normal/delayed imports:
build/packaging/audit/offline-pe.json. It remains a local build artifact.
