# M4 Report - Model Manager and isolated downloads

## 1. Summary

M4 engineering acceptance is complete: Model Manager downloads, verifies,
resumes, cancels and deletes models through a separate dusty-fetch process.
All M4 quality gates and CI pass; calibrated WFP found zero GUI connections
during real downloads. The synchronized M5 split bundle also passes its PE,
license, GUI and packaged WFP gates. Optional installer prework compiles, but
binary upload is held for the PM's InnoSetup license-policy decision (ISSUE-017).
ThinkPad review and clean-machine installer acceptance remain Owner work; no PR was opened.

### Branches

- `m4-downloader`: M3 carried forward, unchanged Owner M4 brief plus archived
  M3 brief, Start/label/contrast corrections, complete Model Manager, tests,
  source WFP audit, screenshots and this report. Product/renderer source aab3ec6.
- `m5-packaging-spike`: rebased onto M4; retains approved stdlib DOCX,
  separate offline/downloader runtimes, exact PE/CRT pins and license evidence.
  Packaged acceptance is green at 5ca1180. Optional installer prework is draft
  only: ADR 0022, generated per-user setup, complete license acceptance,
  bundled downloader/self-test gates, conservative uninstall cleanup and
  audit-only CI. Compilation passes; installer binary upload is blocked by its
  separate license gate. See M5-interim-5.md on that branch.
- `main`: unchanged by the engineer; no merge, publication or repository-setting change.

### Owner actions for the morning

