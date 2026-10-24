# M5 report - Packaging, installer and draft release pipeline

## ISSUE-020 repair in progress

PM approved the ownership repair on 2026-10-23. It is pushed with the original
three regressions enabled, expanded reparse/destination/unknown-content tests,
and a complete delete-call sweep in [M5-interim-9.md](M5-interim-9.md). Final
source, packaged, installed WFP and uninstall gates are running. Keep affected
historical drafts unpublished and postpone VM acceptance until a repaired build
is identified below. No Owner files were inspected or changed.

## Summary

M5 implementation is on m5-installer; m5-packaging-spike and m6-docs remain
untouched references, and updated guides are pushed on m6-docs-v2. The first
successful draft release and calibrated Setup/probe/download audit passed;
the second-version upgrade and final native page evidence are being collected.
M5 is not accepted: ISSUE-020 repair, PM page review and fresh standard-user VM evidence
remain outstanding. No PR, merge or published release is authorized or created.

## Owner actions for the morning

0. The ownership repair is approved. Keep historical M5 drafts unpublished and
   wait for the repaired build identified in this report before VM acceptance. If any real files
   are under Dusty's app-managed work folders, back them up manually before
   launching/updating affected builds; the agent has not inspected the real profile.
1. PM page decisions have arrived. Their implementation follows green repair
   gates; a new page-review screenshot bundle will replace the earlier review.
2. Owner: AMD SVM is now enabled (2026-10-23). Set up the VM and return each numbered
   result from docs/pm/M5-checklist.md. Windows 11 Home uses VirtualBox 7.2.22;
   no host security setting will be changed by this agent.
3. Check real-device model inference and CPU retry where possible. VirtualBox
   normally cannot expose Iris Xe/RTX Vulkan and is not GPU acceptance evidence.
4. Publishing, merging and repository settings remain Owner-only. Keep test
   releases draft. No portable bundle is part of the approved release assets.

## Final gap table (updated as evidence arrives)

Every item is release-blocked by ISSUE-020. Done below refers only to historical
implementation/gate evidence, not milestone acceptance. The new NN-7 regression
is **not met**, and the final receipt-based release run was stopped.

| SPEC M5 item | Status | Evidence / remaining work |
|---|---|---|
| Task 1: split onedir packaging, bin/resources | Done | Existing approved split payload, exact PE pins, runtime provenance, license gates and packaged GUI/WFP tests retained. |
| Task 2: installer pages, downloads and tests | Partial | Shared strings, license views, bounded real-GPU/RAM probe and failure/retry flows implemented; PM page review and clean-machine acceptance pending. |
| Task 3: upgrade preserves verified models | Partial | Existing silent lifecycle passes on earlier CI; new two-version path verifies increasing PE versions, model SHA/write-time identity with fetch blocked. Await final tag evidence. |
| Task 4: uninstall and model-size choice | Partial | Known owned files only, explicit retain/remove choice, protected transcript sentinel and source regressions; fresh VM both variants pending. |
| Task 5: gated tag draft release and assets | Partial | release.yml reuses all CI gates; approved tag validation/version map and exact asset closure tested. Two draft tag runs pending. |
| Task 6: SmartScreen README | Done | README gives unsigned explanation, More info/Run anyway, Get-FileHash and full checksum comparison. |
| Acceptance: draft CI release with artifacts | Done | v0.5.0-m5.2, run 40038534920, all gates and draft creation passed; five assets. |
| Acceptance: SPEC 11.6 fresh VM | Owner needed | Final M5-checklist.md, standard user, all cases and expected results. |
| Acceptance: installer size | Done | First successful .2 installer: 34,670,296 bytes (34.67 MB); final .3 size will be recorded separately. |
| Brief: all pages light 100%/150% | Partial | 21 native light PNGs plus README uploaded; archive gate passes. Effective 96 DPI with host bitmap scaling disclosed; genuine 100%/150% VM display checks remain Owner actions. |
| Brief: Setup/probe/GUI/fetch WFP | Done | .2 corrected audit: Setup 0, GUI/probe 0, native 0, fetch allowed 4, blocked 0; calibrated control and negative parser pass. |

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

