# Task Ledger

| ID | Milestone | Task | Status (todo/doing/blocked/done) | Evidence | Issues |
|----|-----------|------|----------------------------------|----------|--------|
| LICENSE-APACHE | M3 | Owner-authorized Apache-2.0 relicense | done | Owner is sole contributor; full LICENSE, NOTICE, README, pyproject metadata and amended ADR 0012; docs/metadata only | - |
| M0-01 | M0 | Repo structure, license, README, changelog | done | `6324f8c`, `90def49`; `git add --renormalize .` had no line-ending warnings | ISSUE-001 (resolved) |
| M0-02 | M0 | Pinned Python dependencies and lockfile | done | `6324f8c`; `uv sync --locked --python 3.12` resolved 60 packages | ISSUE-001 (resolved) |
| M0-03 | M0 | Review AGENTS.md, ledger, ADRs | done | AGENTS.md retained and updated; ADRs 0001-0014 in `bb03965`, `dee07bf`; PM spec revision `39bf2ae` | ISSUE-001 (resolved) |
| M0-04 | M0 | Three policy checks and negative tests | done | `9754c7e`, `25c9915`; `uv run pytest`: 13 passed; all three policy commands passed, with negative tests | ISSUE-002 (resolved) |
| M0-05 | M0 | Windows CI workflow | done | Owner confirmed PR #1 merged with green CI; merge commit `3bb0f7e` on `main` | - |
| M0-06 | M0 | Empty Qt window and --version | done | `6324f8c`; `--version` printed `Dusty 0.0.1`; Owner confirmed window on 2026-10-21 | - |
| M1-HK | M1 | Housekeeping | done | `9a65509`, `d0f1407`; M0 accepted per Owner | - |
| M1-A1 | M1 | Pin and verify versions | done | `native/versions.toml`, `docs/dev/build-native.md`; pinned upstream source and SDK checks | - |
| M1-A2 | M1 | Native whisper.cpp CI build | done | CI runs 39692634372 and PR #2 run 39694259471 passed; Owner's independent Vulkan and Haswell desktop retest exited 0 | ISSUE-003 (resolved) |
| M1-A3 | M1 | Minimal FFmpeg and fixtures | done | CI runs 39693880471 and PR #2 run 39694259434 passed; 17 formats plus Unicode and long path passed, three invalid inputs rejected | - |
| M1-A4 | M1 | Model conversion pipeline | done | CI run 39691863874; ten candidates, VAD, and manifest uploaded to draft `models-v1` | - |
| M1-A5 | M1 | Verify engine flags and output | done | Desktop CPU, Vulkan, VAD, JSON, progress, and prompt limit documented in `docs/dev/engine-cli.md` | - |
| M1-A6 | M1 | Bench tooling and accuracy reference | done | Source-text-only spans in `swineherd-scored-spans.json`; 20 desktop public runs scored; four scorer tests passed | - |
| M1-A7 | M1 | Bench kit draft prerelease | done | Drafts `bench-kit-m1` and `bench-kit-m1b`; new kit 46,254,971 bytes, SHA-256 `16f94ad209be637ae41e1dda61b619d68e4b32a2bf2e8010ad848e64efaad1cc` | - |
| M1-B1 | M1 | Proxy hardware and gate decision | done | PM approved ThinkPad i7-1365U/Iris Xe 96EU proxy, estimated 20% faster than Surface, RTF target 0.8; `docs/pm/benchmarks/m1/README.md` | - |
| M1-B2 | M1 | Correct WER scoring and preserve desktop results | done | `be02def`, `11031b9`; 20 public JSON files scored on three Gutenberg-only spans; private files contain timing only | - |
| M1-B3 | M1 | Distinct result names and Quick mode | done | `fa17ee9`; public/private smoke tests and overwrite rejection passed; local Quick check ran both backends | - |
| M1-B4 | M1 | Record Iris Xe startup concern | done | `docs/pm/issues/ISSUE-004-iris-xe-startup-cost.md`; resolved in M2 with Owner measurements and PM decision | ISSUE-004 (resolved) |
| M1-B5 | M1 | Revised draft bench kit | done | `bench-kit-m1b` uploaded as draft and verified; original draft retained | - |
| M1-B6 | M1 | ThinkPad results and final gate report | done | 10 CPU and 10 Vulkan public runs at four threads, 20 matching JSON files; Gutenberg-only WER computed for all; `docs/pm/reports/M1-report.md`; PR #2 checks passed at runs 39718968447, 39718973895, 39718973892, and 39718973902 | - |
| M1-B7 | M1 | Focused Quick thread sweep | done | `b1f3ac0`; local 4, 8, 10 thread smoke test produced three rows each on CPU and Vulkan; draft `bench-kit-m1c` verified | - |
| M1-GATE | M1 | PM gate decision | done | Conditional GO per M2 brief; PR #2 merged as `d3a35f7`; `docs/adr/0016-v1-model-catalog.md` records accepted catalog | - |
| PRE-M7-SURFACE | M7 | Real Surface Laptop 5 Vulkan smoke test | todo | Owner-owned M1 conditional GO item; required before M7, does not block M2-M6 | - |
| M2-01 | M2 | Pinned engine and model assets for dev and CI | done | Published `engine-v1` digests matched three pins; fetch script verified engine archives, manifest, tiny, small.en, and VAD; PR #3 checks passed in runs 39722358788 and 39722363339 | ISSUE-005 (resolved) |
| M2-02 | M2 | Headless core pipeline | done | Public engine-v2 full local suite: 76 passed; PR 39813686035 and push 39813676982 green, including controls/recovery, collisions, Medium translation, canary and policy checks; mypy 43 files; actual Vulkan agreement passed locally, absent-device comparison skipped on CI | ISSUE-006, ISSUE-007, ISSUE-008 (resolved) |
| M2-03 | M2 | ISSUE-004 startup probe and findings | done | Owner ThinkPad exit 0: CPU 0.940/0.760/0.750/0.751/0.752 s, Vulkan 1.000/0.627/0.617/0.633/0.644 s; load 85-93 ms, encode 85-92 ms; PM closes ISSUE-004, ADR 0004 unchanged; `startup-probe-thinkpad.md` | ISSUE-004 (resolved) |
| M2-04 | M2 | VAD integration check | done | Active published engine-v2 passed native CPU CI, desktop CPU/Vulkan and PR 39813686035; outside-span segment words 22 before, 0 after; word timestamp violations 0 after on both backends; 0.5 s tolerance; `engine-v2-desktop.md` | ISSUE-007 (resolved) |
| M2-05 | M2 | Persian translation fixture | done | Public-domain Persian quatrain, 15 seconds, independent 1883 reference; PM-recommended Medium retains original keyword plus stronger source-content checks; local full suite and PR 39813686035 / push 39813676982 passed | ISSUE-008 (resolved) |
| M2-06 | M2 | CI offline and WFP network isolation | done | Published engine-v2: PR run 39812231667 offline job 119941284787 passed; run 39812652065 offline job 119942750382 passed; exact new CLI contract verified, positive blocked-event control, self-test/batch, zero processing events and cleanup | ISSUE-007 (resolved) |
| M2-07 | M2 | Approved engine-v2 native correction | done | Owner published prerelease engine-v2; `d3ed49c` active pins; public downloads verified all five digests; green PR 39812231667 and run 39812652065 include VAD and WFP; upstream patch retirement in BACKLOG.md | ISSUE-007 (resolved) |
| M2-HK | M2 | Optional-work backlog and escalation scope | done | Owner instruction 2026-10-22; `BACKLOG.md` records deferred optimizations and SPEC section 3.2 scope; AGENTS rules 11 and 15 keep independent required M2 work moving | - |
| M2-08 | M2 | Unit acceptance: folder scanning, failure mapping, invalid preferences | done | Full public-engine suite: 76 local tests; PR 39813686035 green; core 95.2%, export 98.5%, models 94.4%, queue 91.7%, privacy 95.1%, total 93.9%; scanner, actionable failure messages, malformed preferences and missing Done outputs tested | - |
| M2-09 | M2 | Coordinator controls, live progress and Windows sleep prevention | done | Focused lifecycle tests: 14 passed; final full suite: 76 passed; PR 39813686035 / push 39813676982 green; numeric progress delivered before child exit, cancel-current continues batch, prior execution state restored on failure | - |
| M2-10 | M2 | Confine test application state to the repository | done | `d49be69`; fixed explicit test RuntimePaths and autouse LOCALAPPDATA isolation under repo-local pytest temp; 8 focused tests and full suite 76 passed after isolation; approved external backend_probe-only cleanup completed and verified before M3 | - |
| M2-11 | M2 | Required V2 interface stubs and changelog | done | SPEC 5.9 interfaces only, no dependencies or implementations; pipeline hook documented after parsing; ruff, formatting, mypy (43 files), and all policy checks passed | - |
| M3-01 | M3 | Archive brief and protect real app data in tests | done | M2 accepted and merged as 8b9ecab; briefs committed unchanged in 325973b; approved backend_probe cleanup completed and verified in prior turn; guard rejects protected reads, writes, listing, mkdir and unlink before access; 3 focused tests passed | - |
| M3-02 | M3 | Simple-mode window, options and model rules | done | 7551944; centralized copy, verified 100-language list, backend defaults, translation/English-only rules, explicit missing-resume-model replacement; local and PR tests pass | - |
| M3-03 | M3 | Worker, progress, cancellation, collision and recovery UI | done | 7551944; native QThread workers, actual batches, cancel-current, apply-all and close/save/resume; PR 39827402358 green, WFP gui passed with connection_events=0 | - |
| M3-04 | M3 | Qt acceptance tests and real-batch responsiveness | done | Final 106 local tests; 23 GUI/theme/presentation tests; 200 ms responsiveness gate passed; strict coverage 94.2%; PR 39854200159 and push 39854194307 green (105 passed, 1 unavailable-Vulkan skip) | - |
| M3-05 | M3 | Screenshot matrix and draft release | done | 164 PNGs in m3-screenshots-final-polish.zip, SHA-256 031f699e9f6abaf2bfb0eb1d6571fe8a30da0eabe11e45b04329a6f38c540f2c; still draft with older assets retained | - |
| M3-06 | M3 | Owner walkthrough and M3 report | done | All eight ThinkPad re-tests PASS functionally; PM accepted and Owner merged PR #4 as e66788b | - |
| M3-07 | M3 | Sync warning privacy review | done | Read-only documented Google Drive mount detection and injected-reader tests; final local and PR CI passed, advisory limits documented | ISSUE-009 (resolved) |
| M3-08 | M3 | PM screenshot corrections before walkthrough | done | b1d9552, d728563, 26cf74b, 3df3cae; all requested changes, 99 local tests, green PR 39840103768 / push 39840090723 with WFP zero connections; new screenshots uploaded, report/checklist revised | ISSUE-010 (resolved) |
| M3-09 | M3 | ThinkPad walkthrough corrections | done | d58e629, 62dc03d, b4c9ae5, 1ff2327; AMR root cause fixed, output/model/run-flow/copy/keyboard changes covered by 106 local tests; PR/push CI green; optional recommended-model fetch verified; screenshot/report/re-test checklist ready | ISSUE-011, ISSUE-012 (resolved) |

