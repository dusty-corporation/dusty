# Packaging spike (PyInstaller 6.16.0)

## Layout and runtime boundary

The [pinned spec documentation](https://pyinstaller.org/en/v6.16.0/spec-files.html)
and installed COLLECT implementation support separate onedir applications.
Two independent Analysis/PYZ/EXE/COLLECT chains use `--distpath dist/Dusty`:

```text
Dusty/
  dusty/dusty.exe                 windowed GUI
  dusty/_internal/               offline Python and replaceable Qt DLLs
  dusty-fetch/dusty-fetch.exe     console downloader, separate interpreter
  dusty-fetch/_internal/         independent socket/TLS runtime
  bin/{cpu,vulkan,ffmpeg}/        pinned native children, shared by layout
  resources/{models.json,selftest.wav,icons/}
  licenses/                      original license texts and Microsoft PDFs
  THIRD_PARTY_NOTICES.md          component table and full protective EULA
```

Frozen runtime paths resolve shared bin/resources from the executable folder's
parent. Models remain outside the bundle. Staging verifies all three engine-v2
archive hashes and copied native member bytes, excludes model weights and native
helper programs, and retains all nine approved CPU variants in each engine folder.
No installer, main PR or binary release is created by the spike.

## Offline defenses (ADR 0021)

The first GUI user runtime hook installs the irreversible audit guard before
PyInstaller's Qt runtime hook. Fetch excludes Dusty and has no guard hook.
The GUI excludes socket/ssl, _socket/_ssl/_hashlib, select, _overlapped,
_multiprocessing, asyncio, multiprocessing, dusty_fetch, docx and lxml.
CPython's built-in SHA implementation preserves hash verification without
OpenSSL. Bounded file logging avoids logging.handlers' eager socket transports.

Only Python 3.12.11 build 20250902 and QtCore 6.9.2 are permitted Winsock imports,
with the exact two hashes and function sets in platform-socket-imports.json.
Every MZ-signature PE is checked, including files with unusual extensions;
normal and delayed imports from ws2_32/wsock32/wininet/winhttp/dnsapi are blocked
for all other PEs. Shared native children are scanned without exceptions.
The gate prints every checked PE and retains hashes/imports in offline-pe.json.
Missing platform files, changed hashes or changed functions fail.

The stock QtGui hook pulled Network/QML through unused plugins. The custom hook
retains native/offscreen/minimal platform and ICO support; QtCore/Gui/Widgets
are the only Python Qt modules. The PySide6 base hook omits optional Mesa/ANGLE
renderers. Raster widget startup/closure is tested in the packaged GUI smoke.
Layout checks reject prohibited networking/TLS/optional extension files, Mesa,
Windows UCRT/API-set copies, model weights and wrong PE console/GUI subsystems.
The Python source static check retains zero exceptions.

## Microsoft redistribution (ADR 0020)

The maintainer holds VS 2022 Community under individual-license section 1.a.
Community section 4.a.i plus the Visual C++ Runtime Files redistribution list
are the redistribution basis, not the runtime end-user EULA alone. Only required
vcruntime140*.dll/msvcp140*.dll are copied unmodified from release x64
Microsoft.VC143.CRT inside VC/redist. Debug/onecore and all other Microsoft PEs
are rejected. CRT provenance records every target/source/hash, and the license
gate rechecks byte identity against the live source files.

The default source is installed VS 2022, found with vswhere. To use the maintainer's
installation, set DUSTY_VC_REDIST to its VC/redist folder. Both local and CI
builds select only MSVC/14.44.35112/x64/Microsoft.VC143.CRT and require exact
byte identity with packaging/microsoft-runtime.json (maintainer installation).
The v143 alias and spectre copies are never selected. Normal and delayed PE
imports determine required CRT filenames within each executable family; unused
CRT names are pruned. Receipts include importing PEs and the collected hash and
version before replacement, making wheel/runner differences visible.
The three unchanged maintainer PDFs, complete extracted texts, URLs, retrieval date
and hashes are in packaging/licenses/microsoft. The future installer MUST
present the runtime EULA alongside Dusty's Apache-2.0 terms and require agreement
under section 4.b. The installer acceptance gates check this. Terms are scoped to Microsoft code;
Qt's LGPL replacement/debugging rights are preserved.

## Reproduce

```powershell
uv python install 3.12.11
uv sync --locked --python 3.12.11
uv run python tools/fetch_dev_binaries.py
uv run python -m tools.build_bundle
uv run python tools/check_bundle.py dist/Dusty
uv run python tools/check_pe_imports.py dist/Dusty/dusty --native dist/Dusty/bin
uv run python tools/smoke_packaged_gui.py dist/Dusty
uv run python -m tools.inventory_bundle dist/Dusty
uv run python tools/check_licenses.py --bundle dist/Dusty --inventory build/packaging/audit/inventory.json
```

uv 0.8.18 selects the approved managed Python build; the PE hash gate is the
final check, so a different binary cannot silently pass. Build requires the
release VC/redist source; it never downloads an unverified replacement.

Inventory covers actual files/providers and embedded modules per executable,
not the development environment. It includes libffi's MIT notice, Qt LGPL/GPL
reference texts, FFmpeg source/configuration, PyInstaller's approved bootloader
exception and Apache runtime-hook notices. Test-only XML providers are rejected.
The earlier generic native-review placeholder was a scope warning, not a detected
component; actual unknown file providers remain explicit failing findings.
This is a component/provider SBOM and draft notices, not a claim to have
reverse-engineered every statically linked source unit in upstream libraries.
CycloneDX 1.6 is schema-validated. Every file has a hash/component attribution;
missing, added, modified or unattributed files fail the bundle license gate.
Microsoft's exception additionally requires all original document hashes,
complete protective terms in notices and exact release-source provenance.
Separate warn-gui.txt and warn-fetch.txt preserve both PyInstaller analyses.

## Packaged WFP acceptance

On disposable administrator Windows CI only:

```powershell
./tools/test_network_isolation.ps1 -Bundle dist/Dusty
```

Packaged fetch downloads Tiny into temporary LOCALAPPDATA/Dusty/models before
the firewall/audit window. A positive blocked-connection control must produce
WFP event 5157. The harness blocks the GUI, both engine CLIs and FFmpeg/ffprobe,
runs the real windowed --self-test --backend auto --model tiny, and requires zero
5156/5157 processing events plus exit zero and the redacted status=done log.
Windowed Python has no console stdout, so stdout is not used as the success gate.
CPU is exercised; usable Vulkan runs too, without assuming GPU availability on CI.
Existing source self-test/batch/GUI WFP acceptance also remains enabled.
Rules, audit policy and environment are restored in finally blocks.
CI uploads audit metadata, notices/SBOM, measurements and warnings. No installer
or bundle binaries are published by this workflow.
