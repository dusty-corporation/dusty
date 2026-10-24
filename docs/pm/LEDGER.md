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


### Final screenshot selection contrast

- Visual inspection of the regenerated light 150% manager found three-line
  cell labels using normal ink on the selected row. Corrected to use Qt's
  highlighted text role for every selected line and restore normal ink on others.
- Two light/dark selection regressions pass, requiring >=4.5:1 against the
  selection background for each row; the corrected 150% light capture is legible.
- Screenshot upload will use this last product revision, retaining earlier
  draft assets. Complete final source/packaged CI remains required.


### Final selection and source acceptance

- Final synchronized local suite: 204 passed, 1 CI-only skip in 191.96 seconds;
  94.5% strict coverage. The additional explicit backend-choice regression passes
  separately: refreshing a recommendation cannot replace a user-chosen model.
- M4 full local coverage run: 154 passed/1 skip, 172.46 seconds, 94.2%; the two
  selected-row contrast regressions also pass separately. Final CI runs the
  complete combined test set, including these additions.
- Corrected antialias-aware CI is green at 12bd62e / 39991998164.
- Source WFP at b884fae / 39992418056: calibrated, GUI 0, fetch 4 allowed/0 blocked,
  real consent path and model/VAD verified; redacted m4-download-audit downloaded.
- Final visually checked draft asset m4-screenshots-b884fae.zip: 84 PNGs,
  4,097,039 bytes, SHA-256
  05387171a91849629a6e755b0511935a2575b0f833d02af0a9c3a4c3bc3295cc.
  Release remains draft, all earlier assets retained. Backend-choice guard does
  not change any rendered state. Next: final packaged acceptance/report.


### M4 Owner UX fixes complete, 2026-10-23

- Owner's original six ThinkPad packaged checks: all PASS functionally.
- All 15 requested UX corrections implemented on m4-downloader and carried by
  normal forward merges to m5-packaging-spike and m6-docs; no force push used.
- Final implementation CI: M4 51e6d2a / 39993285087 green (156 passed/2 expected
  skips, 94.2%); M5 545dac4 / 39993290851 green (204 passed/2 expected skips,
  94.5%); M6 e0e34e2 / 39993330554 green, all four jobs including packaging.
- Final split bundle: 216 files, 161,991,287 bytes; 64 PE checks, no findings;
  license gate and GUI smoke pass. Source/packaged WFP: GUI 0, downloader 4
  allowed/0 blocked, calibrated. Packaged processing self-test: 0 connections.
- Installed payload, installer-wide licenses, silent install/download/upgrade,
  both uninstall options, unchanged user outputs and installed WFP also pass;
  unsigned installer remains a gated CI artifact only, never a release.
- Latest screenshot draft asset: m4-screenshots-b884fae.zip (84 PNGs); release
  remains draft, old assets retained. Exact hash and link are in M4-report.md.
- Owner review bundle: run 39993330554, artifact 12519212190. Report contains
  isolated-profile commands and six changed-behavior checks, not another full
  walkthrough. M6 user/privacy docs match deletion and cancel-cleanup policy.
- Final report/changelog/ledger update is documentation only. Product code,
  tests, workflows and license/runtime pins remain identical to the green runs.
- No PR opened, main merge, release publication, settings change or new work.
  Stop after pushing this documentation through both later branches; PM review
  and later clean-VM/Surface checks are Owner actions.


### M4 screenshot polish round, 2026-10-23 (doing)

- PM accepted b884fae screenshots with seven final copy/feedback polish items.
  Clean m4-downloader recovered at 3acf37e; no Owner work to preserve.
- Implementing short recommendation names, and-joined consent with unbreakable
  size units, named/recoverable deletion warnings, simpler download progress,
  Verify all feedback only after an explicit request with installed models,
  one existing Options button, and decimal GB for sizes >=1000 MB.
- Voice deletion behavior stays unchanged: with Skip silent parts enabled,
  Start is blocked until Voice detection is downloaded or the option is off.
- Next: focused/full tests, quality/policy gates, push and green CI; matching
  packaged review bundle via existing packaging branch; targeted light-1/dark-1
  screenshots only after CI; append Polish round evidence to M4-report.md.


### M4 polish source checkpoint