| M3-10 | M3 | Final ThinkPad polish after eight functional passes | done | 112 local tests, green PR CI 39889192873 (111 passed/1 hosted Vulkan skip), WFP zero events; final screenshot asset uploaded, polish accepted and merged by Owner | - |
| M4-D1 | M4 | PM-authorized downloader-only prework | done | Branch m4-downloader based on m3-gui 9efea1f; cf299a8; stdlib CLI and verified exact host chain; 129 local tests plus 1 CI-only skip, all quality gates passed; no offline/GUI source changes or PR to main | - |
| M4-D2 | M4 | Explicit CI-only Tiny download and isolation evidence | done | Push run 39857544641 green: 128 passed, 2 expected skips; real-network test 1 passed in 3.87 s; WFP GUI/headless zero connections; M4-interim-1.md written and stop | - |

| M4-R1 | M4 | Preserve Owner brief and rebase feature branches | done | Owner brief preserved byte-for-byte in stash and build/m4-transition; M4 rebase tests 135 passed/1 CI-only skip, M5 165 passed/1 skip; both pushed with explicit feature-branch leases; M3 brief archived and unchanged M4 brief committed as 7de0372 | - |

| M4-01 | M4 | Carry-over Start layout, recommendation labels and dark contrast | done | Start stays full width (including running/disabled), centered reason above; recommendation suffix simplified; dark disabled text contrast tested at least 4.5:1. Alt+Arrow routing handles table shortcut overrides explicitly; 25 Qt/theme tests and lint/types pass | - |