[Draft v0.5.0-m5.2](https://github.com/dusty-corporation/dusty/releases/tag/untagged-717061651366b4239b75),
[CI 40038534920](https://github.com/dusty-corporation/dusty/actions/runs/40038534920):
all gates passed. Installer 34,670,296 bytes. No portable release asset.

| Asset | SHA-256 |
|---|---|
| Dusty-0.5.0-m5.2-draft-unsigned.exe | eb4c1efe73e4d11ddad09d6aa3ab887cc678ef7f45a1793214aa6fe57e08d8bb |
| THIRD_PARTY_NOTICES.md | 29dc09e94eb1a43c0f6e4b2bf2cfaf754fbd557034808823eab1ce0cd4ab251e |
| dusty-0.5.0-m5.2-sbom.json | 86b4bb27abbf8745dee8cc81bab8dad040fabbb9d58207dea2e6557ee9c40b1a |
| installer-jedi-source.zip | 4dac842302518887fd2e8692da73ca1f2adcac9092c32cb634e4f7143f4ae217 |
| SHA256SUMS.txt | 3484ed0475b5f46bd950253d389a7e970464630c87d3618ce01d3723d173b766 |

The .2 installer audit is calibrated: Setup 0, GUI/probe 0, native 0, fetch
allowed 4, blocked 0. Installed processing-only audit and both uninstall choices
passed; transcript sentinel unchanged. Its upgrade reused the same build and is
not two-version evidence. The corrected test tag .4 runs a true .2-to-.4 upgrade,
including prior-installer checksum verification and downloader blocking.
CI .2 source: 256 passed, 2 skipped, 94.6% coverage; separate real-network
download test 1 passed. The failed .1 source golden/version attempt produced no
release or installer upload. Its tag/history remain unchanged.

## Questions for the PM

0. Approve the S0 repair across startup, probe, self-test and coordinator cleanup.
   Recommendation: unique owned work areas, saved output/source protection,
   conservative handling of unknown content/metadata, and rejection of new
   destinations inside app-managed work areas. Preserve already-saved destinations
   before any startup cleanup; never silently move/delete existing files.
1. Approve or annotate the installer page bundle. Recommendation: review the
   complete native flow, including failed GPU test versus failed CPU test.
2. Upgrade reuses verified models; hash failures are detected before download.
   The catalog does not yet show per-file damaged/re-download badges. Confirm
   whether the plain Checking/Downloading phase is sufficient, or request this
   as a page change. Recommendation: show a clear per-model repair status.

## Installer screenshots

[Draft page review](https://github.com/dusty-corporation/dusty/releases/tag/untagged-a1e1f91641e95222b8da):
`m5-installer-pages-step-b-895e199-light-review.zip`, 7,861,054 bytes,
SHA-256 `d09b2e4695fca10c5c0409dcee5cac70121bec5da1e8555b34c68aa57ca0578e`.
21 real native-control PNGs plus README, archive gate passed. License views,
catalog, folder, shortcut, consent, progress, retry/CPU retry, incomplete setup,
finish and uninstall states included. Synthetic states are labeled, not treated
as functional failure-injection results. CI provenance: 40036996425 / 40039096810 /
40040642247. Process-effective 96 DPI was used on an unchanged 175% desktop;
Windows bitmap scaling remains visible. Actual 100%/150% display acceptance is
not claimed and stays on the Owner checklist. No further wording/layout changes
are planned before the PM reviews M5-interim-2.md.

## Self-review

**Blocking finding: ISSUE-020, NN-7.** Named work directories are treated as
exclusive app property despite being selectable/saved transcript destinations.
The new startup cases (probe/selftest) and installer self-test preservation case
all fail. Existing uninstall protection does not cover these paths. No repair
was implemented after the mandatory S0 stop; further source/packaged/installed
and uninstall acceptance must follow the PM's decision.

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

## M6 documentation prework branch

Authorized optional prework is pushed on m6-docs-v2 at 8a91934, based on
m5-installer 20cce6b (same final application/installer behavior at that point).
It contains user guides, privacy, CONTRIBUTING and README guide links only,
plus its ledger entry. It covers current installer pages, failed-model outcomes,
model deletion/voice-detection blocking, normal-stop versus crash partials,
seven-day cleanup and SmartScreen. Exact SPEC 9.6 wording is retained.
Reference m6-docs (c855b52) and m5-packaging-spike (95dd90b) remain untouched.
No M6 acceptance or PR is claimed. Later M5 evidence-only report updates are on
m5-installer; the documentation branch is available for PM review after M5.
