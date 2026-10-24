# Final packaging PE and runtime provenance evidence

Local Owner CRT rebuild, 2026-10-22. Final CI evidence is linked in M5-interim-4.md.

## PE import gate

Command: `uv run python tools/check_pe_imports.py dist/Dusty/dusty --native dist/Dusty/bin`.

Result: 64 PEs checked, zero findings. Only the two exact ADR 0021 platform pins
permit their recorded WS2_32 primitives; all shared native PEs have zero exceptions.

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
bin/cpu/ggml-base.dll
bin/cpu/ggml-cpu-alderlake.dll
bin/cpu/ggml-cpu-cannonlake.dll
bin/cpu/ggml-cpu-cascadelake.dll
bin/cpu/ggml-cpu-haswell.dll
bin/cpu/ggml-cpu-icelake.dll
bin/cpu/ggml-cpu-sandybridge.dll
bin/cpu/ggml-cpu-skylakex.dll
bin/cpu/ggml-cpu-sse42.dll
bin/cpu/ggml-cpu-x64.dll
bin/cpu/ggml.dll
bin/cpu/whisper-cli.exe
bin/cpu/whisper.dll
bin/ffmpeg/ffmpeg.exe
bin/ffmpeg/ffprobe.exe
bin/vulkan/ggml-base.dll
bin/vulkan/ggml-cpu-alderlake.dll
bin/vulkan/ggml-cpu-cannonlake.dll
bin/vulkan/ggml-cpu-cascadelake.dll
bin/vulkan/ggml-cpu-haswell.dll
bin/vulkan/ggml-cpu-icelake.dll
bin/vulkan/ggml-cpu-sandybridge.dll
bin/vulkan/ggml-cpu-skylakex.dll
bin/vulkan/ggml-cpu-sse42.dll
bin/vulkan/ggml-cpu-x64.dll
bin/vulkan/ggml-vulkan.dll
bin/vulkan/ggml.dll
bin/vulkan/whisper-cli.exe
bin/vulkan/whisper.dll
```

## Collected copies replaced with Owner files

All collected and replacement files report version **14.44.35211.0**. The hashes
differ, so the collected copies were replaced unmodified from the exact Owner
14.44.35112 regular x64 folder. Packaged CPU/Vulkan self-test and GUI smoke pass.
The five replacement hashes and exact source path are in ADR 0020.

| Bundle location | Collected SHA-256 before replacement |
|---|---|
| dusty/_internal/PySide6/MSVCP140.dll | f67c2a3abe1dea72c331f04404101eafb656351b5086d51cf3e35015da59e8a9 |
| dusty/_internal/PySide6/MSVCP140_1.dll | 2ec1ff818cb225856879d2985054ff3367efceefd4843f00560e9aeee488370e |
| dusty/_internal/PySide6/MSVCP140_2.dll | 3146102c05128ba0f77cd09698a0ab4c405c5c7261ffcb51e04e4a62911f26e7 |
| dusty/_internal/PySide6/VCRUNTIME140.dll | adc02ee3166cb0d70dd02076ce67a3e8940ff2ce1a48ebf125cb807796af781b |
| dusty/_internal/PySide6/VCRUNTIME140_1.dll | 4fb3971a37f3faf2520cd873e4a25057c9f7d4a15ead8e27b0a65cf5feac3e46 |
| dusty/_internal/shiboken6/MSVCP140.dll | 5bc530e0f09b3f023cd81f28e9ae406f304f93ffcb81bde0656017fc2cf8ae7e |
| dusty/_internal/shiboken6/VCRUNTIME140.dll | bbea6c008604b7d4a24f59ca093dfddf37be085759c0f5a46a8bbe6c3c0e173b |
| dusty/_internal/shiboken6/VCRUNTIME140_1.dll | 677c07f1f00b697e82986ff393305126c0ddee184712487945d80cd35b0f0823 |
| dusty/_internal/VCRUNTIME140.dll | f18b2e10bce61f9d9b721561c165c4d2486b30fc486d62d5a6e45ed76049c252 |
| dusty/_internal/VCRUNTIME140_1.dll | fe4f518343d41037b301396397b19be2ecf6afecc2ab4b965fbf6579c092b8dd |
| dusty-fetch/_internal/VCRUNTIME140.dll | f18b2e10bce61f9d9b721561c165c4d2486b30fc486d62d5a6e45ed76049c252 |

Eleven copies, five unique names. QtCore/Gui/Widgets import msvcp140 and the _1/_2
helpers; CPython/extensions and the CRT itself import vcruntime140 and _1.
The downloader imports only vcruntime140. Normal and delayed imports are scanned.
Receipts list each importing PE and the source/replacement hashes and versions.
Other files in the Owner redist folder are not copied. No UCRT/API-set copies.