| M4-02 | M4 | Model Manager and isolated downloader child | done | aab3ec6; 149 local passes/1 CI-only skip, 94.2% coverage, CI 39910270912 green; source and packaged WFP GUI=0/fetch allowed=4/blocked=0; report and draft screenshot evidence | - |

## M4 checkpoint, 2026-10-22 - stopped at the Owner's usage request

### Done

- Main is the Owner-merged M3 revision e66788b. M4's own commits were rebased
  onto main, then M5's own packaging commits onto rebased M4. Both feature
  branches were pushed using explicit force-with-lease guards; main was not rewritten.
- Rebased full suites passed: M4 **135 passed, 1 CI-only skip**, 94.2% strict
  coverage; M5 **165 passed, 1 CI-only skip**, 94.4%. Logs are repository-local
  build/m4-transition/rebased-m4-tests.log and rebased-m5-tests.log. These runs
  precede the Model Manager changes and are not final M4 acceptance evidence.
- Owner's uncommitted M4 brief was copied byte-for-byte and stashed with the
  pending engineer M3 report before branch changes. Brief SHA-256:
  528329b1f13884503500fcbfe3d87200348839249ef554f14a98c7964b6774b3.
  Recovery copies and hashes remain in build/m4-transition; the stash is retained.
- Archived main's M3 brief to briefs/M3-brief.md, restored the Owner's M4 brief
  unchanged, and committed both as 7de0372. The pending M3 report evidence was
  recovered and committed separately in 9a7ff51. SPEC was not edited.
- First three M4 nits committed/pushed in 67a9a7b: full-width Start, centered
  disabled reason above, ', recommended' labels and higher dark disabled-text
  contrast. Actual Alt+Arrow handling now routes table shortcut overrides
  explicitly after the active-window precondition alone proved insufficient.
  **25 Qt/theme tests passed**, plus lint and types.
- Model Manager WIP **66461dd** is committed and pushed on m4-downloader.
  It lists five transcription models plus bundled voice detection, displays
  verified/missing/damaged/downloading state and free space, confirms the named
  download files and total size, and parses progress from a separate Job Object
  child. Cancel/close keeps resumable parts; deletion protects the selected/last
  transcription model and voice detection while in use. Verify all re-hashes.
- Options and Tools open the manager; missing recommendations have Download it.
  No-model Start guidance and live installed-choice updates are implemented.
  An implicit recommendation becomes selected when available; explicit choices
  are preserved. Required voice detection is included in the explicit consent
  and download plan; missing/damaged voice detection blocks default VAD use.
- Local TLS tests exercise real child downloads, progress, consent rejection,
  cancel/restart resume, hash mismatch, verification, deletion rules, immediate
  model-choice updates, missing-model prompts and closing cancellation.
  **31 focused Model Manager/GUI tests passed** before the final PID change.
  Development and split-package command resolution have unit coverage.

### In progress / not yet verified

- Final additive CLI JSON metadata now includes the real downloader PID, parsed
  by the GUI for later WFP attribution (Windows launcher PIDs may differ).
  This last change has passed lint/types but **has not been rerun through the
  tests**. Existing downloader operations/hosts were not redesigned.
- Latest lint and mypy passed (56 source files). The static no-network checker
  passed during implementation with zero exceptions. The full suite, all policy
  checks and final CI have not been rerun against 66461dd; no green final-M4
  or packaged-integration claim is made.
- No Model Manager download WFP scenario, WFP PID/count report, M4 screenshot
  renderer/asset or M4-report.md exists yet. No M4 PR was opened.
- M5 is rebased and tested through the transition at M4 1f583fc; it **does not
  yet include** the new M4 brief, first nits or Model Manager WIP. Its packaging
  code/CRT pins and split-layout safeguards were preserved during that rebase.

### Next, in order

1. Verify the PID addition with the focused Model Manager and downloader tests;
   resolve any real failures, then run the full M4 suite and all quality/policy gates.
   Cover remaining main-window/manager shutdown and entry-point integration as needed.
2. Implement the real CI-only Model Manager download WFP scenario using the actual
   manager/controller. Require zero GUI connection events and report the separate
   downloader count. Attribute the real process IDs, including source Python
   launcher behavior; retain calibrated source offline acceptance.
3. Document the child command paths, JSON PID metadata and network audit method.
   Generate M4 screenshots for manager states and main prompts in both themes/scales;
   create/upload only to a new draft m4-screenshots release. Do not publish it.
