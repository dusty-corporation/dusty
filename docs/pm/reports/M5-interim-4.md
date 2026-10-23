# M5 Interim 4 - Packaging spike remediation complete

## 1. Summary

The split onedir bundle passes the final PE, license, GUI smoke and calibrated
WFP self-test gates. The offline runtime excludes lxml and networking extensions;
DOCX uses the standard library. Only five required Microsoft CRT filenames are
shipped, byte-identical to the Owner's exact regular VC/redist files. ISSUE-013,
ISSUE-014, ISSUE-015 and ISSUE-016 are resolved. This completes the authorized
packaging spike; installer and full M5 acceptance remain for the future brief.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Separate windowed Dusty and console fetch onedir folders | met | Two Analysis/PYZ/EXE/COLLECT chains; layout and real Qt startup/close pass. |
| Shared bin/resources, no models | met | engine-v2 CPU/Vulkan and minimal FFmpeg archive/member hashes verified; manifest, selftest.wav and icon included; weights rejected. |
| Remove runtime lxml; preserve DOCX content | met | ADR 0019; unchanged goldens plus python-docx openability, escaped Unicode and empty core-property tests; python-docx test-only. |
| Strict offline PE boundary | met | 64 PEs checked: 35 offline runtime and 29 native children. Only the exact two ADR 0021 pins; no additional networking import exceptions. |
| Optional modules and unused Qt components absent | met | _socket, _ssl, OpenSSL, select, _overlapped, _multiprocessing, QtNetwork/WebEngine, Mesa and UCRT/API-set copies rejected by gates. |
| Community CRT redistribution proof and protective terms | met | ADR 0020, Owner hash/version pins, importer/source receipts, three original PDFs and full EULA; installer acceptance requirement in M5-checklist.md. |
| Actual bundle inventory, notices, CycloneDX and license gate | met | 205 hashed files, 12 provider components, schema-valid CycloneDX 1.6; final license gate passed. |
| Packaged offline acceptance | met | CI selftest passed; zero connection events; positive blocked-event calibration passed. |
| Apache-2.0 relicense on M3, carried forward | met | Docs/metadata-only c33da50 on m3-gui; d5f828a on m4-downloader; 99e209a on this branch. |

## 3. What was built

- `dist/Dusty/dusty/` is the offline GUI runtime; `dusty-fetch/` has an independent
  console interpreter and TLS dependencies. Shared top-level bin/resources avoid
  copying native engines, while keeping TLS entirely outside Dusty's folder.
- `tools/build_bundle.py`, `check_bundle.py`, `check_pe_imports.py`,
  `stage_microsoft_runtime.py` and the actual-file inventory/license checks enforce
  the layout, exact pins and provenance. Source no-network checking has zero exceptions.
- `packaging/dusty.spec` excludes optional extensions and unused Qt modules/plugins.
  The first GUI runtime hook installs the audit guard; fetch has no hook.
- Bounded file logging avoids logging.handlers' socket transports. Built-in Python
  SHA supports model verification without offline OpenSSL/_hashlib.
- Original notices and Microsoft PDFs are retained in packaging/licenses and the
  generated bundle. The inbox is removed. The root THIRD_PARTY_NOTICES.md is the
  final CI-generated draft. The SBOM and raw inventory stay in CI audit artifacts.

Reproduction commands and upstream behavior verification:
[packaging guide](../../dev/packaging-spike.md).
Every checked PE and collected/replacement CRT comparison:
[final PE evidence](../../dev/packaging-offline-pe-final.md).

## 4. Test and measurement results