- Full local suite: 170 passed, 1 CI-only skip in 174.65 seconds; 94.2% strict
  coverage. Focused Model Manager suite: 31 passed before the additional size
  rollover boundary case; the full suite includes that case. Ruff/format/mypy
  and all three policy checks pass; no em/en dash matches.
- Initial integrity scan is separate from explicit Verify all. The CI download
  exercise waits for a successful completed worker, preserving the failure
  guard without depending on the removed startup feedback text.
- Targeted renderer prepared for 14 affected states, light-1 and dark-1 only.
  It has not run yet: PM requested rendering after CI is green.
- Next: green source/packaged CI, collect matching m4-review-bundle run/name,
  render and inspect targeted captures, upload new draft asset, append report.


### M4 polish round complete

- Product 7c7d5cf, renderer/checkpoint 789e56b; source CI 39998311028 green:
  169 passed/2 expected skips, 94.2%. Existing tests kept and 13 cases added.
- Packaged M5 merge 8c48200 / 39998318413 and M6 e212a8d / 39998323956 are
  fully green, including PE/license/GUI/WFP, installer and upload-order gates.
- Review bundle m4-review-bundle: run 39998318413, artifact 12520629143.
- After source CI green, rendered only 14 changed states x light-1/dark-1.
  Inspected all changed states, uploaded new draft asset
  m4-screenshots-polish-789e56b.zip (28 PNGs, 759,997 bytes), verified digest
  e3b3b14e25ff1c2af290468790ad1aab33ac31498ebb068310e8794dbb38476c.
  All prior assets retained; release remains draft.
- M4-report.md has the requested short Polish round section with commit, CI,
  bundle name/run and screenshot evidence. It explicitly describes the actual
  blocked-Start behavior after deleting in-use Voice detection.
- Final follow-up changes report/changelog/ledger only. No PR, main merge,
  publication or settings change. Push documentation carry-forward and stop.


### M4 final Owner check and decisions, 2026-10-23 (doing)

- Owner ThinkPad changed-behavior review of m4-review-bundle run 39998318413:
  all seven steps PASS on 2026-10-23.
- PM decision 1: plain Best for descriptions for Turbo/Small/Medium/Small English,
  wrapped to at most two lines; Turbo note becomes Fast on newer computers.
  Slow on older ones. Dynamic recommended suffix remains unchanged; Tiny unchanged.
- PM decision 2: in-use Voice detection deletion warning ends after the Options
  alternative, without repeating the download-again sentence.
- PM decision 3: Verify all is unavailable when neither a transcription model
  nor Voice detection is installed.
- PM decision 4: recent crash/forced-close partials may resume, still requiring
  complete size and SHA-256. GUI startup removes .part files older than seven
  days. Normal Cancel/close keep immediate partial cleanup.
- In progress: startup-age/resume tests and a forced GUI TerminateProcess test
  proving the Job Object kills the downloader while its HTTPS read is paused.
- Next: full checks and green CI, only screenshots 06/08/21/27 in light-1/dark-1,
  new draft screenshot asset, updated report and draft PR M4_model_manager.
  M5/M6 stay untouched; no rebase or carry-forward in this round.

### M4 final implementation verified locally

- Full suite: 176 passed, 1 expected skip; strict-package coverage 94.4%.
- Ruff lint/format, mypy (59 source files), and all three policy gates pass.
- Forced GUI TerminateProcess regression passes: the Job Object kills the real
  fetch interpreter while its HTTPS response is paused, neither cleanup handler
  runs, and the partial stops growing. A new GUI resumes the retained prefix
  with HTTP Range and verifies the complete size and SHA-256.
- Stale startup partial cleanup, recent-partial retention, empty Verify all,
  exact deletion text and two-line Best for layout regressions pass.
- Implementation complete; source CI, targeted screenshots and draft PR pending.


### M4 final source and screenshots complete

- Implementation e75dd79 / 6752599 pushed. Source CI 40008197028 green:
  175 passed, 2 expected skips, 94.4% coverage. Forced GUI termination and
  retained-prefix resume regressions pass locally and on Windows CI.
- WFP source GUI 0, fetch allowed 4, blocked 0; calibration passed.
  Accepted packaged baseline remains run 39998318413 with the same counts.