4. Rebase m5-packaging-spike onto completed m4-downloader again; preserve stdlib
   DOCX, exact platform/Owner CRT pins and split layout. Rerun its suite and
   packaged build, PE gate, license gate and packaged WFP self-test, including
   GUI-to-downloader use in the split layout. Push with a feature-branch lease.
5. Record verified CI/test/WFP counts, screenshot link and about six ThinkPad
   checks in M4-report.md, then stop. Do not open a PR against main until PM acceptance.

No further implementation or tests were started after the Owner requested this checkpoint.


## M4 overnight continuation, 2026-10-23

- Recovered clean m4-downloader at 3883ef7; no uncommitted work to preserve.
- Checkpoint protocol suite now passes 31 tests, including exact cancellation
  event/PID metadata. Added entry/menu/main-window shutdown coverage: 12 manager
  tests passed, plus the guarded real GUI/local-TLS exercise passed separately.
- AUDIT-NOTES.md records the requested private cache API review and other
  non-urgent boundaries for the independent M6 audit; no optional refactor started.
- Model Manager WFP scenario is implemented for source and split-package paths,
  with real GUI/consent exercise, calibrated auditing and separate GUI/fetch PID
  counts. Local tests use only TLS loopback; Windows firewall changes remain CI-only.
- Next: obtain real CI WFP evidence, complete screenshots and full M4 gates,
  then sync/reverify M5. Installer drafts are separately authorized only after that.

### M4 acceptance evidence, 2026-10-23

- Full local suite: 149 passed, 1 CI-only skip in 169.01 s; strict-package coverage
  94.2% (core 93.7%, export 98.5%, models 94.4%, queue 93.0%, privacy 95.2%).
- Ruff, format (98 files), mypy (58 source files) and all three policy checks passed.
- CI run 39909561630 at 01bcc73: checks and offline both green, including the real
  public-release integration and calibrated Model Manager download WFP scenario.
- Download WFP: GUI 0 connection events; downloader 4 allowed, 0 blocked;
  positive control blocked event present. Model and voice detection verified,
  consent confirmed, guard installed. Redacted artifact: m4-download-audit.
- Added reproducible synthetic M4 screenshots: 19 states x two themes x two
  scales = 76 PNGs. Visually checked main prompt, dark manager/progress and
  150% consent; upload to the new draft release is next.
- Remaining: draft screenshot upload, report, M5 rebase and packaged acceptance.

### M4 engineering complete, Owner morning review pending

- M4-report.md records all acceptance evidence, branch scope, draft screenshots,
  source and packaged WFP counts, exact Persian fixture provenance, and six
  ThinkPad checks. PM/Owner hardware review remains pending; no PR opened.
- Screenshots are a new draft m4-screenshots release, not published. M5 was
  synchronized and its app gates passed in 39910562031. Optional installer
  prework remains isolated to M5; its compilation follow-up is not M4 acceptance.

### M4 final morning handoff

- M4 engineering complete and CI green at 34256af / 39913841073; final report
  adds documentation only. Screenshot draft remains m4-screenshots-aab3ec6.zip.
- ThinkPad app review: 39916465602 artifact m4-review-bundle; no clone/Python
  needed. Six-step isolated-profile instructions are in M4-report.md.
- Synchronized M5 app gates all pass on final code 0adc037: source 188 passes,
  2 expected skips; local 189 passes/1 skip, 94.5%; PE/license/GUI and WFP pass.
- Optional installer compiles but binary upload is intentionally held for M5
  ISSUE-017 / proposed ADR 0023 (InnoSetup not in the allowlist). No exception
  was granted by the engineer. Morning PM policy decision and later VM checks
  are documented; no PR, merge, publishing or repository-setting change.
- No em/en dash matches in the report's recorded repository search; no SPEC or
  Owner brief edit. Final M5 rebase carries this documentation only, then stop.
| M5-S1 | M5 | Authorized packaging-only spike | done | Final split onedir layout verified locally and in 39884809028; windowed GUI/console fetch, shared verified bin/resources; 205 files, no models bundled | - |
| M5-S2 | M5 | Actual bundle license inventory, notices and CycloneDX SBOM | done | 39884809028: 205 actual files, 12 providers, schema-valid CycloneDX 1.6, complete notices/EULA and license gate passed; final evidence in M5-interim-4.md | ISSUE-013 resolved |
| M5-S3 | M5 | Packaged self-test under calibrated WFP audit | done | 39884809028 packaging job: selftest passed, connection_events=0, calibration_blocked_event=true; source offline job green; local CPU/Vulkan and GUI smoke passed | - |
| M5-S4 | M5 | Redistribution license clearance | done | ADR 0020/0019; 39884809028 packaging job license gate passed, 205 actual files/12 providers, original notices and protective EULA retained | ISSUE-013 resolved |
| M5-S5 | M5 | Processing native dependency network boundary | done | Runtime lxml removed; calibrated packaged WFP zero events, 64-PE exact-pin gate, GUI smoke and full local 159-pass suite; docs/dev/packaging-offline-pe-final.md | ISSUE-014 resolved; ISSUE-015 resolved |
| M5-S6 | M5 | PM-approved DOCX, split bundle and license remediation | done | f266d98 implementation fully green in 39884809028; 159 local passes/1 skip, 158 CI passes/2 expected skips plus real-network pass, coverage 94.4%; final report M5-interim-4.md | ISSUE-013/014/015/016 resolved |
| M5-S7 | M5 | ADR 0019 standard-library DOCX implementation | done | 5ba88dd; unchanged DOCX goldens plus python-docx openability/Unicode/empty metadata pass; runtime closure and bundle exclude docx/lxml, export coverage 98.6% | ISSUE-014 resolved |
| M5-S8 | M5 | Owner-verified Persian fixture documentation | done | m3-gui docs-only 2a6e065 pushed; Owner confirmed [107, 122) s is a complete Farsi quatrain; AUDIO_SOURCES.md and M3 report updated | - |
| M5-S9 | M5 | Community redistribution evidence and protective terms | done | Owner exact regular CRT pins f266d98; 11 needed copies/5 names byte-identical locally and in CI, hashes/versions/importers and 3 original PDFs retained, EULA included, future installer checklist updated | ISSUE-013 and ISSUE-016 resolved |

