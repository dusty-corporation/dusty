# M5 report - Packaging, installer and draft release pipeline

## Summary

M5 implementation is on m5-installer; m5-packaging-spike and m6-docs remain
untouched references. Source checks pass, the ThinkPad model-free GPU probe
passed, and native page/release/WFP evidence is being completed in this autonomous
session. M5 is not accepted: PM page review and fresh standard-user VM evidence
remain outstanding. No PR, merge or published release is authorized or created.

## Owner actions for the morning

1. PM: review M5-interim-2.md and its draft screenshot bundle before requesting
   any further installer wording/layout changes.
2. Owner: enable AMD SVM, set up the Windows 11 VM, and return each numbered
   result from docs/pm/M5-checklist.md. Windows 11 Home uses VirtualBox 7.2.22;
   no host security setting will be changed by this agent.
3. Check real-device model inference and CPU retry where possible. VirtualBox
   normally cannot expose Iris Xe/RTX Vulkan and is not GPU acceptance evidence.
4. Publishing, merging and repository settings remain Owner-only. Keep test
   releases draft. No portable bundle is part of the approved release assets.

## Final gap table (updated as evidence arrives)

| SPEC M5 item | Status | Evidence / remaining work |
|---|---|---|
| Task 1: split onedir packaging, bin/resources | Done | Existing approved split payload, exact PE pins, runtime provenance, license gates and packaged GUI/WFP tests retained. |
| Task 2: installer pages, downloads and tests | Partial | Shared strings, license views, bounded real-GPU/RAM probe and failure/retry flows implemented; PM page review and clean-machine acceptance pending. |
| Task 3: upgrade preserves verified models | Partial | Existing silent lifecycle passes on earlier CI; new two-version path verifies increasing PE versions, model SHA/write-time identity with fetch blocked. Await final tag evidence. |
| Task 4: uninstall and model-size choice | Partial | Known owned files only, explicit retain/remove choice, protected transcript sentinel and source regressions; fresh VM both variants pending. |
| Task 5: gated tag draft release and assets | Partial | release.yml reuses all CI gates; approved tag validation/version map and exact asset closure tested. Two draft tag runs pending. |
| Task 6: SmartScreen README | Done | README gives unsigned explanation, More info/Run anyway, Get-FileHash and full checksum comparison. |
| Acceptance: draft CI release with artifacts | Pending | First authorized tag v0.5.0-m5.1, run 40037642063; not yet claimed successful. |
| Acceptance: SPEC 11.6 fresh VM | Owner needed | Final M5-checklist.md, standard user, all cases and expected results. |
| Acceptance: installer size | Pending | Must use final successful release inventory, not review executable size. |
| Brief: all pages light 100%/150% | Partial | Native review build and PNG-only archive gate; capture/upload in progress, Owner guest 150% check still needed. |
| Brief: Setup/probe/GUI/fetch WFP | Partial | Calibrated harness and negative parser cases added; final corrected audit counts pending. |

## Test results

- `uv run python tools/measure_coverage.py`: 257 passed, 1 expected skip,
  193.37 s; core 93.7%, export 98.6%, models 96.0%, queue 93.0%, privacy 96.2%,
  total 94.6% (953/1007 executable lines in measured packages).
- Ruff/format: pass (135 files); mypy: pass (75 sources); static network (zero
  exceptions), excluded-model-host and license checks: pass.
- Focused version/assets/generator/upload-order tests: 11 passed.
- Installer WFP negative parser checks pass for Setup original/temp image,
  GUI, engine and decoder; missing positive fetch evidence is rejected.
- CI and release run results below will be updated from actual completed runs.

## Probe evidence

Owner ThinkPad Iris Xe on 2026-10-23 returned
`{"real_gpu_found":true,"model_file_opened":false}`. Desktop diagnostic passed
under PowerShell 7 and Windows PowerShell 5.1; production guarded entry also
returned true. This proves physical GPU initialization and a 4 KiB buffer
operation, not model inference. Software devices and low RAM default Small;
low RAM is a warning, never an installation block.

## Release assets and WFP counts

Pending final gated run. Approved closure: unsigned installer,
THIRD_PARTY_NOTICES.md, versioned CycloneDX SBOM, installer-jedi-source.zip,
SHA256SUMS.txt. No portable release. The first test tag predates the corrected
Setup image matcher and is not final Setup-isolation acceptance evidence.

## Questions for the PM

1. Approve or annotate the installer page bundle. Recommendation: review the
   complete native flow, including failed GPU test versus failed CPU test.
2. Upgrade reuses verified models; hash failures are detected before download.
   The catalog does not yet show per-file damaged/re-download badges. Confirm
   whether the plain Checking/Downloading phase is sufficient, or request this
   as a page change. Recommendation: show a clear per-model repair status.

## Self-review

Reviewed new paths against SPEC 2/9/10/11.6 and accepted ADR exceptions. No new
network-capable application imports or dependencies were introduced; downloads
remain in the separate hardened fetch process. Runtime/installer exception
scopes and pinned source notices remain enforced. A failed self-test now exposes
CPU retry only after an actual Vulkan failure. Normal failure/Cancel/Finish
without cleanup now removes the active partial after child shutdown; forced
termination remains resumable. Negative WFP parser tests caught and fixed Setup
image array precedence before final acceptance. Unknown files and unsafe/corrupt
ownership metadata remain preserved rather than silently deleted. Further audit
soft spots are in docs/pm/AUDIT-NOTES.md, including integer state transitions and
full extraction timing. No fabricated failure injection or VM result is claimed.

## Deviations and remaining risks

PM-approved ADRs 0019 to 0023 and subsequent decisions supersede the original
MIT/python-docx/shared-folder/Inno-downloader assumptions. Models are not bundled.
Installer failure simulations in screenshots are review-only. Standard-user,
SmartScreen, visual scaling and physical GPU tests remain Owner evidence.