- Rendered only 06/08/21/27 in light-1/dark-1 after green CI; all eight inspected.
  Uploaded m4-screenshots-final-e75dd79.zip, 290,143 bytes, to draft
  m4-screenshots; digest verified as
  f1b3abf27b55c12cdc80b7fed5460fd82c5a168d3113a1c377c9c5a88a35c072.
- Final M4 report includes Owner seven-step PASS, decisions, forced-close
  evidence, CI and both source/packaged WFP attribution. Developer docs updated.
- Next and final action: draft PR M4_model_manager into main, then stop.
  m5-packaging-spike and m6-docs remain untouched; no rebase or user-doc edits.


## Imported M5 spike history (historical states, see Phase 1 below)

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


## M5 Phase 1, 2026-10-23: complete, awaiting PM

| ID | Milestone | Task | Status | Evidence | Issues |
| --- | --- | --- | --- | --- | --- |
| M5-01A | M5 | Preserve brief and create clean branch from merged M4 | done | main 87a1304; m5-installer f84dbd2; M4-brief.md archived from HEAD; Owner M5 bytes preserved | - |
| M5-01B | M5 | Port M5-only spike work | done | 00ec6a4 licensing/history, c3438f1 packaging/installer/gates; normal push; final M4 unchanged, M6 endurance files excluded | - |
| M5-01C | M5 | Revalidate port source | done | 224 passed/1 expected skip, 94.6%; lint/format 127 files, mypy 70, all source policies pass; CI 40011781091 checks/offline/upload regression green | - |
| M5-01D | M5 | Model-free Vulkan investigation | done | Pinned engine-v2 API: 1 device/init/4 KiB buffer clear+sync, no model, exit 0 in 0.468 s; docs/dev/m5-model-free-vulkan-check.md | - |
| M5-01E | M5 | Gap analysis and decision inventory | done | M5-interim-1.md covers all six SPEC tasks/three acceptance items, brief gaps, six recommended decisions, Phase 2 estimate | - |
| M5-02 | M5 | Finish installer and release acceptance | blocked | S0 self-review: three transcript-preservation regressions fail; M5-interim-8.md; normal work stopped, active builds requested cancelled, final release/VM acceptance withheld | ISSUE-020 |

- Original spike interim-1 retained as M5-packaging-spike-interim-1.md; other
  spike reports remain historical, with no old passing run claimed for this head.
- Initial local port run: 221 passed/3 failed/1 skip. License-byte tests detected
  CRLF copies created during patch application; restored exact committed LF
  notice bytes, with no policy, pin or test change. Serial full rerun passed.
  License PDFs match their recorded original hashes.
- Port CI 40011781091 packaging/installed job remains in progress at handoff;
  no fresh installer size, bundle/license/WFP acceptance or release claim yet.
- Owner brief SHA-256:
  ca53f763fe97ad32a591b18b05acb7b73b96b84121bc31de6b3a5e801b3dc2b0.
- m5-packaging-spike remains 95dd90b; m6-docs remains c855b52. No PR, tags,
  releases, reference-branch changes or Owner-profile installation. Phase 1 stops.


## M5 Step A/B authorized, 2026-10-23

- PM approved temporary existing-payload extraction and a bounded, Job Object
  model-free probe. Only integrated/discrete Vulkan devices count, excluding
  known software implementations; Small fallback on failure/crash/timeout.
- RAM minimum, failure completion preserving files/clearing selection, M4 crash
  partial policy, prerelease version/assets approved. Self-test scope: each
  selected model once on Auto plus smallest once on CPU and VAD verification.
- Standalone diagnostic tools/bench/model-free-probe.ps1 requires only PowerShell
  and the existing engine-v2 DLLs. Vulkan physical-device type and software
  exclusions precede actual ggml initialization/4 KiB clear/synchronize. Child
  waits for Job Object assignment; eight-second deadline; raw stderr discarded.
- Desktop standalone result: real_gpu_found=true, model_file_opened=false.
  ThinkPad commands next; Step B proceeds without waiting for Owner hardware.


### M5 Step B page implementation checkpoint

- Shared Model Manager names, Best for, notes, size formatter and consent now
  generate installer choices/consent. Full third-party notices are included in
  license acceptance, with page buttons for Apache/NOTICE, notices and Microsoft.