| M5-S10 | M5 | Carry final accepted M3 UI polish | doing | M3 merged locally into spike; GUI smoke profile now declares its explicit synthetic output folder so it tests the main window under the folder-based Welcome rule; final CI pending | - |

### M5 resync with M4, 2026-10-23

- Rebased all 19 packaging commits onto M4 aab3ec6; conflicts were limited to
  additive workflow jobs and ledger task states. Retained current M4 evidence,
  accepted M5 issue resolutions, split runtime paths, stdlib DOCX and exact PE/CRT pins.
- Feature rebase d402a38 pushed with explicit lease; no main changes or PR.
- Added the packaged Model Manager download WFP scenario to packaging CI and
  artifact evidence. Full rebased suite running; bundle/PE/license/GUI/WFP results pending.
- M4 screenshot draft uploaded: m4-screenshots-aab3ec6.zip, 76 PNGs, 3605372 bytes,
  SHA-256 1d7d30ea6d3e83824502f77dcfd22122f5178be8f2800ebeccdebcb15594e7f6.

### M5 synchronized bundle acceptance, 2026-10-23

- Local full suite: 179 passed, 1 CI-only skip in 197.64 s; coverage 94.4%.
- Rebuilt split bundle: 205 files, 161929803 bytes. Layout, all 64 PE exact-pin
  checks, packaged GUI window startup/close, notices/SBOM and bundle licenses pass.
- CI 39910562031 at 5ca1180: packaged job green, original offline self-test
  connection_events=0; packaged Model Manager GUI events=0, fetch allowed=4,
  fetch blocked=0; both positive controls calibrated. Source offline job green;
  full checks job still running at this checkpoint.
- Optional installer prework is starting only on m5-packaging-spike. Inno Setup
  stays at approved major 6, pinned stable 6.7.3; no local machine installation,
  publishing, PR or Owner settings changes. Fresh-machine acceptance remains Owner work.

### Installer prework: safe data cleanup

- Added a hidden offline uninstall entry point on M5 only. Removes recognized
  settings/history/log/work files and optionally catalog model files; preserves
  unknown content, output folders and recordings. Refuses linked/junction data
  and corrupt protection metadata. An overlapping saved output prevents cleanup
  before any metadata is deleted, so subsequent attempts remain safe.
- Five cleanup tests passed (including both keep/remove model choices); two
  generator license/trust-anchor tests passed. No cleanup ran against real app data.

### Installer prework: generated draft and pinned compiler

- ADR 0022 records the PM's bundled dusty-fetch decision. Generator retains the
  manifest trust anchor, creates full Apache/NOTICE/Microsoft EULA acceptance,
  catalog selection plus VAD, verify/reuse/download/verify and self-test gates.
- Per-user lowest-privilege layout, Start Menu/optional Desktop shortcut, retry,
  incomplete exit code, child Job Object containment and model-removal checkbox
  drafted. Safe cleanup tests pass; no Owner machine installation or data cleanup.
- Inno 6.7.3 official bootstrap SHA pinned; CI compilation/artifact only. Source
  license retained, SmartScreen/checksum guidance added. Seven focused tests pass;
  real compilation, full regression and fresh-machine behavior still need evidence.

### Installer draft verification follow-up

- Full local regression after draft additions: 186 passed, 1 CI-only skip in
  184.24 s; strict coverage 94.5%. Seven focused license/cleanup tests pass again.
- CI 39912687607 packaging job passed all app bundle, PE, GUI, license and WFP
  steps but stopped before compilation at Unexpected Inno compiler version.
  The text FileVersion check did not expose its numeric identity; changed to
  exact numeric 6.7.3 fields with both forms printed, retaining the bootstrap hash pin.
- Cleanup now reports preserved unknown content instead of silently implying
  complete removal. Added independent audit notes for ownership and the Inno ABI.

- Verified pinned upstream ISCC.dpr and its binary version resource: launcher
  FileVersion is intentionally 0.0.0.0. The actual engine is reported by
  ISDllGetVersion in the compile banner. Replaced the incorrect launcher version
  assumption with exact engine-banner 6.7.3 verification, retaining bootstrap SHA.

- Actual engine banner verified as Inno Setup 6.7.3 in 39913542021. Compilation
  then rejected generated line 211: Invalid section tag. An indented Pascal
  array literal began with '[' at line start, which Inno's section parser treats
  as a section. Moved the bracket onto the preceding expression; no behavior or
  acceptance gate changed. M4 report sync rebase changed only docs/ledger.

- Hardened uninstall ownership further: unfamiliar metadata schemas are preserved,
  and discovery-time filesystem failures return the same redacted failure result.
  Eight focused installer tests pass. Added the stale README introduction to the
  M6 documentation backlog instead of widening this milestone's product scope.

- 39914143568 reached Pascal compilation; line 260 rejected the pre-6.6
  CreateCustomForm signature. Verified the documented four-argument 6.7.3 API,
  updated the constructor and removed obsolete writable size properties.
- Compiler bootstrap now also compares its installed license text with the
  pinned source terms, in addition to the binary hash and exact engine version.

### ISSUE-017: installer-only license policy gap

