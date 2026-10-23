# M5 Interim 1 - Packaging spike stopped on native network capability

Historical initial spike report. Subsequent PM decisions and the required-platform
import stop are recorded in M5-interim-2.md and ADRs 0019/0020.

## 1. Summary

**S0 ISSUE-014 stops implementation:** the collected lxml native extension imports
Winsock operations including socket/connect/send/recv/DNS, outside dusty_fetch.
No network event was observed, but Python's audit hook does not block native calls.
Both executables build in a shared onedir folder; the packaged self-test passed
WFP with zero events, and the local packaged GUI opens and closes successfully.
The bundle license gate also fails on ISSUE-013; no bundle binaries were uploaded
or released, no installer or PR was created, and both earlier branches are unchanged.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Windowed dusty and console dusty-fetch, shared onedir | met | Separate Analysis/PYZ/EXE, one COLLECT; PE subsystem and startup checks pass. |
| Pinned engine-v2, minimal FFmpeg, resources, no models | met | Archive hashes and each staged native member verified; only engine CLIs, DLLs and required resources copied. |
| No Qt Network/WebEngine DLLs | met | Recursive case-insensitive gate passed locally and in CI; custom hook removes unused plugin dependency chains. |
| Packaged Tiny self-test, calibrated WFP, zero events | met for exercised self-test | CI 39876227600, job 120162376525: calibration true, selftest passed, connection_events=0. |
| NN-2 for all processing components | not met | ISSUE-014: lxml.etree imports native Winsock operations; no further implementation after discovery. |
| Size, count, largest files, warnings | met | Measurements below; separate GUI/fetch warning reports preserved. |
| Draft notices and actual-content CycloneDX SBOM | met as draft | THIRD_PARTY_NOTICES.md; generated hashed inventory and schema-validated CycloneDX 1.6 in CI audit artifact. |
| Bundle license allowlist | not met | Gate returns 1 on unresolved/unapproved components, listed below without policy or dependency changes. |

## 3. What was built

- `packaging/dusty.spec`: shared `_internal`, independent embedded module archives;
  GUI guard runtime hook runs before PyInstaller's Qt hook; fetch has no guard or GUI imports.
- `bin/{cpu,vulkan,ffmpeg}` and `resources/` live beside the executables, matching
  frozen runtime paths. All nine pinned CPU variants are retained in both engine
  folders; engine benchmark/server helpers and model weights are excluded.
- `tools/build_bundle.py`, `check_bundle.py`, `inventory_bundle.py` and
  `smoke_packaged_gui.py`; bundled-content mode in `check_licenses.py`.
- Windows `packaging-spike` CI job uses the existing WFP harness with `-Bundle`.
  Tiny is fetched with packaged dusty-fetch into temporary app data before auditing.
- Reproduction/layout/upstream verification: `docs/dev/packaging-spike.md`.

## 4. Test results and measurements

Before the S0 discovery:

- Full local `uv run python tools/measure_coverage.py`: **140 passed, 1 CI-only
  skip**, 128.35 s; strict packages **94.2%** coverage.
- Focused packaging/policy tests: **22 passed**; ruff lint/format, mypy
  (**59 source files**) and all three source policy checks passed.
- Packaged fetch verify succeeded. Packaged `dusty.exe --self-test --model tiny
  --backend vulkan` exited **0**, requiring both CPU and Vulkan on the desktop.
  Redacted log: `status=done`. Packaged Qt window creation and clean closure passed.