- Production model-free entry uses a suspended Job Object child and five-second
  deadline, Vulkan physical type plus software exclusions, engine initialization
  and buffer clear/sync. Installer defaults to Small and updates untouched
  choices after a successful real-GPU/RAM check.
- Added responsive timer-driven guarded child operations: verify/reuse/download,
  each selected Auto test and smallest CPU test; plain retry/CPU retry/explicit
  finish-without flows, preserving files and clearing only a failed selection.
- Normal cancellation kills its nested child job before removing the active
  partial; crash keeps recent partials. Installer preparation expires stale ones.
- Focused support/generation/archive regressions: 24 passed; lint/types pass.
  Full suite and native compilation/screenshots remain in progress, not claimed.
- WFP harness now exercises the model-free probe under the same blocked images
  and zero-event requirement. Review executable is a CI artifact only, gated
  after license/installed acceptance, and cannot install or download.


### M5 Step B source verification and first compilation

- Full local source at 775289b: 245 passed/1 expected skip in 198.01 s,
  94.6% coverage. Current focused generator regression also passes (3 tests).
- CI 40015931598 / 40016359782 reached native compilation after passing source,
  bundle PE/license/GUI/WFP gates, then rejected a leading array expression as
  an Inno section. c1993b4 fixes the parser layout and adds a negative regression.
- The shared-description regression then caught missing Voice detection details;
  03aa70c adds the always-included Voice detection row text and size. No test
  was removed or weakened. Those intermediate failing runs are not acceptance.
- Standalone diagnostic passed on desktop with both PowerShell 7 and Windows
  PowerShell 5.1. Production guarded entry returned real_gpu_found=true too.
- Current native compile/review artifact and PNG captures remain pending CI.

### M5 resumed session: Owner probe and CI repair

- Owner ThinkPad Iris Xe model-free probe PASS on 2026-10-23:
  `{"real_gpu_found":true,"model_file_opened":false}`. No model file opened.
- CI 40021423809 failed native compilation: `Unrecognized [Setup] section
  directive "DialogFontSize"`. Pinned Inno 6.7.3 source lists it under
  LangOptions; moved the directive there and added a generator regression.
- Pending self-test correctness fix now identifies the actual attempted backend;
  Retry on CPU is offered only for a failed Vulkan test, never a failed CPU test.
- Focused installer support/generation: 24 passed; ruff and mypy pass (73 files).
  Screenshots and final CI still pending; release pipeline and VM checklist next.

### M5 release pipeline checkpoint

- Added fail-closed draft-only release workflow, reusing all CI source, PE,
  license, installed lifecycle and calibrated WFP gates before asset upload.
- Approved mapping: v0.5.0-m5.N -> Python 0.5.0.devN, displayed 0.5.0-m5.N,
  numeric installer 0.5.0.N. Any other tag is rejected by the release job.
- Release staging permits only installer, complete notices, installer CycloneDX
  SBOM, retained JEDI source and SHA256SUMS covering those four assets.
- Focused release/generator/upload-order tests: 11 passed. Tag runs and two-build
  upgrade acceptance remain pending; no draft release has yet been claimed.

### M5 Owner VM instructions checkpoint

- README now explains unsigned SmartScreen review and full Get-FileHash comparison.
- M5-checklist.md provides the supplied Windows 11 Home/VirtualBox 7.2.22 route,
  AMD SVM Owner prerequisite, EFI/Secure Boot/TPM 2.0, 8 GB/4 CPU/80 GB settings,
  standard user, draft transfer, and all SPEC 11.6 cases with expected results.
- VirtualBox is explicitly CPU-only acceptance, not substitute evidence for a
  physical Vulkan GPU. Owner must run and return the numbered results.

### M5 audit/self-review checkpoint

- Local full source: 257 passed/1 expected skip, 94.6% strict-package coverage
  in 193.37 s. Ruff/format (135 files), mypy (75), all three policy checks pass.
- Correctness fix: normal Cancel or Finish without after a failed transfer now
  removes only the active known partial, after child shutdown. Crash remains
  resumable. Generator regression covers both busy and failed normal-close paths.
- Installer WFP parser negative cases reject allowed/blocked events from Setup
  EXE/temp runtime, GUI, engine and decoder, and missing fetch-positive evidence.
  The negative test caught PowerShell array-concatenation precedence in Setup
  image matching; corrected it before treating any new audit as acceptance.