- SPDX identifies the pinned wrapper license as InnoSetup, distinct from the
  allowlisted BSD/Zlib names. ADR 0008 selects the tool but does not record a
  license exception. Filed S1 ISSUE-017 and proposed ADR 0023; no allowlist change.
- Cancelled our own 39914802080 before its installer compile/upload steps; no
  workflow was deleted. App bundle remains separately audited and allowed.
- Added an installer-wrapper gate using allowed_license plus a negative test.
  It intentionally fails pending PM clearance, and installer binary upload is
  downstream. Audit metadata remains available even on failure. Nine focused
  installer tests pass. Continue compilation and M4 documentation independently;
  this is a morning policy decision, not an observed S0 license violation.

- 39915503372 compiled the unsigned draft successfully (34586726 bytes,
  SHA-256 8f7d644fe54570e16a4ee841f96060348b91d33f52a5cfe39266188c522bdc45).
  The installer policy gate then failed exactly for InnoSetup; binary artifact
  skipped, audit metadata retained. App review artifact is separately available.
- Final cleanup regression also preserves empty internal output folders and the
  metadata protecting them across repeated attempts. Ten focused installer tests
  pass; the draft is not installed on the Owner machine. Final CI rerun follows.

### Final overnight code verification, 2026-10-23

- 0adc037 local full suite: 189 passed, 1 CI-only skip in 174.00 s; 94.5% strict
  coverage. CI 39916465602 source checks: 188 passed, 2 expected skips in
  274.44 s, real-network integration and all quality/app policy gates passed.
- Earlier 39915503372 source run missed the 200 ms responsiveness limit at
  229.671 ms; final run passes the unchanged test. No skip, retry plugin,
  threshold increase or product workaround was introduced.
- Final packaged app: 207 files/161936952 bytes, all 64 PE pins, license gate,
  GUI smoke and both WFP scenarios pass. Offline processing 0; Model Manager
  GUI 0, fetch allowed 4/blocked 0, calibrated controls and verified assets.
- Final installer compiles: 34593012 bytes, SHA-256
  a63903ef8020bc4e469365fb36aa88b5ae68e518124dbde0acf0882a2da0b632.
  Only the installer wrapper license gate fails as intended (ISSUE-017); binary
  upload skipped, audit artifact retained. No unallowlisted binary was shipped.
- M5-interim-5.md records the morning license decision and remaining VM/release
  acceptance. M4 app review artifact: run 39916465602, m4-review-bundle,
  artifact 12484769263. Final cross-branch report/documentation sync is next.

### Final branch synchronization

| ID | Milestone | Task | Status | Evidence | Issues |
|---|---|---|---|---|---|
| M5-R2 | M5 prework | Carry completed M4 and final handoff forward | done | Rebased onto M4 3b874d3; diff against pre-rebase 87f08cb contains only M4 report/ledger, implementation unchanged; final code gates remain 39916465602 evidence | - |
| M5-P1 | M5 prework | Per-user installer source, compiler and safe cleanup | done for prework | Compiles with pinned 6.7.3; 10 focused tests; final local 189/1 skip and CI 188/2 skips; full VM acceptance remains future work | - |
| M5-P2 | M5 prework | Installer wrapper license clearance | blocked | InnoSetup rejected without an engineer exception; binary upload skipped; audit metadata and proposed ADR 0023 retained | ISSUE-017 |
| M5-P3 | M5 | Complete installer-wide inventory, installed-app audit and VM/release gates | todo | After PM license decision: complete wrapper/subcomponent SBOM and notices, rerun license/installed-app WFP, then Owner standard-user VM checklist and Owner-controlled release | ISSUE-017 |

Both feature branches are pushed. No implementation changes were made during
this final report rebase; no additional optional testing or next-milestone work
is needed. Return the workspace to m4-downloader with a clean tree for the Owner.

### PM-approved overnight continuation, 2026-10-23

- ISSUE-017 resolved: ADR 0023 Accepted by PM, exact InnoSetup exception only in installer context. App dependencies still reject it; focused positive/negative test passes.
- Installer-wide inventory and CI lifecycle acceptance now in progress. M6 docs and desktop long-recording tests explicitly authorized by PM; Owner machine install is not required tonight.

### Installer acceptance and static inventory checkpoint

- Implemented explicit silent terms/download consent and explicit keep/remove-models uninstall choices; interactive choices remain unchanged. CI lifecycle harness covers installed WFP self-test, PE gate, verified Tiny/VAD, upgrade with downloader blocked, both uninstall modes and untouched output sentinel. Verification is pending CI, not claimed passed.
- Extended installer SBOM/notices with source-identified static components. ISSUE-018 records six unapproved/provenance findings; installer artifact remains blocked. ISSUE-017 wrapper-only approval remains resolved. Eleven focused installer tests now include narrow scope and inventory/notice tamper regressions.
- Desktop packaged long-recording Small CPU run is active in an isolated repository profile; no Owner app-data writes. CIM initially needed approved escalation. Turbo Vulkan follows automatically.

- Long-recording harness/provenance checked in: repeated public-domain Swineherd, 7920.1875 s, packaged shared coordinator, CPU Small then Vulkan Turbo, VAD on, isolated profile. The run is still active; no measurements or cleanup success are claimed yet. M5 checklist now distinguishes CI automation from remaining standard-user VM acceptance.

### Installer CI follow-up

- CI 39923879707: checks and source offline pass; compiled installer installs, downloads Tiny/VAD, passes installed calibrated WFP (0 events) and 64-PE gate. Lifecycle then fails because harness assumed unins000.exe. Pinned Setup.Install generates uninsNNN names; harness now reads the exact per-user registered UninstallString, validates its folder and reports the phase. Next CI run must establish both uninstall results.
- Installer-wide gate reports five static license entries plus unresolved Delphi provenance; no installer artifact uploaded. M6 guides pushed separately at a206740. Local full suite: 190 passed/1 skip, 94.5% strict coverage.

