# M5 report - Packaging, installer and draft release pipeline

## Summary

M5 engineering work is complete on m5-installer; fresh standard-user VM
acceptance is still pending. Final repaired drafts are **v0.5.0-m5.11** and
**v0.5.0-m5.12**, with every release job green and a real .11 to .12 upgrade.
The second review found and fixed ISSUE-023 (legacy destination protection)
and ISSUE-024 (interrupted license cleanup); all original regressions remain
enabled. No Owner data was accessed, and no PR, merge or publication was made.

## Owner actions

1. Use only the final .11/.12 pair below. .1 through .10 are historical,
   superseded drafts. Keep every test release draft.
2. Follow [M5-checklist.md](../M5-checklist.md), about 90 minutes after setup and
   downloads. Dusty-M5: Windows 11 Home, 8 GB, 4 CPUs, 80 GB, VBoxSVGA,
   Guest Additions, standard DustyTester, snapshot clean. AMD SVM is enabled.
3. Use the checklist's exact host commands for the read-only auto-mounted
   C:/Users/kdash/bench/m5-vm share. Copy into guest Downloads before running;
   verify the full installer hashes below. No GitHub credentials go to the guest.
4. Return numbered PASS/FAIL results, Windows build, SmartScreen/UAC outcome,
   model hashes/write times across upgrade, and both uninstall results. Test
   the explicit legacy-setting/sentinel commands separately, then revert clean.
5. Confirm native 100%/150% layout, Cancel/X/Escape and checked Open Dusty now
   surviving Setup exit. Use public fixtures only. VirtualBox is CPU acceptance;
   real-device GPU tests and the pre-M7 Surface Vulkan smoke remain hardware checks.
6. PM acceptance and any future PR/publication remain separate Owner decisions.

## Final gap table / acceptance criteria

| SPEC M5 item | Status | Evidence / remaining work |
|---|---|---|
| 1. PyInstaller split payload, bin/resources | Done | Separate app/fetch onedir; engine-v2, minimal FFmpeg, resources, no bundled models. Exact PE pins, license/notices/SBOM and GUI gates pass. |
| 2. Generated installer, choices, downloads, self-tests | Implementation done; VM partial | Shared catalog/wording, bounded real-GPU/RAM probe, Auto per selected model plus smallest CPU test, VAD verification, retry/processor/Finish without. PM pages accepted; fresh VM pending. |
| 3. Upgrade | CI done; VM partial | Real .11 to .12; verified models reused with fetch blocked, hashes/write times preserved. Damaged files show Needs download again. Exact installed inventory passes. |
| 4. Uninstall | CI done; VM partial | Both choices, output sentinel, persisted legacy protection and conservative owned cleanup pass. Actual standard-user VM controls remain manual. |
| 5. Gated tagged draft release | Done | Runs 40099284709 and 40100326932; every job green, five assets each, hashes verified. No portable asset. |
| 6. SmartScreen README | Done | Unsigned explanation, More info/Run anyway, Get-FileHash and full checksum comparison. |
| Acceptance: tagged draft with artifacts | Met | Final .11/.12 drafts; release assets listed below. |
| Acceptance: fresh Windows 11 VM, SPEC 11.6 | Not met yet, Owner | Exact 90-minute checklist, shared-folder transfer, standard user, interruption/tamper/upgrade/both uninstalls and expected results. |
| Acceptance: installer size | Met | Exact sizes below, about 34.7 MB compressed, no model weights. |
| Brief: page review and scaling | PM review accepted; VM scaling partial | 21 native light PNGs plus README, explicit scale limitation. Output row has 16 Qt light/dark 100%/150% captures. Genuine native monitor-scale checks remain Owner evidence. |
| Brief: source/packaged/installed WFP | Met in CI | All privacy gates green, calibrated counts below. |

## What was built

Split PyInstaller specs; generated Inno template/controller; guarded offline
probe, self-test, upgrade and cleanup helpers; exact installed/PE/license
inventories; calibrated source/package/installed/download WFP tests; receipt-gated
tag releases and checksums. This round also aligns the app's output row with
Options, elides long paths and preserves complete accessibility/tooltip text.

## Test results and CI evidence