- First approved test tag v0.5.0-m5.1 is running (40037642063). Its older Setup
  matcher is superseded; final acceptance must use the corrected next test tag.
- Added a true two-version upgrade path: next tag downloads the previous gated
  draft, checks increasing numeric versions, and preserves verified model hashes
  and write times while blocking downloader egress during upgrade.

### M5 green native review and first tag result

- CI 40036996425 (75656dd) is fully green, including native compilation,
  installed lifecycle, PE/license, packaged GUI and WFP. Native page artifact
  downloaded for review. CI 40037091940 also green.
- Tag v0.5.0-m5.1 / release run 40037642063 failed the JSON export semantic
  golden solely because its expected app_version was hardcoded 0.0.1. Draft
  upload was skipped. Expected metadata now follows the package version; all
  other golden fields remain asserted. Focused exports/release tests: 17 passed.
- Next release discovers the latest earlier existing draft, so a failed test tag
  does not require deletion, retagging or an unavailable preceding installer.
- Page review is active; desktop scale is 175%. A process-only DPI-unaware
  compatibility launch reports effective 96 DPI without changing host settings,
  but Windows bitmap-scales its capture. This limitation must be disclosed;
  native 100%/150% display acceptance remains an Owner VM check.

### M5 native review fixes and documentation preparation

- Native review of green artifact 40036996425 exposed an overlapping hidden
  download action behind Retry controls; e05d8d9 hides it in production failure,
  active and finished states. Generator regression passes.
- The harmless review build's CreateAppDir=no caused the native folder page to
  be skipped; e3e2d7f exposes its real controls without enabling installation.
  69222ef separates the uninstall-only silent API from Setup's review form.
  These capture corrections await their gated CI artifact, not claimed complete.
- First 18 usable native page captures are retained under ignored build/;
  wrong folder/uninstall captures are excluded from the review archive.
- Added prior-draft checksum verification before executing an upgrade input;
  8 focused release tests pass, including tamper and duplicate checksum rejection.
- Draft M6 docs are prepared in build/m6-docs-v2-port, not yet on a branch:
  installer pages/failure outcomes, deletion rules and crash/stale partial policy
  updated. Prepared local-link and prohibited-dash checks: zero findings.
- Tracked UTF-8 text scan via git ls-files -z: em/en dash matches: 0. Host scale
  unchanged; all development changes stay in whisper_app.

### M6 docs v2 pushed, return to M5

- m6-docs-v2 8a91934 pushed normally from M5 20cce6b. User/privacy/contributing
  docs updated to current behavior, README links added, no application code.
- Verified reference heads unchanged: m5-packaging-spike 95dd90b, m6-docs c855b52.
- Returned to m5-installer. Remaining overnight work: latest native review PNGs,
  draft screenshot upload, final tagged release/true two-version upgrade evidence,
  final report hashes/counts and clean checkpoint. Owner/PM checks remain manual.

### M5 first successful draft and corrected upgrade gates

- Draft .2: CI 40038534920 fully green; five assets, installer 34,670,296 bytes.
  Corrected calibrated download audit: Setup 0, GUI/probe 0, native 0,
  fetch allowed 4, blocked 0. Both uninstall choices and output preservation pass.
  CI source 256 passed/2 skipped, 94.6%; separate public download 1 passed.
- .3 run 40040057856 is in progress but its two-version harness compares the
  old install with the new inventory before upgrade. 895e199 moves payload,
  PE and installed WFP gates after upgrade, with an ordering regression.
  Focused release/generator checks: 12 passed. No gate is weakened.
- Authorized tag .4 starts the corrected true .2-to-.4 upgrade test. Test tags
  are permitted for N=1,2,... by CURRENT_MILESTONE line 33; automatic review's
  initial two-tag interpretation was resolved by presenting that explicit scope.
- Page artifact 40039096810 is green. Corrected failure controls no longer
  overlap; native uninstall form captured. Review-only folder description's
  name placeholder is corrected in 895e199 and awaits its native artifact.
- M5 report now records .2 asset hashes/counts and outstanding manual acceptance.

### M5 page delivery and final acceptance receipts