- Added installed-file inventory: every payload file must match the audited bundle, with only the exact Inno notice and generated uninsNNN runtime records allowed. Changed/extra-file negative test passes; inventory is retained with acceptance evidence.
- Desktop Small CPU endurance completed: 7920.1875 s input, 1060.9096 s wall, RTF 0.13395, sampled tree working set 2612928512 bytes, work bytes 253446078, exit 0, done on CPU, zero remaining work files. Turbo Vulkan is active. Final benchmark summary awaits both runs.

### S0 containment and final overnight handoff

- ISSUE-019 OPEN S0: ac06dad enabled the exact wrapper exception before the full static inventory. Run 39922816919 uploaded m5-installer-draft-unsigned, artifact 12488875272, compressed 34115983 bytes. Installer 34591385 bytes, SHA-256 f70f1ede9923d605f3ec1b3d072a1f4ed7c9e3d4da3c7fb2111fb05af64ec14d. Owner must remove this artifact; the agent cannot delete it. All implementation stopped on discovery.
- Later run 39924971496 at 126aedb completed all installer lifecycle checks: explicit silent per-user install, bundled Tiny/VAD download, installed WFP self-test with 0 events, 64-PE gate, blocked-downloader upgrade with unchanged model hashes/mtimes, both uninstall choices, unchanged external output sentinel. Only the intended installer-wide license gate fails; binary upload skipped. CI checks: 189 passed/2 expected skips; separate network integration 1 passed.
- Source and packaged WFP processing 0; Model Manager GUI 0, fetch allowed 4/blocked 0 in both layouts. App license and GUI gates pass. Payload 213 files/161951722 bytes. Final installed-file identity gate has a passing negative unit test but its final CI run was cancelled for the S0 stop.
- Requested cancellation of active CI 39925428852 and 39925218957. 39924971496 was already completed. Stopped the remaining local final-coverage process tree; its unfinished run is not evidence. No release/PR/merge/settings change, no artifact deletion.
- Both endurance runs had completed before discovery: Small CPU 1060.9096 s/RTF 0.133950; Turbo Vulkan 268.3786 s/RTF 0.033885 for 7920.1875 s public-domain repeated audio. Both Done/exit 0, requested backend, zero work files AND directories. Summary in docs/pm/benchmarks/m6/desktop-long-recording.md; raw files remain ignored.
- M6 docs pushed separately at a206740: user guides, privacy, CONTRIBUTING, README. Exact HIPAA paragraph, local links and dash checks pass. No M6 app code. That branch still needs later M5 follow-ups carried forward after authorization to resume.
- M5-interim-6.md records Owner morning actions, incident root cause, all completed evidence and incomplete gates. Next: Owner removes artifact and PM reviews static licenses/S0, then authorizes resumption and final CI/VM acceptance. No further implementation while S0 is open. Incident documentation uses [skip ci] only to preserve the stop; no skipped run is claimed green.

### PM-authorized installer license resolution and resumed acceptance

- Owner deleted artifact 12488875272; read-only API returns HTTP 404. PM reclassified ISSUE-019 to process S1, resolved with upload gating and a negative CI regression. No further containment required; work resumed as instructed.
- ISSUE-018 resolved by ADR 0023 amendment: exact installer-only unmodified runtime exceptions. Pinned source/build review selects Setup.e32 + SetupLdr.e32, verifies Pascal Script references and only NewUxTheme/NewUxTheme.TmSchema JEDI units. The original two source files and full MPL are retained for the installer, with exact source hashes and all component notices. App allowlist unchanged.
- Added explicit upload condition and source/offline/negative-regression dependencies; live CI test deliberately fails a synthetic license gate and asserts upload is skipped. Nine focused tests pass. Full source/installed/licensing/CI revalidation next; no final pass claim yet.

- Resumed source gates: ruff/format (124 files), mypy (69 sources), three source policies pass. Actual generator script command exposed a tools import-path regression; fixed its direct-script path setup and added a subprocess entry-point regression. The targeted pytest attempt collided with the active full run using the same .pytest-tmp and produced 3 setup errors (WinError 32); the initial pass-count note was incorrect and is corrected here. The real --help command now succeeds. A serial full rerun is required.

- Added retained-source tamper coverage and compiler-bootstrap receipt verification. The failed concurrency attempt is not acceptance evidence; final full source/CI checks will run with one pytest process per workspace.

- Serial final source suite: 197 passed/1 CI-only skip in 179.59 s, strict coverage 94.5%. Earlier overlapping-pytest attempt had one GUI resume failure after temp deletion plus 3 setup errors; no test was weakened. Local split bundle, app license, GUI smoke and 64-PE gate pass.
- CI 39984075122 found a source-fetch HTTP 404: the earlier pin c7af86b is an annotated tag object, not its commit. Verified GitHub git/ref -> git/tag -> commit 4adf37ed7f3fd2bd11c6836ba056e3de170fbabf, corrected provenance/current docs, retained both IDs. All reviewed source/JEDI hashes verify from that exact commit; actual original-source ZIP generation and 7 focused regressions pass. Binary/version unchanged. Final CI rerun follows.

### Resumed M5 acceptance complete, 2026-10-23

