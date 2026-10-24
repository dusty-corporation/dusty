# M6 Report - Hardening and documentation

## 1. Summary

M6 is **not ready for acceptance**: production engine activation, the real cause
of ISSUE-027, and Owner checklist sign-offs remain open. The exact UTF-8 engine
candidate passed every source, packaged and installed gate in
[CI 40125892713](https://github.com/dusty-corporation/dusty/actions/runs/40125892713).
Documentation, audit dispositions, safety repairs and the requested installer/
About changes are implemented and pushed on m6-hardening. M5 code and frozen
.13/.14 drafts remain unchanged; only the explicitly authorized M5 documentation
commit d4ee428 records ThinkPad results and SmartScreen test instructions.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| User, privacy, developer and contributing documentation | met | docs/user, docs/privacy.md, docs/dev/build-from-source.md, release process, conversion recipe, CONTRIBUTING and README; exact SPEC 9.6 FAQ wording; five consistency/negative tests pass. |
| Every audit note fixed or given a V1 disposition | partial | AUDIT-NOTES.md disposition table; public registry API, work leases, path boundaries and truthful cleanup fixed. ISSUE-027 native producer remains unproven. |
| V1 polish | met | Graphics-test failure meter reflects completed download bytes; no new artwork, dependencies, catalog or network paths. |
| Automated adverse paths | met for candidate | Real GUI Unicode model/profile paths and sync consent, >300-character Unicode decode/all exports, forced process death/resume, cancellation, preflight/decode/export disk exhaustion and downloader disk failures; full suite below. |
| Packaged privacy, PE and licenses | met for candidate | Packaged and installed canaries/WFP pass; 64 PE files checked at each stage, exact platform pins, bundle and installer-wide licenses pass. |
| Actual Unicode Windows account | partial | Synthetic app-data/models/output paths and real Unicode installation directory pass. Runner account name is ASCII; separate account protocol in M6-checklist.md is pending. |
| Desktop and ThinkPad manual offline/reboot test | not met | M6-checklist.md, about 20 minutes per machine, awaiting Owner. Automated WFP is separate evidence. Surface offline check belongs to M7. |
| SPEC >=2 h laptop endurance | partial | Historical desktop Small CPU/Turbo Vulkan runs completed 7920.1875 s of public audio; physical laptop endurance not performed. No Surface result or waiver is invented. |
| Zero open S0/S1 | not met | ISSUE-028 resolved on M6; ISSUE-026 is S1 until an approved engine release is activated and production-pin CI passes. |
| All checklists with Owner sign-off | not met | M5 fresh-VM .13/.14 and M6 manual checks remain pending. No PR/merge/publication requested or performed. |

## 3. What was built

- Public, serialized ModelRegistry.invalidate; the Model Manager no longer
  changes its private verification cache. Prepared VAD state defaults safely.
- Work-area OS leases preserve another live instance's files. Restored relative
  paths reject traversal, roots and drive-relative forms. Windows ordinary/
  extended namespace aliases share protection comparisons without shortening
  actual long-path I/O. Unknown or protected content is retained.
- Disk-full errors reach the correct plain reason, including native decoder
  exhaustion derived without logging stderr. OS-denied partial cleanup reports
  retained data instead of claiming success.
- Successful Setup preserves an installed/hash-valid choice; fresh, empty,
  unknown or damaged selections receive its tested default. Wizard priority is
  recommended selected model, otherwise first selected. Five profile cases pass.
- About shows name/version, one-line description, Apache-2.0, selectable plain
  repository text and read-only local notices. Privacy and accuracy is unchanged.
- Windows Apps uninstall uses /SILENT /DUSTYCONFIRM=yes: one Dusty confirmation,
  working model-removal checkbox, no generic second question, protection first.
- Documentation consistency gate, independent AUDIT-PACKET.md, M6-checklist.md,
  proposed ADR 0024 and exact candidate-validation provenance. Accepted images
  remain historical review links; no new image source or screenshot was added.

## 4. Test and CI results

Final code: fc2c6e55f76d720e2ac93fc89aa3f4570c9a8beb. Later commits contain
documentation only. Commands in CI: ruff check, ruff format --check, mypy,
tools/check_docs.py, tools/measure_coverage.py, three policy checks, native PE/
license gates and the source/packaged/installed PowerShell acceptance scripts.

| Result in 40125892713 | Evidence |
|---|---|
| Source | 392 passed, 2 expected skips, 286.62 s. Skips are the separately opted-in real-network test and unavailable physical Vulkan device. No new skip/xfail. |
| Explicit public Tiny integration | 1 passed, 1.67 s, separate CI-only network opt-in. Unit download tests use local TLS. |
| Strict coverage | 1046/1092 = 95.8%; core 93.7%, export 98.6%, models 97.4%, queue 94.7%, privacy 96.6%; every package exceeds 85%. |
| Static checks | Ruff pass, 152 files formatted, mypy 82 sources, docs/network/model-host/license policies pass. |
| Source Model Manager WFP | GUI 0; fetch allowed 4, blocked 0; verified true; blocked-event calibration true. |
| Packaged Model Manager WFP | GUI 0; fetch allowed 4, blocked 0; verified true; calibration true. |
| Packaged and installed processing | Connection events 0 in both; self-test, model-free probe and sensitive-log canary pass. Runner has no real GPU; not a physical Vulkan inference claim. |
| Setup full download | Installer 0, GUI 0, native 0; fetch allowed 4, blocked 0; probe and calibration pass. |
| Setup cancellation | Installer/GUI/native 0; fetch allowed 2, blocked 0; retry succeeds and partial cleanup passes. |
| Installed ownership | 221 files match inventory; ordinary and extended protected destinations refused before native deletion; original synthetic bytes/metadata survive. |
| Uninstall UI | custom_confirmation=1, generic_confirmation=0, keep_models_choice=passed. Both removal choices and output sentinels pass. |
| Upgrade limit | Verified models keep hashes/write times with downloader blocked. This run reinstalls the same version: two_distinct_versions=false. Frozen M5 .13/.14 is the separate true-upgrade pair. |
| Redistribution | Bundle and installer-wide license gates pass; offline and installed PE scans each list 64 files, exact ADR 0021 pins. Bundle: 216 files, 162,030,546 bytes. |

Artifacts in that run: m4-download-audit, packaging-spike-audit,
m5-installer-draft-audit, m5-installer-draft-unsigned, m4-review-bundle and gated
page-review executable. Names are inherited workflow names, not new releases.
Downloaded installer verified locally:

- File: Dusty-0.0.1-draft-unsigned.exe, **34,707,674 bytes**.
- SHA-256: `6976d416eb02ae842bcbe691f80f134e9d2fda5a50e8fdc76eda48861f5ecae8`.
- CI artifact only, candidate engine, not an approved public installer.

Native CPU/Vulkan build
[40110881732](https://github.com/dusty-corporation/dusty/actions/runs/40110881732)
passed at d0abc304942255a1d30d741fff0ca98c2c1cdf45, retaining GGML_NATIVE=OFF,
CPU dispatch and the VAD patch. Every candidate member and deterministic package
hash is pinned in native/m6-engine-candidate.json. CPU package SHA-256 is
`b47ec54df7ecb09b341bb7abc5f0f461f746f4bfe72b4873d5843340b9cef910`;
Vulkan package is
`0e8f26c55c4abd7b708af1106027c2d75ed2d4592f103e10263f08e0c8d523c7`.
These are staged package hashes, not GitHub's outer artifact ZIP hashes.

Candidate mode explicitly verifies the native run and stages both exact packages
in a disposable CI checkout. **Committed production pins still select engine-v2.**
Normal push run 40124502543 failed its enabled Unicode-profile test (1 failed,
391 passed, 2 skips); candidate success must not be called production CI green.
No failing test was disabled or weakened.

Earlier candidate 40124502580 passed protection/installed WFP/PE, then failed the
new UI harness's control discovery. Visibility/initialization and documented,
bounded cross-process WM_GETTEXT reads repaired that harness; both 40125713083
and final 40125892713 pass the entire lifecycle. Failed runs uploaded no installer.
Superseded 40123796192 was cancelled before affected review-binary upload after
the path finding; its audit evidence remains. No run or artifact was deleted.

Local final docs checks: five tests pass, 1.46 s; lint/types/policies pass.
`git grep -n -I -P '[\x{2013}\x{2014}]' -- .` produced no output, exit 1.

Historical endurance details, hashes and sampling limits are in
../benchmarks/m6/desktop-long-recording.md: Small CPU 1060.9096 s, RTF 0.133950,
sampled tree RAM 2,612,928,512 bytes, peak work 253,446,078 bytes; Turbo Vulkan
268.3786 s, RTF 0.033885, RAM 2,119,102,464 bytes, work 264,681,781 bytes. Both
exit 0, work empty afterwards. This is 2026-10-23 desktop prework, not a new M6
candidate measurement or laptop acceptance. No long audio/raw JSON is committed.

## 5. Deviations and limits

ADR 0024 remains proposed: a link-time UTF-8/long-path manifest fixes the pinned
CLI's lossy narrow argv. Same engine/dependencies, no runtime binary alteration,
system-locale change or ASCII-path workaround. Activation requires PM/Owner.

The supported uninstall route is Windows Settings > Apps. Directly running the
internal bare unins*.exe without its registered arguments can still show Inno's
generic question; no compiler/runtime patch was introduced. Pinned behavior and
the native UI driver's Microsoft API contracts are in docs/dev/release-process.md.

Crash temporaries, unknown changed contents and OS-denied cleanup may remain
rather than risk removing outputs. Deliberate same-account reparse replacement
is outside SPEC 9.1; static link checks are not handle-relative traversal.
Completed Qt wrappers remain until window teardown; long interactive retention
is an audit limit, not claimed bounded memory. All original audit notes have
explicit dispositions and remaining limits in AUDIT-NOTES.md.

## 6. Issues

| ID | Severity | Status | Summary |
|---|---|---|---|
| ISSUE-026 | S1 | Candidate fixed; activation pending | Public engine-v2 fails non-ASCII model/audio paths; full candidate gates pass. |
| ISSUE-027 | S2 | Open | 0x8001010d native producer unknown. Three isolated comparisons and full passive-observer run did not reproduce it; capture file is empty. HRESULT meaning is not a root cause. No suppression. |
| ISSUE-028 | S0 boundary risk | Resolved on M6 | Ordinary/extended path protections unified and native refusal cases pass. Predicate-only finding; no Owner data touched. Frozen M5 has no backport. |

## 7. Questions for the PM

1. Approve ADR 0024 and preparation of a new engine draft for Owner publication?
   Recommend yes, using the exact gated candidate, then activate verified new
   release pins and rerun normal CI. Do not alter engine-v2 or frozen drafts.
2. Authorize a separate M5 backport of the namespace protection repair?
   Recommend before confidential use, preserving .13/.14 and using new builds
   if needed. M5 code remains frozen until instructed.
3. ISSUE-027 root cause is still required. Recommend keeping it open and doing
   targeted native observation on recurrence, rather than accepting a guessed
   COM/accessibility explanation or suppressing the diagnostic.
4. Accept the registered Windows Apps route as the single-confirmation contract?
   Recommend yes; keep the bare internal-uninstaller limitation documented.
5. Confirm laptop endurance scheduling/proxy. Recommend the approved ThinkPad
   class for the next >=2 h measurement, keeping unavailable Surface evidence
   explicit rather than treating the desktop run as a substitute.

## 8. Owner actions

1. Finish the frozen M5 VM checklist separately. ThinkPad .14 evidence on
   2026-10-24 is recorded in M5-report.md and the ledger: no UAC; Turbo suggested;
   Vulkan and CPU fallback tests; Finish launch; correct TXT/DOCX; OneDrive
   Documents warning; 150% layout; complete app/data/models removal with
   transcripts untouched. It is not VM/offline sign-off. SmartScreen was not
   exercised because gh omitted Mark of the Web; M5-checklist.md and release docs
   contain the exact Zone.Identifier ZoneId=3 command for guest-local installers.
2. PM first resolves the engine/backport questions. Owner publication is a later
   explicit step after a reviewed draft exists; nothing has been published here.
   The current candidate can be retrieved for public-fixture review only:

   ```powershell
   gh run download 40125892713 --name m5-installer-draft-unsigned --dir build/m6-review
   $setup = @(Get-ChildItem build/m6-review -Recurse -Filter 'Dusty-0.0.1-draft-unsigned.exe')
   if ($setup.Count -ne 1) { throw 'Expected one candidate installer' }
   Get-FileHash -LiteralPath $setup[0].FullName -Algorithm SHA256
   ```

   Compare with the hash above. Do not replace the frozen VM pair or use this as
   an activated production release. After activation, identify the newly gated
   build/hash before final acceptance.
3. Run M6-checklist.md on desktop and ThinkPad, including disconnected reboot,
   public batch, CPU fallback, cancel/resume and sync consent. Send build/hash,
   model/device and numbered PASS/FAIL; no private paths/state/recordings.
4. Perform its separate fresh-standard-account path check after M5 VM testing;
   report the actual space/non-ASCII profile flags. Laptop endurance remains
   separate pending PM scheduling. Keep the Surface offline check for M7.

## 9. Risks for the next milestone

Do not advance acceptance while production engine pins fail or Owner checklists
are incomplete. Frozen M5 does not contain the Unicode/namespace/handoff fixes.
Qt root cause, actual account paths and physical GPU/cold-machine behavior need
their named evidence. Current native lifecycle uses same-version reinstall;
do not mislabel it as a new true-upgrade pair. Independent audit should use
AUDIT-PACKET.md and retain conservative cleanup/temporary-file limits.

## 10. Effort notes

Windows code pages, namespace equivalence, live-work ownership and native-window
discovery required actual cross-process/native regressions. Packaging and
installed WFP were rerun after the final driver repair. The remaining gaps
require PM/Owner evidence, not additional speculative features. Work stops here;
no next milestone, PR, merge, new release/tag or publication was started.
