# M5 interim 1 - Phase 1 gap analysis

Phase 1 only. Created m5-installer from main 87a1304, archived M4, and committed
the Owner's M5 brief unchanged (f84dbd2). Ported M5 in 00ec6a4/c3438f1 and
pushed. Final M4 fixes remain; reference branches m5-packaging-spike and m6-docs
are untouched. No Phase 2 implementation, test tag, draft release or PR created.
Historical spike report 1 is M5-packaging-spike-interim-1.md; reports 2 to 7
remain historical evidence, not completion claims for this branch.

## 1. Gap table

Done requires current-branch acceptance evidence. Earlier spike CI is identified
as historical rather than substituted for the new branch's checks.

| SPEC M5 item | Status | Evidence and remaining gap |
| --- | --- | --- |
| Task 1: PyInstaller and native/resources payload | partial | Ported packaging/dusty.spec, separate onedir folders, exclusions, exact PE/CRT/license gates and GUI/WFP tests. Prior packaged CI 39998318413 green; fresh port CI 40011781091 pending. |
| Task 2: generated per-user installer | partial | installer/generate_iss.py and dusty.iss.template compile in the spike. Missing real Vulkan pre-selection, full shared catalog wording/GB display, notices reachable from license page, inline consent, Finish without a model, plain failure/retry flow and normal-cancel partial cleanup. Current self-test checks only the first selected model. |
| Task 3: upgrade | partial | tools/test_installer.ps1 previously passed verified reuse with downloader blocked and unchanged hashes/mtimes. Needs damaged-model UI and upgrade between two different tagged builds. |
| Task 4: uninstall | partial | Tested recognized-data cleanup, both model choices and unchanged output sentinel. Checkbox lacks real GB size; final leftover accounting and fresh standard-user VM evidence missing. Unknown/protected data must still be preserved safely. |
| Task 5: tagged release pipeline | missing | No release.yml. Existing ci.yml builds audited CI artifacts only; inventory/notices/CycloneDX and ISSUE-019 upload regression are ported. Need tag/version wiring, all-asset checksums, installed gates and draft-release upload after every gate. |
| Task 6: SmartScreen README | partial | Hash command and More info / Run anyway exist. Remove obsolete M0/license-block text and finish the plain unsigned/free/open-source explanation. |
| Acceptance: tagged CI draft with all artifacts | missing | No M5 test tag or draft app release yet. |
| Acceptance: SPEC 11.6 fresh Windows 11 standard-user VM | missing | Existing M5-checklist.md is a draft; CI silent lifecycle is not fresh-VM acceptance. Add VM setup, expected results, tampering/interruption and two-build upgrade. Owner executes. |
| Acceptance: installer size reported | partial | Historical spike: 34,618,916 bytes (CI 39985711346); final M5 size and all release-asset hashes not measured yet. |
| Brief: installer download WFP | missing | Source/packaged GUI 0, fetch allowed 4/blocked 0 and installed processing 0 are historical passes. Setup's own download-phase events were not measured. Add calibrated installer 0 / GUI 0 / allowed fetch attribution. |
| Brief: screenshots and ZIP hygiene | missing | No final installer page captures at 100%/150%; no enforced PNG/README-only archive gate. Existing final M4 ZIP was restricted manually; render output also contains state files. |

## 2. Questions for PM, with recommendations

1. **Probe before installation:** approve temporarily extracting the existing
   split payload and running a guarded, isolated model-free Dusty probe before
   Choose model? **Recommend yes**, bounded timeout, raw driver output discarded,
   Small on failure/timeout. No new native binary. This preserves page order;
   moving Choose model after installation is the alternative.
2. **RAM rule:** the catalog recommends 8 GB for every model, while the brief
   makes Vulkan the main default criterion. **Recommend Turbo when Vulkan works
   and RAM meets that catalog minimum; otherwise Small, with a warning below
   the minimum, not an installation block.** Surface/ThinkPad remain Turbo.
3. **Finish without a model after self-test failure:** downloaded files can be
   hash-valid yet fail inference. Keep them or discard them? **Recommend keep
   verified files and all pre-existing models, clear the failed default selection,
   and show the failed-test warning plus existing Choose model in Options state.**
   The no-model recommendation prompt applies when none exists. This needs PM
   approval because the brief requests that prompt for every Finish-without-model
   path. Never silently delete an existing model or call a failed test successful.
4. **Multiple selections:** test every selected transcription model, or only the
   first/default as in the spike? **Recommend every selected model on CPU and
   Auto**, plus VAD verification, before claiming full setup success. Retry can
   use CPU after a Vulkan failure, with the actual outcome stated plainly.
5. **Interrupted Setup policy:** normal Cancel removes its partial; what about
   forced Setup termination? **Recommend the same M4 rule:** Job Object kills
   fetch, recent partial resumes with full verification, older-than-seven-day
   partials expire at the next installer/app startup. Verified models stay.
6. **Draft version/assets:** current app metadata is 0.0.1. **Recommend Python package version
   0.5.0.devN, displayed release/tag v0.5.0-m5.N and numeric installer version
   0.5.0.N**, with two successive builds for upgrade acceptance. Release assets: unsigned x64 installer,
   THIRD_PARTY_NOTICES.md, dusty-<version>-sbom.json, installer-jedi-source.zip,
   and SHA256SUMS.txt covering the other assets. No portable bundle unless asked.

Existing ADR 0014/0019 to 0023 approvals are retained; no license exception or
new dependency is requested. Owner action after Phase 2: run the final roughly
45-minute clean Windows 11 VM checklist; publication and merging remain Owner-only.

## 3. Vulkan pre-selection answer

**Yes through the already bundled engine DLLs, not the current CLI flags.**
The CLI returns 3 for a missing model before loading backends. Using the pinned
C API, load ggml-vulkan.dll via ggml.dll, enumerate its registry through
ggml-base.dll, initialize a device, allocate/clear a 4 KiB GPU buffer and synchronize.
Desktop verification passed without opening a model: one device, one initialized
backend, successful buffer operation, exit 0 in 0.468 s. DLL bytes match the
engine-v2 archive pin. This proves initialization, not Turbo inference or RAM
sufficiency; the post-download self-test remains mandatory. The new probe still
needs ThinkPad confirmation and WFP coverage. Exact API/export details and limits:
[developer evidence](../../dev/m5-model-free-vulkan-check.md).

## 4. Verification

Port CI: [40011781091](https://github.com/dusty-corporation/dusty/actions/runs/40011781091),
source checks, offline and upload-regression jobs passed; packaging/installed
validation is still running. Ruff/format (127 files), mypy (70 sources) and all
three source policy checks pass. Local serial rerun: **224 passed, 1 expected
skip, 94.6% coverage**, in 209.78 seconds.
Initial local run: 221 passed, 3 failed, 1 skipped, 94.6% coverage. Failures were
license-byte checks after patch application wrote CRLF notice copies; restored
exact committed LF bytes without changing pins, policy or tests. Not a new
license decision. No installer ran against the Owner profile.

## 5. Phase 2 plan and estimate

After PM replies: (1) installer UX/probe/failure/cancellation and regression tests;
(2) calibrated Setup download audit, packaging/license/installed gates and two
allowed test-tag draft builds; (3) page screenshots/archive gate, README/checklist,
asset hashes/size and final report. Commit/push at each checkpoint.
Estimate **8 to 12 hours of engineering and CI**, plus Owner VM time/downloads;
not a promised completion time. No PR until PM accepts the final M5 report.
**Stopped at Phase 1. Phase 2 awaits the PM's reply.**
