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