- Final code/test head 791682b, tag .12, [CI 40100326932](https://github.com/dusty-corporation/dusty/actions/runs/40100326932):
  **354 passed, 2 expected skips**, 315.72 s; separate real-network test
  **1 passed**, 1.95 s. Skips are unavailable hosted Vulkan and the default-disabled
  CI-only real-network test, which is run explicitly afterwards.
- Required package coverage **94.7% (1012/1069)**, all above 85%: core 93.7%,
  export 98.6%, models 96.6%, queue 92.7%, privacy 96.6%.
- Full local source before the final 16 atomic cases: **339 passed, 1 expected
  skip**, 213.48 s, 94.2%. All **49 adversarial cases** pass separately; all are
  included in the final full CI run. GUI/output-row tests: 29 passed.
- Ruff/format (140 files), mypy (77 sources), static network with zero exceptions,
  excluded-host policy, runtime/installer license and exact PE gates pass.
- .11 [CI 40099284709](https://github.com/dusty-corporation/dusty/actions/runs/40099284709)
  and .12 have every source/offline/package/installed/draft job green. Receipts
  prove true upgrade, preserved model hashes/times with fetch blocked, exact
  installed payload, legacy protection, normal cancel/retry, both uninstalls and
  unchanged output sentinel. Failed/missing legacy receipt rejects release staging.
- Deliberate failing-license upload regression proves no installer upload follows
  a failed gate. Its expected negative annotation is not a failed job.
- Historical failures are retained: .8 inventory caught old versioned notices;
  40064929172 caught a native script type mismatch; docs-only 40066264053 had an
  offline child exit 1. None is green evidence. Local Qt diagnostic 0x8001010d
  with exit 0 is recorded for M6 audit, without suppression or invented cause.

### Calibrated final .12 WFP counts

| Scenario | Setup | GUI/probe | Native | Fetch allowed | Fetch blocked |
|---|---:|---:|---:|---:|---:|
| Full installer model download and model-free probe | 0 | 0 | 0 | 4 | 0 |
| Normal cancel after real prefix bytes, then retry | 0 | 0 | 0 | 2 | 0 |

Processing-only source, packaged and installed self-test audits also pass with
zero connection events. Only dusty-fetch downloads; no new network code or
static exception was added. Original and extracted Setup images are attributed.

## Page review round

PM **ACCEPTED** native pages 7b8d28b and app output row a75f1cf on 2026-10-24.
Shared wording covers three license views, catalog, inline consent, persistent
Downloading heading, Next=Download, byte totals, pre-start Back, truthful retry,
processor fallback, singular/plural success and Finish without. Open Dusty now
and desktop shortcut start checked. Uninstall is compact with true model size
and Cancel as default. Failure-bar/full-byte consistency is backlog as requested.

The app row is Choose folder... then Saving to, followed by TXT/Word and Options.
Buttons have equal width and aligned summaries. Qt ElideMiddle recomputes on
resize; full path remains tooltip/accessibility description. No-folder amber and
save-next-to disabled states and the actual Tab order have regression tests.

[Draft screenshot release](https://github.com/dusty-corporation/dusty/releases/tag/untagged-a1e1f91641e95222b8da):

| Asset | Contents | SHA-256 |
|---|---|---|
| m5-installer-pages-pm-round-7b8d28b-light.zip | 21 actual native PNGs plus README; CI 40065869279; 7,725,089 bytes | 27a3731c91478669cc5f13778b8ef432624c404cb2fb2adaf0fccb2905dbe1b0 |
| m5-main-output-row-a75f1cf-light-dark-100-150.zip | 16 actual Qt captures plus README, four states in both themes/scales | 84552bcbff635ea4de685e9694bc147b930bfe5483d258aa48aad95092eb0c08 |

Archive gates pass: PNGs/README only, no profiles or settings. Native review
states are explicitly synthetic, install-disabled/no-op, not failure-injection
or VM evidence. Native captures report 96 effective DPI on unchanged 175% host
bitmap scaling, never resized; genuine 100%/150% native acceptance is not claimed.
Qt output-row captures use actual offscreen device ratios 1/1.5 at 800 x 680
logical size. Own preview process was closed; no host settings/profile changed.

## Final release assets and installer sizes

Both downloads were verified against every API SHA-256 digest and all four
SHA256SUMS entries per release: ten asset digests and eight listed checksums
match. No installer was executed against the Owner's profile. Five assets per
draft only; no portable bundle. Historical .1 through .10 remain untouched and
superseded, not recommended as final candidates.

### v0.5.0-m5.11

[Draft release](https://github.com/dusty-corporation/dusty/releases/tag/untagged-ac62bd72d9a50ad10d0f), installer **34,695,893 bytes** (34.70 MB).

| Asset | SHA-256 |
|---|---|
| Dusty-0.5.0-m5.11-draft-unsigned.exe | 7dd7ac6d67a5cd175e2acec2956a0090c64fe3e05ff17a54393854efc7b4bac9 |
| SHA256SUMS.txt | 5ca935fd9dab575a86c2a1f75cbae370c5f62c448f0f6284035699dfa5cdb5e0 |
| THIRD_PARTY_NOTICES.md | e89e579cb529a1f635f0051f45448e8d16b4ba924c9182fbc20f7ac3136a9dba |
| dusty-0.5.0-m5.11-sbom.json | 2aec240041bab48794ce8663cf83231488745f2287a292500a6300e0eeaa1707 |
| installer-jedi-source.zip | 4dac842302518887fd2e8692da73ca1f2adcac9092c32cb634e4f7143f4ae217 |

### v0.5.0-m5.12

[Draft release](https://github.com/dusty-corporation/dusty/releases/tag/untagged-4c18b8608a05f5d8eb38), installer **34,685,652 bytes** (34.69 MB).

| Asset | SHA-256 |
|---|---|
| Dusty-0.5.0-m5.12-draft-unsigned.exe | bf2b137b014e26723643f3512ca5ce7d57f7e25f831a27402c88af0d1b38cd54 |
| SHA256SUMS.txt | 58454c95a7bcccdfc00d28dc73edfb85f200856cf15572b584c71a8359674574 |
| THIRD_PARTY_NOTICES.md | 90192151cedeeeaca067eaa12384762e42961ff6d4d6ae9704ad7e8bbbf92193 |
| dusty-0.5.0-m5.12-sbom.json | 8ddba09296f47da7b8453b101407b6c924072c47e9bf73d37c64e9ef434ed5e1 |
| installer-jedi-source.zip | 4dac842302518887fd2e8692da73ca1f2adcac9092c32cb634e4f7143f4ae217 |

## Probe evidence

Owner ThinkPad Iris Xe, 2026-10-23: real_gpu_found=true,
model_file_opened=false. The existing pinned engine initializes a real GPU and
4 KiB buffer without a model, bounded by a child Job Object/deadlines. Software
GPUs, hang/crash/timeout default Small; catalog RAM minimum selects Turbo only
when met, with a warning rather than a block below minimum. The standalone
probe is not model inference or full temporary-extraction timing evidence.

## Second self-review

Reviewed only M5 file deletion/move/overwrite code. The matrix exercised work
markers, obsolete licenses, stale partial receipts, uninstall, and atomic
state/export writes. Real junctions and symlinks point outside each work area
but remain inside isolated repo fixtures. Read-only files, another process's
exclusive handle, Unicode, extended Windows paths over 300 characters and
synthetic OneDrive output sentinels were tested. No real synced folder was used.

- **ISSUE-023, S0/NN-7:** a failing isolated test proved preserved_paths was
  omitted from uninstall's first inspector. The already-approved ownership rule
  required the repair. The actual installed app now retains that subtree and
  metadata; final release receipts must prove it. No Owner file was touched.
- **ISSUE-024, S1:** a child called os._exit(91) immediately after a real unlink;
  old-license cleanup preserved the remaining file but could not resume. An
  exclusive purpose/directory/hash receipt now permits safe retry and rejects
  changed receipt/content, unknown files and reparse points. Normal completion
  leaves no receipt in the exact installed inventory.
- Abrupt exit during other cleanup preserves unrelated output. Incomplete work
  inventories stay conservative. Atomic exit before/after replace keeps an old
  or new complete file; ordinary failures clean only their exclusive temporary.
  Active OS-locked download receipts already prevented stale-prefix removal.
- All 49 matrix cases pass, plus original safety/negative tests. No test skip,
  weakened inventory/license gate or new network exception was introduced.

Handle-relative traversal, possible retained .dusty-tmp after crash, and older
uninstall after an interrupted upgrade remain non-urgent AUDIT-NOTES items.
Do not sweep transcript folders or infer ownership from a filename suffix.

## Deviations and issues

Owner/PM-approved ADRs supersede the original SPEC: Apache-2.0 (0012), bootloader
exception (0014), stdlib DOCX/no shipped lxml (0019), VC runtime provenance/EULA
(0020), exact platform primitive pins (0021), separate hardened fetch rather than
Inno networking (0022), and installer-only licensing/source notices (0023).
No new dependency, native component or policy exception was added this round.

| Issue | Severity | Status | Evidence |
|---|---|---|---|
| 013 to 019 | Historical S0/S1 | Resolved | Accepted packaging/licensing and upload-order gates retained. |
| 020 | S0 | Resolved | Ownership/protection repair; original regressions enabled, green final runs. |
| 021 | S1 | Resolved | Native post-copy Cancel/X, real-prefix cancellation and retry pass. |
| 022 | S1 | Resolved | Exact obsolete own-license cleanup; true-upgrade inventory passes. |
| 023 | S0 | Resolved | Persisted legacy protection verified by installed exe and release receipt. |
| 024 | S1 | Resolved | Actual abrupt-exit recovery and unchanged/unknown preservation tests. |

## Questions for the PM

No new policy decision requested. Pages/output row are accepted; requested
progress-bar polish is backlog. M5 acceptance remains conditional on Owner VM
results, including native scaling and actual interactive controls. CI is not
claimed as fresh Windows 11 Home standard-user or physical GPU evidence.

## Branches and remaining risks

m5-installer holds implementation and this handoff. m6-docs-v2 e6de0aa carries
all second-review code/tests with verified parity and matching privacy/install
guides; final evidence/checklist sync follows. No M6 acceptance is claimed.
Reference m5-packaging-spike (95dd90b) and m6-docs (c855b52) remain unchanged.
Manual VM/SmartScreen/scaling and physical GPU outcomes are explicit gaps, not
assumed passes. Unknown/changed content is intentionally preserved with a notice.

## Time and effort notes

Ownership repair, native post-copy cancellation and real two-version upgrade
inventory required more work than screenshots. The second review added real OS
failure tests and installed-state coverage, finding two defects before handoff.
Engineer work is complete; stop here pending Owner VM results and PM acceptance.