- Step B review delivered: draft m5-screenshots asset
  m5-installer-pages-step-b-895e199-light-review.zip (7,861,054 bytes),
  SHA-256 d09b2e4695fca10c5c0409dcee5cac70121bec5da1e8555b34c68aa57ca0578e.
  Archive gate: 21 native PNGs + README only. Exact scale limitation is disclosed;
  genuine 100%/150% display acceptance still needs the Owner VM. Interim 2 updated.
- Local final pre-receipt suite b20470c: 259 passed/1 expected skip in 188.56 s,
  94.6% coverage, offscreen configuration used in CI. Earlier isolated visible
  Qt run printed COM diagnostic 0x8001010d but exited 0/1 test passed; this clean
  full offscreen run did not print it. No application assertion was suppressed.
- CI 40039950278 failed in the Qt test driver's exists/stat race after a partial
  was removed. b20470c avoids that timer race; all cleanup/orphan assertions stay.
- .3 draft CI passed but had two_distinct_versions=false: read-only GitHub tokens
  cannot list draft releases. It is NOT true-upgrade acceptance evidence.
- Automatic review rejected broadening validation/packaging to contents:write.
  That proposal was removed, never committed. Safer cf9904e reads prior successful
  release-workflow artifacts with contents:read/actions:read, verifies checksum,
  and removes the token from the child environment. No repository settings changed.
- Final .6 run 40041736046 must prove a real increasing-version upgrade, current
  installed payload/PE/WFP, both uninstall choices, unchanged outputs and a fresh
  CURRENT-installer download/probe audit. Asset staging now rejects missing/false
  receipts. Focused receipt/upload regressions: 11 passed. No completion claimed.

### M5 repeated-audit correction and synchronized documentation branch

- .5 run 40041077970 failed installer acceptance: auditpol `Error 0x00000050`,
  then `Installer audit backup failed`. Cause: the second calibrated audit reused
  the first CSV filename. 7db67d4 gives each audit a unique backup and preserves
  independent restoration. No connection violation was reported; no binary upload.
- .7 run 40042648483 is the final corrected receipt/true-upgrade experiment.
  The earlier chat run number 40042684409 was a mistaken ID and was immediately
  corrected; it is not evidence. All report/evidence links use verified IDs.
- m6-docs-v2 0e005ea pushed normally with final M5 code/test-helper corrections.
  `git diff m5-installer..m6-docs-v2 -- src tools installer .github tests
  pyproject.toml uv.lock` is empty. User docs differ; reference branches unchanged.
- Non-urgent independent-audit notes added for explicit external license-browser
  links and partial-deletion failure reporting. No new application work started.

### S0 STOP - ISSUE-020, transcript preservation

- Stopped normal M5/M6 work under AGENTS rule 2 / SPEC NN-7. Startup and installer
  self-test recursively delete named work directories even when settings record
  them as the chosen transcript destination. GUI folder selection does not reject
  those destinations. The existing uninstaller's protection does not cover them.
- Exact isolated command: uv run pytest tests/unit/test_work_output_ownership.py
  -q --basetemp=build/issue020-repro. Result: 3 failed in 0.38 s. Synthetic public
  sentinels only; no real Owner profile, recording or transcript was touched.
- Enabled failing regressions retained; no xfail/skip or safety fix without the
  PM's S0 decision. ISSUE-020 and M5-interim-8.md contain root cause and proposal.
  M5-report.md now starts with the release-blocking finding and morning actions.
- Cancellation requested for own active runs 40043241355, 40042984627,
  40042648483, 40042645271 and 40042365579. No run/artifact/tag/release was deleted.
- Screenshots and M6 docs prework are pushed, but neither is acceptance for the
  affected code. Keep all M5 drafts unpublished and postpone VM installation.

### Final incident containment checkpoint

- All five requested workflow cancellations are confirmed completed/cancelled.
- m5-installer incident regression commit c621c88 pushed; m6-docs-v2 5c8b285
  also carries the enabled failing tests and S0 warnings, blocking packaging.
- Reference heads remain 95dd90b (m5-packaging-spike) and c855b52 (m6-docs).
  Working tree is on m5-installer; no product repair or further work after stop.
- M5-report.md / M5-interim-8.md are the morning handoff. PM approval for the
  cleanup-ownership repair is required before resuming. No final CI/VM/release
  acceptance is claimed. Owner profile and output files were not touched.

