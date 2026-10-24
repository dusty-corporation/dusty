# M5 offline dependency PE preflight

Date: 2026-10-22. Existing experimental local bundle at code 04e9b5a.

This is a read-only candidate-dependency preflight, before the approved split layout
or DOCX replacement is implemented. It is not a claim that a new offline bundle passed.
lxml, dusty-fetch.exe, _socket, _ssl, OpenSSL and software OpenGL were excluded from
this candidate scan. Existing UCRT/API-set and unused helper files are still listed
because they were inspected, although the PM requires their removal from a new build.

Normal and delayed imports were compared case-insensitively against ws2_32.dll,
wsock32.dll, wininet.dll, winhttp.dll and dnsapi.dll.

## Hits

| PE file | Imported DLL | Functions | SHA-256 | Matches original installed binary |
|---|---|---|---|---|
| _internal/_multiprocessing.pyd | WS2_32.dll | recv, send, closesocket, WSAGetLastError | a15837be2706cee8864bc86dd1e756617c957a8f7f4353fcd17dd59eb73ea4bf | True |
| _internal/_overlapped.pyd | WS2_32.dll | closesocket, WSASend, ntohl, WSAIoctl, WSASendTo, WSAConnect, socket, ntohs, WSAStringToAddressW, WSARecv, WSARecvFrom, inet_ntop, htons, bind, WSAGetLastError | 6c756bc27b4244d5682c9045f356bc836f9479be38141763bf5d542b2f0db0ad | True |
| _internal/PySide6/Qt6Core.dll | WS2_32.dll | WSACleanup, WSAStartup, WSAAsyncSelect | 393833b9d4deef7abd8bf475d38c15126c2f016058b03dd5eb27fa18198cfa75 | True |
| _internal/python312.dll | WS2_32.dll | getsockopt, send, WSAGetLastError | e1643b99a6f7b69410bd941f2bcd03614baa8f4d3eaf6fbe9a29929f5a3bf79e | True |
| _internal/select.pyd | WS2_32.dll | select, __WSAFDIsSet, WSAGetLastError | 279ac7ea8e3058179e5fa51eb5801036af8becc1aefe0b2d43b8d54bffaeeae3 | True |

## Every PE checked

114 PE files were checked. Five matched the prohibited import set.

```text
_internal/_asyncio.pyd
_internal/_bz2.pyd
_internal/_ctypes.pyd
_internal/_decimal.pyd
_internal/_hashlib.pyd
_internal/_lzma.pyd
_internal/_multiprocessing.pyd
_internal/_overlapped.pyd
_internal/_queue.pyd
_internal/_uuid.pyd
_internal/_wmi.pyd
_internal/api-ms-win-core-console-l1-1-0.dll
_internal/api-ms-win-core-datetime-l1-1-0.dll
_internal/api-ms-win-core-debug-l1-1-0.dll
_internal/api-ms-win-core-errorhandling-l1-1-0.dll
_internal/api-ms-win-core-fibers-l1-1-0.dll
_internal/api-ms-win-core-fibers-l1-1-1.dll
_internal/api-ms-win-core-file-l1-1-0.dll
_internal/api-ms-win-core-file-l1-2-0.dll
_internal/api-ms-win-core-file-l2-1-0.dll
_internal/api-ms-win-core-handle-l1-1-0.dll
_internal/api-ms-win-core-heap-l1-1-0.dll
_internal/api-ms-win-core-interlocked-l1-1-0.dll
_internal/api-ms-win-core-kernel32-legacy-l1-1-1.dll
_internal/api-ms-win-core-libraryloader-l1-1-0.dll
_internal/api-ms-win-core-localization-l1-2-0.dll
_internal/api-ms-win-core-memory-l1-1-0.dll
_internal/api-ms-win-core-namedpipe-l1-1-0.dll
_internal/api-ms-win-core-processenvironment-l1-1-0.dll
_internal/api-ms-win-core-processthreads-l1-1-0.dll
_internal/api-ms-win-core-processthreads-l1-1-1.dll
_internal/api-ms-win-core-profile-l1-1-0.dll
_internal/api-ms-win-core-rtlsupport-l1-1-0.dll
_internal/api-ms-win-core-string-l1-1-0.dll
_internal/api-ms-win-core-synch-l1-1-0.dll
_internal/api-ms-win-core-synch-l1-2-0.dll
_internal/api-ms-win-core-sysinfo-l1-1-0.dll
_internal/api-ms-win-core-sysinfo-l1-2-0.dll
_internal/api-ms-win-core-timezone-l1-1-0.dll
_internal/api-ms-win-core-util-l1-1-0.dll
_internal/api-ms-win-crt-conio-l1-1-0.dll
_internal/api-ms-win-crt-convert-l1-1-0.dll
_internal/api-ms-win-crt-environment-l1-1-0.dll
_internal/api-ms-win-crt-filesystem-l1-1-0.dll
_internal/api-ms-win-crt-heap-l1-1-0.dll
_internal/api-ms-win-crt-locale-l1-1-0.dll
_internal/api-ms-win-crt-math-l1-1-0.dll
_internal/api-ms-win-crt-process-l1-1-0.dll
_internal/api-ms-win-crt-runtime-l1-1-0.dll
_internal/api-ms-win-crt-stdio-l1-1-0.dll
_internal/api-ms-win-crt-string-l1-1-0.dll
_internal/api-ms-win-crt-time-l1-1-0.dll
_internal/api-ms-win-crt-utility-l1-1-0.dll
_internal/libffi-8.dll
_internal/pyexpat.pyd
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
_internal/select.pyd
_internal/shiboken6/MSVCP140.dll
_internal/shiboken6/Shiboken.pyd
_internal/shiboken6/shiboken6.abi3.dll
_internal/shiboken6/VCRUNTIME140.dll
_internal/shiboken6/VCRUNTIME140_1.dll
_internal/ucrtbase.dll
_internal/unicodedata.pyd
_internal/VCRUNTIME140.dll
_internal/VCRUNTIME140_1.dll
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
dusty.exe
```

No exceptions or runtime changes were made after these findings. The PM explicitly
required stopping if a required platform component imports a prohibited DLL.
See ISSUE-015 and M5-interim-2.md.
