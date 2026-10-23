# Packaging spike (PyInstaller 6.16.0)

## Verified layout

The pinned [spec documentation](https://pyinstaller.org/en/v6.16.0/spec-files.html#making-a-one-folder-app)
permits multiple EXE objects in a shared COLLECT for onedir applications.
`packaging/dusty.spec` uses separate Analysis/PYZ/EXE objects, then one COLLECT.
MERGE is unnecessary for this onedir layout. Qt DLLs are replaceable files.

```text
Dusty/
  dusty.exe                 Windows GUI subsystem, no console
  dusty-fetch.exe           Windows console subsystem, separate interpreter
  _internal/                shared Python, Qt and exporter dependencies
  bin/cpu/                  engine-v2 CLI, ggml and all CPU variant DLLs
  bin/vulkan/               engine-v2 CLI, CPU variants and Vulkan DLL
  bin/ffmpeg/               pinned network-disabled ffmpeg and ffprobe
  resources/models.json
  resources/selftest.wav
  resources/icons/dusty.ico
  licenses/                 available original texts added by inventory step
```

`bin` and `resources` are staged beside the executable because frozen
`resolve_paths()` uses that directory. No weights, VAD weights, whisper-bench,
servers or download helper scripts are copied. Archive SHA-256 pins and every
copied native member are checked against engine-v2. Models stay in a separate
repo-local test profile during verification, never in the application folder.
Duplicate shared destinations with different bytes fail the spec build.

The [runtime hook order](https://pyinstaller.org/en/v6.16.0/when-things-go-wrong.html#changing-runtime-behavior)
and the local 6.16.0 build log confirm the user hook precedes standard hooks.
Dusty's hook installs the audit guard before the Qt runtime hook. The fetch
Analysis excludes Dusty and does not install that hook. Standard-library socket
and TLS files are present in the shared folder for the separate downloader;
Dusty's irreversible audit hook still blocks socket operations.

## Qt collection

Python module exclusions alone were insufficient: the stock QtGui hook collected
unused PDF and virtual-keyboard plugins, pulling in QML and Qt6Network.dll.
The custom QtGui hook restricts collection before native dependency analysis to
qwindows, qoffscreen, qminimal and qico. Widgets use Fusion styling and native
Windows input. Only QtCore, QtGui and QtWidgets Python modules are retained.
`check_bundle.py` rejects case-insensitive nested Qt6Network.dll and
Qt6WebEngine*.dll, model weights, missing resources and incorrect PE subsystems.
It also checks the guard is the first GUI script and is absent from fetch.

## Reproduce

```powershell
uv sync --locked
uv run python tools/fetch_dev_binaries.py
uv run python tools/build_bundle.py
uv run python tools/check_bundle.py dist/Dusty
uv run python -m tools.inventory_bundle dist/Dusty
uv run python tools/check_licenses.py --bundle dist/Dusty --inventory build/packaging/audit/inventory.json
```

The last command intentionally fails on unresolved or unapproved components.
It never grants new license exceptions. The normal lockfile check is unchanged.
Generated inventory, CycloneDX 1.6 SBOM (validated with pinned CycloneDX tooling),
draft notices and measurements are in `build/packaging/audit`. They describe the
actual collected files with hashes, native member pins and embedded module origins,
not every installed development distribution. Original available license texts
are copied into the audit bundle; missing/transitive texts remain findings.

## Packaged WFP test

On disposable Windows CI only:

```powershell
./tools/test_network_isolation.ps1 -Bundle dist/Dusty
```

The packaged console downloader fetches Tiny into a temporary LOCALAPPDATA/Dusty/models
before firewall rules or the audit window. The existing harness then calibrates
Windows Filtering Platform event 5157 with its blocked positive control, blocks
the packaged GUI, both engine CLIs and FFmpeg/ffprobe, runs the real windowed
`dusty.exe --self-test --backend auto --model tiny`, and requires zero 5156/5157
events. Success requires exit zero and the redacted `status=done` log. A windowed
PyInstaller executable has no stdout console, so stdout is not used as evidence.
CPU runs on CI; Vulkan runs if a usable adapter exists. No GPU availability is
claimed from this test alone. Existing source self-test/batch/GUI audit remains.
Rules, audit policy and environment are restored in finally blocks.

CI uploads audit metadata, warning logs and WFP summaries only. It never uploads
this unapproved experimental bundle as an artifact or release. No installer is built.

## Licensing findings to review

- Microsoft runtime DLLs (MSVCP/VCRUNTIME, UCRT/API-set DLLs on the local uv Python
  build): [Microsoft's redistribution terms](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files)
  are not on SPEC 10.2's open-source allowlist.
- lxml wheel LICENSES.txt discloses bundled iconv under LGPL 2.1. This requires
  linkage/source review; static LGPL is not permitted by the current rule.
- Qt's opengl32sw.dll, libffi and native subcomponents need exact versions,
  source-level license/copyright reconciliation and complete notices.
- PyInstaller bootloader exception is approved by ADR 0014; its original COPYING
  text is retained. Runtime hooks and runtime utility helpers are Apache-2.0
  according to the installed source headers, separately inventoried.

Do not treat Python/Qt package metadata or a draft SBOM as a complete native audit.
No dependencies or binary selection are changed to hide these findings.