### ISSUE-020 repair authorized by PM (2026-10-23)

- PM approved unique work ownership markers, explicit content inventories,
  conservative unknown-content preservation, no reparse traversal, managed-area
  source/output rejection and preservation of legacy internal destinations.
- Repair in progress on m5-installer. Three original regressions stay enabled.
  Part 2 page changes wait for all Part 1 gates, including installed WFP/uninstall.
- Owner reports AMD SVM enabled on the desktop; VM setup no longer awaits that.
- Damaged existing models must show "Needs download again" on Choose model.
- Latest pre-repair CI 40044102299 fails the intentional preservation regressions.

### ISSUE-020 first repair checkpoint

- Implemented unique purpose-marked work folders and explicit SHA-256 inventories;
  cleanup validates the entire flat inventory before deleting any file. No runtime
  recursive deletion remains. Unknown, changed, unmarked, linked and protected work
  is preserved with a path-free log line.
- Startup clears legacy internal output selection, retains persistent protection,
  and gives a one-time shared message. GUI and coordinator reject managed-area
  source/output paths, including save-next-to-source and resolved aliases.
- Focused ownership/probe tests: 39 passed. Lint, mypy (76 sources), all three
  source policy checks passed. Full suite and CI pending; ISSUE-020 stays open.
- Deterministic atomic temporary files replaced with exclusive random files;
  repeated local bundle builds refuse existing destinations instead of rmtree.
- Old name-only cleanup test fixtures now create explicit owned inventories;
  crash recovery expects uncertain killed-writer output to survive, per PM rule.

### ISSUE-020 source verification checkpoint

- Full isolated source suite: 282 passed, 1 expected skip in 168.39 s. Additional
  no-reparse/cancel/log-folder tests were added afterward; final-head CI remains
  authoritative and pending. Focused latest safety tests: 33 passed.
- Logging initialization now preserves a legacy transcript folder under logs;
  the enum-only skip diagnostic is admitted by the existing privacy filter.
- Rollback checks the content hash of newly published transcripts before removal.
  Downloader and Model Manager reject reparse ancestors; installer normal-cancel
  partial cleanup uses the guarded app helper instead of direct Pascal deletion.

### ISSUE-020 development boundary correction

- Offline source CI 40059180686 failed exit_code=1 (no connection violation): the
  first boundary implementation treated all of development build/ as an install
  folder, rejecting the audit's build/offline-*/outputs destination. RuntimePaths
  now carries the actual frozen install root explicitly. Development protects
  its binary/resource/model folders without rejecting sibling test outputs.
  The installed app still protects the complete install folder.

### ISSUE-020 automatic partial ownership

- The M4 age-only .part deletion now also requires an exact downloader-written
  hash receipt in the existing .lock file. Unknown/modified old prefixes survive.
  Interrupted transfer attempts write receipts; recent crash prefixes still
  resume and the final size/SHA-256 checks remain mandatory. A crash before its
  receipt can leave an old prefix preserved instead of guessing ownership.
- Downloader plus stale-prefix tests: 24 passed in 32.36 s. Dedicated unknown and
  modified stale-prefix preservation regression added. Full final-head gates next.
- M5-interim-9.md records the repair and every explicit delete/rmtree call site.

### ISSUE-020 packaged gate checkpoint

- 40059794329: source checks, offline and upload regression pass; packaged PE,
  GUI smoke, license gate, self-test WFP and Model Manager WFP pass. Inno compile
  failed at generated line 400: Unknown preprocessor directive. A line beginning
  with Pascal #13#10 in the new damaged-model label was parsed by ISPP. Joined
  it to the assignment; added a generator regression against leading #digits.
- Installed WFP/uninstall were correctly skipped. Installer upload was blocked.
- Full local measured source: 291 passed/1 expected skip, 217.06 s; core 93.7%,
  export 98.6%, models 96.6%, queue 91.8%, privacy 96.6%; total 94.2%.
- m6-docs-v2 511b0b6 has the repair plus updated preservation/privacy guides;
  implementation parity with m5-installer was checked before this syntax fix.

### ISSUE-020 marker continuity regression