| ID | Milestone | Task | Status | Evidence | Issues |
|---|---|---|---|---|---|
| M5-P2 | M5 prework | Scoped wrapper and static runtime license approval | done | ADR 0023 amendment; pinned actual units, complete notices and original JEDI source; installer license gate green 39985711346 | ISSUE-017/018 resolved |
| M5-P3 | M5 prework | Inventory and installed acceptance gates | done for CI | 216 payload files/161989319 bytes; 221 installed files byte-checked; 64 PE gate; installed calibrated WFP 0; full lifecycle passes | VM manual acceptance remains |
| M5-P4 | M5 prework | Upload ordering regression | done | Synthetic failing gate produces skipped upload; production requires source/offline/regression + successful license/installed gates; green 39985711346 | ISSUE-019 resolved process S1 |
| M6-D1 | M6 prework | Carry current M5 into docs branch | done | M6 e1c7758 carries the complete M5 implementation and interim-7 report, docs-only delta | - |

- Final code CI 39985711346 at fa5fbcb: all four jobs green, source 196 passed/2 expected skips plus real-network integration 1 passed. Local serial 197 passed/1 skip, 94.5% strict coverage; lint/types/policies pass.
- Unsigned installer only as CI artifact 12516525534, 34618916 bytes, SHA-256 4ea17b60157593ff989c06e9d6d8e745b8e25ba61f0bb77478706ee58e1a2720. No release upload. Full notice/SBOM/runtime/installed acceptance audit artifact 12516480610.
- Source, packaged and installed processing WFP events 0. Source/packaged Manager GUI 0, fetch allowed 4/blocked 0. Silent install with Tiny/VAD, verified upgrade while downloader blocked, both uninstall choices and unchanged output sentinel pass. Owner clean-VM checklist remains.
- M5-interim-7.md supersedes historical interim-6 stop instructions. No outstanding containment or license decision for ISSUE-018/019. Final report-only branch heads will be checked in CI before handoff; no new product work begins.


### M4 Owner review corrections, 2026-10-23 (in progress)

- Owner ThinkPad packaged app: all six M4 checks passed functionally.
- M5 ISSUE-018/019 checkpoint is clean and pushed at 0e70c31; its final CI
  39987858934 is green. M6 checkpoint ca1ac2a is pushed; CI 39987905683
  timed out in the real CPU self-test entry-point guard test (30 seconds).
  No failure was hidden; carry-forward acceptance will rerun the complete suite.
- PM replaced earlier cancel/resume UX: Ctrl+C/cooperative cancellation removes
  the partial. GUI cancellation also removes it after joining the terminated
  downloader child. Existing Range integrity checks remain for network failures.
- Focused downloader/GUI first run: 57 passed, three GUI expectations needed
  adjustment for the new labels/style and missing recovery-model selection.
  After correcting recovery behavior, focused GUI/manager/theme tests: 42 passed.
- In progress: unrestricted model deletion, explicit cleared Options selection,
  three-line catalog/Best for column, consent, contextual prompts and disabled
  styling. Next: full suite/coverage, fresh screenshots, CI, carry to M5/M6,
  packaged PE/license/GUI/WFP gates and final M4 report.


### M4 UX implementation checkpoint

- 42 focused manager/GUI/theme tests pass, including selected/last/VAD deletion,
  no automatic replacement, persisted empty selection, automatic first download
  selection, cancel/close cleanup and rendered disabled controls in both themes.
- Ruff, format, mypy and all three source policy gates pass on eb0bd60.
- New renderer covers 21 states in both themes at 100%/150% (84 PNGs).
  Visually inspected the dark catalog, 150% no-selection main screen and consent.
  Empty Options now also has an explicit placeholder and plain summary wording.
- Full M4 coverage run and CI 39989976906 are running. Screenshot upload and
  packaging carry-forward acceptance remain pending; no final-green claim yet.


### M4 full source verification and screenshot upload

- Full local suite/coverage: 153 passed, 1 CI-only skip in 170.71 seconds;
  94.2% total (core 93.7%, export 98.5%, models 94.4%, queue 93.0%, privacy 95.2%).
- Final empty-selection persistence test passes. Disabled render coverage now
  also paints real table/scroll-panel content; all four theme tests pass.
- New draft asset m4-screenshots-6fa2c7b.zip: 84 PNGs, 4,119,558 bytes,
  SHA-256 14ed33cc1566c9e1e7b35c3fa70f48161313abe603b5f0c769fcab12da876c82.
  Upload verified; release remains draft and older asset is retained.
- Next: final code CI, forward merges to M5/M6, full source verification on each,
  packaged build/PE/license/GUI/WFP acceptance, report refresh. No PR opened.


### M4 forward-merge source verification

- M5 4c2da89 carries the M4 fixes; full local suite 201 passed/1 CI-only skip,
  188.96 seconds; 94.5% strict coverage. Ruff/format/types/policy all pass.
- Final review found the missing-voice action still targeted a missing
  recommendation when Tiny was installed. Fixed on M4 and added an actual
  button-click regression; it passes. Carry this small correction forward too.
- M5 merge required only preserving both additive ledger sections. No source
  conflict or license/runtime pin change. Packaging CI 39990617610 is running.


### CI render portability correction

- M4 CI 39990574645 and M5 CI 39990617610 failed the new exact-foreground-pixel
  assertion for disabled combo boxes in both themes. Actual CI glyph pixels
  were antialiased (for example #636c67 instead of #606964), not missing text.
- Corrected on M4: light disabled ink is darker (#535c57). The visual regression
  requires a rendered glyph near the intended gray AND actual contrast >=4.5:1;
  backgrounds/borders cannot satisfy the glyph color bound. Exact gray border
  assertions remain. All four theme tests pass locally. No product assertion,
  policy check or test was disabled; failing CI prevented packaging uploads.
- Synchronized M6 local full suite: 202 passed/1 CI-only skip, 186.83 seconds,
  94.5% strict coverage. Its docs match the new M4 cancellation/deletion policy.
- Next: push this render correction through M5/M6, final CI and packaged gates,
  regenerate the screenshots for the stronger light disabled ink, update report.