1. Review the [M4 screenshot draft](https://github.com/dusty-corporation/dusty/releases/tag/untagged-6184fb70591dd06d1c63)
   and run the six ThinkPad checks in section 8. Send pass/fail by number.
2. Give the PM this report. Wait for PM acceptance before a PR against main;
   the Owner controls merge and publication.
3. Ask the PM to resolve M5 ISSUE-017: approve proposed ADR 0023's narrow
   InnoSetup exception (recommended), or replace the approved Inno architecture.
   The full license permits redistribution but its distinct identifier is not
   in SPEC 10.2's allowlist; no exception was added by the engineer. Only audit
   metadata is uploaded. This is an M5 policy decision, not an M4 blocker.
4. After license clearance and remaining installer inventory, review an installable
   M5 draft on a fresh standard-user Windows 11 VM using docs/pm/M5-checklist.md.
   No installer was run on the Owner's desktop. Fresh install, cancel/resume,
   failed install/retry, upgrade, both uninstall choices and installed-app WFP
   remain M5 acceptance work.
5. Keep the real Surface Vulkan smoke test on the required pre-M7 list. It
   does not block M4 and has not been replaced by a hosted-runner result.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Catalog/statuses, sizes and free disk space | met | All five catalog models plus voice detection; local integrity scan, Installed/Not installed/Damaged/Downloading; Qt/local-TLS tests. |
| Consent, progress, cancel and restart/resume | met | Named files, total MB, explicit GitHub consent; real CLI JSON progress; Job Object cancellation, retained .part, new manager/registry resumes by Range. |
| Damaged model never used | met | Hash mismatch displays Damaged/Download again, removes bad partial; registry integrity remains mandatory for transcription. |
| Delete confirmation/protections and Verify all | met | Selected/last model and in-use voice detection protected in UI and worker; Verify all forces re-hash, including same-size/mtime tampering. |
| Main-window integration | met | No-models Start hint, one-click missing recommendation, live Options refresh, explicit user choice retained, implicit recommendation selected when available; missing VAD handled. |
| Voice detection auto-include | met | Missing required VAD joins the same named consent and verified child-download sequence; standalone voice row also supported. |
| Separate process, development and packaged paths | met | Source Python -m dusty_fetch; packaged sibling dusty-fetch/dusty-fetch.exe; unit resolution tests and actual source/packaged GUI downloads. No GUI import of dusty_fetch. |
| Zero processing connections | met | Source and packaged WFP tables below; guard installed, consent confirmed and both assets verified. Static policy unchanged, zero exceptions. |
| M3 carry-over corrections | met | Start stays full width in idle/running/disabled states, reason centered above; consistent ', recommended' suffix; dark disabled text contrast at least 4.5:1. |
| Automated suite, types, policy and CI | met | 149 local passes/1 CI-only skip; 94.2% strict coverage; M4 run 39910270912 green. |
| Screenshot review and ThinkPad interaction | partial | 76 reviewed synthetic PNGs uploaded; Owner's short real-hardware check pending. |

## 3. What was built

- app/model_manager.py: modal catalog, worker/controller, consent, child
  protocol, cancellation, verification and deletion rules.
- app/window.py, workers.py, messages.py and theme.py: manager entry points,
  recommendation/no-models/VAD integration, current choice preservation and
  the three Start/label/contrast corrections.
- runtime_paths.py: explicit source/frozen downloader command resolution.
  Each downloader JSON event includes its actual PID for reliable WFP attribution
  across Python launcher and packaged child layouts.
- Hidden CI-only GUI download exercise plus calibrated WFP harness; source
  and packaged paths drive the actual manager and consent dialog.
- Local-TLS Qt regression coverage, reproducible render_models.py, developer
  downloader documentation and AUDIT-NOTES.md. The first audit item is the
  private ModelRegistry._verified cache access; no optional refactor was added.

## 4. Test results

### Local and CI

| Check | Result |
|---|---|
| Full M4 suite | 149 passed, 1 CI-only skip; 169.01 s |
| Strict-package line coverage | 94.2% total; core 93.7%, export 98.5%, models 94.4%, queue 93.0%, privacy 95.2% |
| Focused downloader/manager/boundary suite | 31 passed; guarded real GUI/local-TLS subprocess also passed |
| Ruff / format / mypy | Passed; 98 formatted files, 58 source files checked |
| Three policy checks | Passed: check_no_network.py, check_no_huggingface.py, check_licenses.py |
| M4 implementation CI | [39909561630](https://github.com/dusty-corporation/dusty/actions/runs/39909561630), 01bcc73, green |
| M4 renderer/evidence CI | [39910270912](https://github.com/dusty-corporation/dusty/actions/runs/39910270912), aab3ec6, green |
| M4 report/checkpoint CI | [39913841073](https://github.com/dusty-corporation/dusty/actions/runs/39913841073), 34256af, green; subsequent report changes are documentation only |
| M5 after M4 rebase | [39910562031](https://github.com/dusty-corporation/dusty/actions/runs/39910562031), 5ca1180, all jobs green; 178 CI passes/2 expected skips, real-network integration separately passed |
| Rebased M5 local suite | 179 passed, 1 CI-only skip; 197.64 s; 94.4% coverage |
| Packaged gates | 64 PE files checked against exact pins; layout, license/SBOM, GUI smoke and both WFP scenarios passed |
| Final M5 prework code | [39916465602](https://github.com/dusty-corporation/dusty/actions/runs/39916465602), 0adc037: source 188 passed/2 expected skips, 94.5%; all app gates and installer compile pass; installer-only Inno license gate deliberately fails |

The ordinary suite skips the explicit CI-only real-network test. Hosted CI
also skips Vulkan transcript comparison when there is no usable Vulkan device;
this is not a substitute for hardware acceptance.

### WFP evidence

| Scenario | Processing / GUI events | Fetch allowed | Fetch blocked | Calibration |
|---|---:|---:|---:|---|
| Source self-test, headless and GUI processing | 0 | outside audit | outside audit | Blocked positive control passed |
| Source real Model Manager download | 0 | 4 | 0 | Blocked positive control passed |
| Packaged offline self-test | 0 | outside audit | outside audit | Blocked positive control passed |
| Packaged real Model Manager download | 0 | 4 | 0 | Blocked positive control passed |

Source download evidence is artifact m4-download-audit in 39909561630;
packaged evidence is packaging-spike-audit in 39910562031. Both download
results confirm the guard, user-consent exercise and successful model/VAD hashes.
For source runs, GUI/fetch share the Python image, so actual reported PIDs
separate them; the existing blocked-image processing test remains unchanged.
For packaged runs, Dusty's own image remains blocked during download while
the separate fetch image is allowed. No hostname/address data is retained.

### Screenshots

Draft asset: m4-screenshots-aab3ec6.zip, 76 PNGs, 3,605,372 bytes.
SHA-256: `1d7d30ea6d3e83824502f77dcfd22122f5178be8f2800ebeccdebcb15594e7f6`.
There are 19 states in light/dark at 100%/150%: main prompts, updated Options,
catalog states, delete protections/confirmation, consent with VAD, progress,
verification, pause, mismatch, disk/connection failure and Verify all.
These are synthetic widget captures, not claims of completed hardware review;
42 GB free space is illustrative. Native title bars/tooltips are outside grabs.

## 5. Deviations from SPEC

No new M4 security-policy exception, dependency or catalog change. Accepted
ADR 0017 audit-hook and ADR 0021 exact platform primitive pins remain in force.
The source layout uses the current interpreter; the packaged split layout is
the already accepted M5 arrangement. Optional M5 installer prework follows the
PM's ADR 0022 bundled-fetch decision instead of Inno's built-in HTTP downloader.

## 6. Issues

No new S0/S1 issue found in M4. M5's ISSUE-017 (S1, open) records the installer
wrapper license-policy gap; proposed ADR 0023 has not been accepted.
AUDIT-NOTES.md records non-urgent review areas;
enterprise proxy support remains in BACKLOG.md. Previously accepted M5 licensing
and native-import resolutions were retained during the rebase.

## 7. Decisions needed from PM/Owner

PM acceptance after screenshot/ThinkPad review. No unresolved M4 architecture,
privacy or licensing decision. Installer fresh-machine acceptance is a separate
M5 gate, not implied by this report. The separate M5 license decision is described
in the morning list and M5-interim-5.md; it does not change M4's app allowlist.

## 8. Short ThinkPad check list

Use the audited [app review artifact](https://github.com/dusty-corporation/dusty/actions/runs/39916465602/artifacts/12484769263).
The run is red solely at the installer license gate; source and all app gates
are green. No repo clone or Python is needed. In a folder of your choice:

```powershell
gh run download 39916465602 --repo dusty-corporation/dusty --name m4-review-bundle --dir Dusty-M4-review
$dustyReviewData = Join-Path $PWD 'Dusty-M4-review-data'
$dustyReviewPreviousLocal = $env:LOCALAPPDATA
$env:LOCALAPPDATA = $dustyReviewData
Start-Process .\Dusty-M4-review\dusty\dusty.exe -Wait
$env:LOCALAPPDATA = $dustyReviewPreviousLocal
```

This uses an isolated profile for the no-models test and preserves your current
profile/models. Repeat the environment/launch lines for a relaunch. Keep dusty,
dusty-fetch, bin, resources and licenses side by side. Do not move the executables
out of their folders. Allow about 10-15 minutes plus model download time.

1. **Empty state/layout:** no models means Start disabled with its reason
   centered above a full-width button. Output-folder line remains visible.
   Check dark mode and 150% scaling; recommendation suffix reads ', recommended'.
2. **Find models:** open from Tools and from Options. Confirm plain model labels,
   technical names, sizes, statuses, free disk space and the focused recommended row.
3. **Consent/download:** Download it opens that model. With Skip silent parts on,
   missing voice detection is included in the named consent/MB total. Reject once
   (nothing downloads), then accept and observe percentage/MB progress.
4. **Cancel/relaunch/resume:** cancel an incomplete download, close/reopen Dusty
   and download it again. It resumes, verifies and becomes Installed; Options
   updates without restarting. A deliberately chosen model is not replaced.
5. **Integrity/delete:** Verify all remains responsive. The selected/last installed
   model cannot be deleted. Choose a different model when at least two are
   installed; reject then accept deletion. Only the downloaded model disappears.
6. **Offline use:** after a verified model and voice detection are installed,
   disconnect Wi-Fi, transcribe a short public fixture and save Text/Word.
   No downloader or consent should appear during transcription. Send pass/fail
   by step, Windows scale/theme and any visible plain error; no private recordings.

## 9. Risks for the next milestone

- Installer drafts still need real standard-user/upgrade/uninstall and
  installed-app network acceptance; compiler success is insufficient.
- Cold startup without any model cannot perform the speech-based backend probe;
  the CPU-safe recommendation applies until a model permits a real probe.
- Cancellation/recovery, protocol boundaries and private registry cache access
  should receive independent M6 review. Literal static checks do not prove the
  absence of obfuscated code; runtime/PE/WFP layers remain required.
- Existing Persian fixture provenance remains: [original recording](https://archive.org/download/rubaiyat_bilingual_1207_librivox/rubaiyat_01_khayyam_whinfield_64kb.mp3),
  exact source interval [107, 122) s (00:01:47.000 to 00:02:02.000),
  Owner-verified by listening as a complete spoken Farsi quatrain on 2026-10-22.
  Canonical provenance file is tests/fixtures/AUDIO_SOURCES.md; no new audio added.

## 10. Time/effort notes

The main work was safe Qt worker shutdown, preserving explicit choices,
restart/resume through a real TLS child and reliable source/packaged WFP
attribution. Rebase conflicts were additive ledger/workflow changes; accepted
license evidence and exact binary pins were retained. No engineering-hour
estimate or unperformed hardware result is asserted.

## Overnight follow-up

- M5 final local tests: 189 passed/1 CI-only skip, 174.00 s; 94.5% coverage.
  Final source CI: 188 passed/2 expected skips, 274.44 s. An earlier M5 source
  run (39915503372) observed a 229.671 ms Qt event gap; the unchanged 200 ms
  test passed in final verification. No threshold or test was weakened.
- Latest app bundle: 207 files, 161,936,952 bytes; all 64 PE checks and app
  license/GUI/WFP gates pass. The two files added over the 205-file baseline
  are Inno license/provenance text; no PE was added.
- Unsigned installer draft compiled: 34,593,012 bytes. Its binary was not
  uploaded; m5-installer-draft-audit contains only hash/size/terms and findings.
  InnoSetup is a distinct [SPDX license](https://spdx.org/licenses/InnoSetup.html),
  absent from the allowlist. Proposed ADR 0023 and ISSUE-017 are on M5; PM
  clearance and a complete installer-wide inventory are required before distribution.
- No PR, merge, publication, settings change or new milestone beyond the
  explicitly authorized M5 prework. All code and reports are committed/pushed;
  final branch synchronization changes documentation only.
- Long-dash check: `rg -n '[\x{2013}\x{2014}]' AGENTS.md README.md LICENSE NOTICE src tools tests docs installer packaging native modelpipeline .github pyproject.toml uv.lock`.
  Output: none (exit 1, no matches). SPEC and the Owner's M4 brief were not edited.