- [CI 39876227600](https://github.com/dusty-corporation/dusty/actions/runs/39876227600):
  source checks and offline jobs green; packaged WFP passed; packaging job failed
  **only at the bundle license gate**, with audit metadata uploaded.
- Final code is `04e9b5a`. Runs
  [39876948034](https://github.com/dusty-corporation/dusty/actions/runs/39876948034)
  and [39877142894](https://github.com/dusty-corporation/dusty/actions/runs/39877142894)
  were still running at the S0 stop; no final outcome is claimed. The former's
  packaging job failed and offline passed; the latter's offline job passed.
  No additional tests or builds were launched after confirming ISSUE-014.

CI bundle from run 39876227600: **275 files, 183,441,573 bytes** (uncompressed).
Local clean bundle: **275 files, 184,061,784 bytes**, Python 3.12.11; Python/runtime
build differences account for different measurements. These are folder sizes,
not installer or compressed download sizes. The following are the **20 largest
CI files**, from its actual hashed inventory:

| File | Bytes |
|---|---:|
| bin/vulkan/ggml-vulkan.dll | 45,602,304 |
| _internal/PySide6/opengl32sw.dll | 20,639,880 |
| _internal/PySide6/Qt6Core.dll | 10,025,608 |
| _internal/PySide6/Qt6Gui.dll | 9,480,840 |
| _internal/python312.dll | 6,945,272 |
| _internal/PySide6/Qt6Widgets.dll | 6,538,376 |
| _internal/libcrypto-3.dll | 5,231,472 |
| bin/ffmpeg/ffmpeg.exe | 4,992,512 |
| bin/ffmpeg/ffprobe.exe | 4,799,488 |
| _internal/PySide6/QtWidgets.pyd | 4,693,128 |
| _internal/lxml/etree.cp312-win_amd64.pyd | 4,035,584 |
| _internal/PySide6/QtGui.pyd | 3,856,520 |
| dusty.exe | 3,655,343 |
| _internal/PySide6/QtCore.pyd | 3,163,784 |
| dusty-fetch.exe | 1,800,399 |
| _internal/lxml/objectify.cp312-win_amd64.pyd | 1,744,896 |
| _internal/ucrtbase.dll | 1,361,448 |
| _internal/base_library.zip | 1,333,717 |
| bin/cpu/ggml-cpu-cannonlake.dll | 1,216,000 |
| bin/cpu/ggml-cpu-skylakex.dll | 1,216,000 |

Surprises: the stock Qt hook pulled in QtNetwork through unused plugins;
restricting collection removed it. Mesa software OpenGL adds 20.6 MB. The lxml
hook collects unused HTML/Schematron helpers, including separately licensed or
unlicensed data, and its extension imports Winsock calls. Shared stdlib socket/TLS
files are needed by fetch; they do not grant native exporter calls an exception.

PyInstaller's GUI warning file includes optional/platform modules such as java,
_winreg, annotationlib, BeautifulSoup/bs4, html5lib, cython, cssselect,
lxml_html_clean and win32evtlog. Fetch warnings include grp, pwd, posix, resource,
_posixsubprocess, fcntl, termios, _scproxy and frozen-import bootstrap modules.
QtNetwork is explicitly excluded. No missing-DLL build warning was reported.
The smoke tests cover the exercised paths; untested optional helpers are not
claimed functional. Full warning files are retained for later review.

## 5. Deviations from SPEC

The PM authorized this packaging-only branch ahead of full M5. CURRENT_MILESTONE.md
and the earlier branches remain unchanged. Shared COLLECT is supported by the
pinned PyInstaller documentation and verified in the build. A windowed executable
has no console stdout; self-test evidence uses exit zero plus its redacted success
log. This is an audit staging folder, not a distributable release.

## 6. Issues and license findings

| Issue | Severity | Status | Finding |
|---|---|---|---|
| ISSUE-014 | S0 | Open, stopped | Native Winsock operations in collected lxml extension violate the strict processing-code boundary. |
| ISSUE-013 | S1 | Open | Redistribution license clearance is blocked; no automatic substitutions or allowlist additions. |

Unapproved/unresolved license entries: Microsoft runtime EULA terms (MSVCP,
VCRUNTIME, UCRT/API-set DLLs); lxml's disclosed bundled iconv under LGPL 2.1
(linkage/source review required); lxml Schematron transforms and ISO/skeleton
terms; libffi; Mesa/software OpenGL; remaining embedded CPython/Qt/FFmpeg native
subcomponent notices. The first CI gate listed five categories; final inventory
adds explicit Schematron attribution as the sixth. Available original copyright
and license texts are retained, but the draft is not complete release clearance.
The approved PyInstaller bootloader exception remains exactly ADR 0014; runtime
hooks/utilities are separately inventoried under Apache-2.0.

## 7. Decisions needed from PM/Owner

1. Resolve ISSUE-014 before implementation resumes. Recommend investigating a
   network-disabled build of the existing XML dependency, with native regression
   coverage and WFP during packaged Word export. A rebuild/substitution or policy
   change needs explicit PM approval; none was attempted.
2. Decide the approach to ISSUE-013's native licenses and missing notices before
   any binary distribution. The spike intentionally reports these instead of
   changing dependencies or granting exceptions.

## 8. Actions needed from the Owner

Review ISSUE-014 and ISSUE-013 with the PM and relay the approved approach.
Audit metadata is in the `packaging-spike-audit` artifact on run 39876227600;
no Owner runtime test, publication or merge is requested. Earlier branch heads:
m3-gui `fc1df2d`, m4-downloader `11354ce`, both unchanged.

## 9. Risks for later work

No installability, complete export-path isolation, legal redistribution or full
M5 acceptance claim is made. Installer work awaits the existing milestone flow.
Optional size pruning is recorded in BACKLOG.md.

## 10. Effort notes

The shared layout worked. Native transitive dependencies and hook-selected
plugins exposed the substantive privacy/licensing gaps. Implementation stopped
as soon as native network imports were confirmed.
