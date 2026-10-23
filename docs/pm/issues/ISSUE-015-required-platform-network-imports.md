# ISSUE-015 - Required CPython and QtCore import prohibited Windows networking DLL

- Severity: S1
- Milestone: M5 packaging spike
- Status: Resolved
- Environment: Windows x64, Python 3.12.11, PySide6/Qt 6.9.2,
  PyInstaller 6.16.0, code 04e9b5a

## Steps to reproduce

Inspect normal and delayed PE imports of the existing bundle's candidate offline
dependencies, excluding lxml, downloader executable, socket/TLS extensions,
OpenSSL and software OpenGL. The exact five import tables, binary hashes,
source identity checks and all 114 inspected PE names are recorded in
`docs/dev/packaging-pe-preflight.md`.

## Expected

The PM requires the offline app folder to contain no PE importing ws2_32,
wsock32, wininet, winhttp or dnsapi. The PM explicitly requires stopping and
reporting if a required platform component has one of these imports.

## Actual

- `python312.dll` imports WS2_32.dll: getsockopt, send, WSAGetLastError.
- `Qt6Core.dll` imports WS2_32.dll: WSACleanup, WSAStartup, WSAAsyncSelect.
- `_multiprocessing.pyd`, `_overlapped.pyd` and `select.pyd` also import WS2_32.

All five collected files match their original installed binaries byte for byte.
These imports are not introduced by lxml or by sharing the downloader folder.
No runtime network event or data disclosure was observed. Whether particular
functions serve only local IPC has not been investigated or granted an exception.

## Evidence

`docs/dev/packaging-pe-preflight.md`: 114 PEs, five matches, including the
required Python runtime and QtCore. The earlier packaged WFP self-test recorded
zero events; that does not satisfy the requested import-free criterion.

## Root cause

The pinned upstream platform binaries themselves import the prohibited DLL.
Separating onedir folders and removing the exporter dependency do not change
those binary import tables. Earlier checks targeted Python networking imports,
named Qt Network/WebEngine DLLs and observed WFP events, so did not detect this
stricter native-import criterion.

## Fix / proposed fix

PM decision required on required-platform imports. No allowlisting, replacement,
custom rebuild or other workaround was attempted. The approved DOCX replacement,
split layout and license changes remain pending this explicit stop condition.

## Regression test added

No code change after confirmation. A future offline-folder CI check must inspect
all PE files and list every inspected file; its required-platform policy needs
the PM's decision first.

## Resolution, 2026-10-22

Earlier proposed fixes and pending statements above describe the initial stop.

The PM accepted ADR 0021: NN-2 concerns invoked code paths, with exact
filename/SHA-256/WS2_32 function pins for python312.dll and Qt6Core.dll only.
Any hash, function or additional library change fails. The approved manifest is
packaging/platform-socket-imports.json; hash/function/missing/renamed-PE/DNS
negative tests verify the contract. Optional select, _overlapped and
_multiprocessing extensions were excluded; the full source suite (159 passed,
one CI-only skip), packaged self-test and real Qt window startup/closure pass.
No code path needed these optional modules.

Run 39884809028 packaging job 120190381823 inspected 64 PEs (35 offline runtime,
29 shared native children), with zero findings beyond the exact approved pins.
The complete list is docs/dev/packaging-offline-pe-final.md and offline-pe.json.
No other processing PE imports the five prohibited network libraries. Static
source checking retains zero exceptions; the first runtime hook installs the
Python audit guard; optional socket/TLS/network Qt modules are absent; the
calibrated packaged WFP self-test records zero connection events. The separated
downloader succeeds before the offline audit window. The PM decision resolves
the required-platform stop without broadening the manifest.