- Further repair review: final output bookkeeping must not recreate a missing
  or changed marker. OwnedWork now compares it to the exact creation/last-write
  bytes before every inventory update and permanently preserves that invocation
  after any mismatch/read/write error. Two enabled regressions cover marker
  removal and mutation before bookkeeping. No Owner data was touched.

### ISSUE-020 resolved, Part 1 complete (2026-10-24)

- Final repair 1b62946: CI 40061186069 all four jobs green. Source 293 passed,
  2 expected skips plus real-network 1 passed; required coverage 94.2%.
- Packaged PE/license/GUI/WFP, installed payload/PE/WFP and both uninstall choices
  pass. Calibrated Setup 0, GUI/probe 0, native 0, fetch allowed 4, blocked 0.
  Models and output sentinel preserved. two_distinct_versions=false is not
  claimed as true-upgrade acceptance; Part 3 will provide two gated tag builds.
- ISSUE-020 closed with PM decision, root cause, retained original regressions,
  marker continuity/link tests and the deletion sweep in M5-interim-9.md.
- m6-docs-v2 8c199b0 implementation parity verified. Part 2 page work now starts.

### M5 page review round implementation (2026-10-24)

- Part 1 gates passed before these changes began. Shared PM wording, persistent
  download heading, Next=Download, byte counter, processor retry, success plural,
  Finish-without explanation, default shortcuts and compact uninstall controls
  implemented. Sizes share the Model Manager formatter, including real uninstall
  MB/GB units. Wizard artwork replacement parked in BACKLOG.md.
- Pinned Inno 6.7.3 GetPreviousPageID stops at wpInstalling. Added an opt-in
  post-copy model-return page using the same controls, so Back can change models
  before download without copying app files again. It is skipped otherwise.
- Open Dusty now is checked and runasoriginaluser. At the final Finish callback,
  after all workers end, Setup drops only its completed outer job's kill-on-close
  flag so the requested GUI can outlive it. Download/test job protection remains
  active until that point. Failure disables launch and explains Start menu use.
- Automatic review rejected skipping the old VAD wording assertion. Replaced it
  with a complete assertion of the PM-required VAD sentence and catalog size;
  every transcription row remains covered. No test is skipped or disabled.
- Generator/source tests and native CI compilation/acceptance pending.

### M5 native preview consistency

- Local full source/coverage for the page checkpoint: 295 passed/1 expected skip
  in 206.75 s, 94.2% required-package coverage. Native CI remains pending.
- Preview byte totals now come from the selected catalog models plus voice
  detection, matching its heading and bar; no mixed example totals. Preview
  Retry/processor/Finish-without buttons render enabled but have explicit no-op
  handlers, so review binaries can never start downloads or change selection.
- Actual source download progress reads the current manifest partial/file size
  with pinned Inno FileSize64; no downloader/network logic was added to Setup.

### M5 native page interaction check

- First page build aeae3e6 is fully green, CI 40062564379, including installed
  WFP and uninstall. Inspected its gated ReviewOnly executable in a repo-local
  TEMP profile; no installation, network request or real profile change.
- Compact Uninstall Dusty dialog: text unclipped, checkbox checked, Cancel has
  the default-button outline. Finish wording and checked Open Dusty now visible.
- Actual Back -> model page -> toggle Tiny -> Next changed consent from Small
  plus Voice detection (488.5 MB) to Small plus Tiny plus Voice detection
  (566.2 MB). This verifies the native return-page data binding, not just text.
- Closed the verified own preview process after QA. Final screenshots will use
  the later gated build with UTF-8 size reading and safe consistent examples.

### M5 post-copy cancellation correction (ISSUE-021)

- Pinned Inno MainForm.Close only handles pre-install/install steps. The model
  page occurs after file installation, so its original Cancel/X path was inert.
  Fixed with explicit button/Close-query callbacks and normal Finish/cleanup,
  no app launch, active partial removal and exit code 130. No abrupt self-kill.
- Added CI-only real-prefix cancellation acceptance under calibrated WFP, then
  retry/uninstall/sentinel checks. Its separate cancellation audit is retained;
  the complete-download audit stays the primary receipt. Final tag staging now
  requires the normal-cancel pass as well. No release upload gate was relaxed.
- Source invariants and native CI compilation/acceptance pending. Owner VM must
  still exercise the actual Cancel button, Escape and X; preview is not proof.