Final implementation: **f266d987e31d302dd92c38da8c3afd3eb22a82e3**.
[CI run 39884809028](https://github.com/dusty-corporation/dusty/actions/runs/39884809028):
**checks, offline and packaging-spike all green**. Packaging job: 120190381823;
source offline: 120190381966; general checks: 120190381986.
Later documentation/report commits trigger their own runs; these results refer
specifically to the implementation above.

| Command/check | Result |
|---|---|
| uv run python tools/measure_coverage.py | Local 159 passed, 1 CI-only skip, 146.33 s; CI 158 passed, 2 skips, 260.44 s. |
| CI-only real-network downloader test | 1 passed; ordinary-suite skips are the separately gated network test and unavailable CI Vulkan device. |
| Strict package coverage | 94.4% (923/978): core 93.7%, export 98.6%, models 94.4%, queue 93.0%, privacy 96.2%. |
| ruff check / format --check | Passed; 105 files formatted. |
| mypy | Passed; 61 source files. |
| Three source policy checks | All passed, no network exceptions. |
| Packaged CPU/Vulkan self-test on desktop | Exit 0, redacted status=done after Owner CRT replacement. |
| Packaged GUI smoke and layout gate | Passed locally and in CI. |
| PE and license gates | 64 PEs, zero findings; bundle license check passed. |
| Packaged WFP CI | selftest=passed, connection_events=0, calibration_blocked_event=true. |

Download the audit evidence (no bundle binaries uploaded):

```powershell
gh run download 39884809028 --name packaging-spike-audit --dir build/m5-final-audit-39884809028
```

`packaging/audit/` contains inventory.json, sbom.cdx.json, THIRD_PARTY_NOTICES.md,
crt-provenance.json, offline-pe.json, license-findings.txt, measurements.md and
both PyInstaller warning lists. The artifact also contains the WFP summary and build log.

**Uncompressed bundle: 161,909,001 bytes (154.4 MiB), 205 files.** Models excluded.
Twenty largest files:

| File | Bytes |
|---|---:|
| bin/vulkan/ggml-vulkan.dll | 45602304 |
| dusty/_internal/PySide6/Qt6Core.dll | 10025608 |
| dusty/_internal/PySide6/Qt6Gui.dll | 9480840 |
| dusty/_internal/python312.dll | 6974464 |
| dusty-fetch/_internal/python312.dll | 6974464 |
| dusty/_internal/PySide6/Qt6Widgets.dll | 6538376 |
| dusty-fetch/_internal/libcrypto-3-x64.dll | 5932544 |
| bin/ffmpeg/ffmpeg.exe | 4992512 |
| bin/ffmpeg/ffprobe.exe | 4799488 |
| dusty/_internal/PySide6/QtWidgets.pyd | 4693128 |
| dusty/_internal/PySide6/QtGui.pyd | 3856520 |
| dusty/_internal/PySide6/QtCore.pyd | 3163784 |
| dusty/dusty.exe | 1827440 |
| dusty-fetch/dusty-fetch.exe | 1802907 |
| dusty/_internal/base_library.zip | 1334834 |
| dusty-fetch/_internal/base_library.zip | 1334834 |
| bin/cpu/ggml-cpu-cannonlake.dll | 1216000 |
| bin/cpu/ggml-cpu-skylakex.dll | 1216000 |
| bin/vulkan/ggml-cpu-cannonlake.dll | 1216000 |
| bin/vulkan/ggml-cpu-skylakex.dll | 1216000 |

### Microsoft runtime provenance

Source: `C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Redist\MSVC\14.44.35112\x64\Microsoft.VC143.CRT`.
Owner installed Community 17.14 on 2026-10-22 under individual section 1.a.
The v143 alias and spectre folder are not selected. All five file versions are
**14.44.35211.0**: msvcp140.dll, msvcp140_1.dll, msvcp140_2.dll,
vcruntime140.dll and vcruntime140_1.dll. Their complete Owner hashes, three
source-document hashes, legal basis (Community section 4 and redistribution list),
URLs and retrieval date are in [ADR 0020](../../adr/0020-visual-cpp-runtime-redistribution-exception.md).

Eleven loader-local copies represent those five names. Normal/delay imports
require all five in the offline Qt runtime and only vcruntime140 in fetch.
No concrt, vccorlib, atomic_wait, codecvt_ids or threads CRT is copied.
Collected wheel/runtime copies had the same reported version but different
hashes, so all were replaced with the Owner-pinned bytes. Local and CI source
copies match those pins; the receipt records every original hash/version,
replacement and importing PE. Compatibility gates passed after replacement.

### Warnings and surprises

PyInstaller lists excluded socket/select/_hashlib/QtNetwork imports and conditional
Unix/macOS/Java modules (pwd, grp, posix, fcntl, termios, _scproxy, java). These
were retained in the warning artifacts; no missing module broke the exercised
Windows paths. The largest file is the 45.6 MB Vulkan backend; separate Python
runtimes intentionally duplicate python312.dll and the standard-library archive.
The retained FFmpeg cross-build configuration includes Wine initialization messages;
the native runtime and verified decoding checks pass. CI warns that pinned Node 20
actions are forced onto Node 24; refreshing those pins is in BACKLOG.md.

## 5. Approved deviations from SPEC

ADR 0019 replaces python-docx with stdlib DOCX at runtime. ADR 0020 narrowly
approves required Community-licensed Microsoft CRT redistribution and protective
EULA terms. ADR 0021 permits only two exact platform socket-primitive import pins,
backed by source/packaged/runtime/WFP layers. ADR 0012 now records Apache-2.0
instead of MIT, per the sole contributor Owner's patent-grant decision. PyInstaller's
exact bootloader exception remains governed by ADR 0014.

## 6. Issues

| Issue | Status | Resolution evidence |
|---|---|---|
| ISSUE-013, license findings | Resolved | Unneeded XML/Mesa components removed; original notices, CRT evidence and final license gate passed. |
| ISSUE-014, native lxml networking S0 | Resolved | Runtime dependency removed; DOCX regressions, offline PE gate and packaged WFP passed. |
| ISSUE-015, required platform imports | Resolved | Exact PM-approved pins; optional modules excluded; full suite, GUI and packaged gates passed. |
| ISSUE-016, Microsoft document HTTP 403 | Resolved | Owner supplied original PDFs; hashes/protective terms pass the final gate; no rejected-download workaround. |

## 7. Decisions needed from PM/Owner

None for this authorized spike.

## 8. Actions needed from the Owner

None to complete this spike. The future installer must present the runtime EULA
alongside Dusty's Apache LICENSE/NOTICE and require acceptance; the checklist
records this. The Owner's current M3 eight-check re-test remains the active GUI
follow-up; the stale 20-step request is not renewed. No installer or main PR was created.

## 9. Risks for the next milestone

Python/Qt platform hash or WS2_32 function changes require PM review. CRT updates
must retain exact Owner provenance, import necessity and compatibility evidence.
This first draft SBOM covers actual files/providers and embedded modules; it does
not claim to reverse-engineer every upstream statically linked source unit.
Actual unknown providers still fail; no generic unknown-component waiver was added.
A possible MSVC-free MinGW distribution and enterprise proxy support are backlog items.
Full installer, installed-app and fresh-machine acceptance remain unimplemented.

## 10. Effort notes

The shared runtime prototype exposed native Winsock imports and licensing gaps.
Separate runtimes, dependency removal and exact platform/CRT provenance made the
boundary verifiable. All implementation stays on m5-packaging-spike; only the
explicitly requested documentation/metadata commits touched the earlier branches.
Work stops at this report.
