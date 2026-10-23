# M4 Report - Model Manager and isolated downloads

## 1. Summary

Owner ThinkPad review of the packaged app: **all six checks PASS functionally**
(received 2026-10-23; i7-1365U, Iris Xe). The subsequent PM UX changes are
implemented: unrestricted confirmed deletion, an explicitly empty model choice,
fresh downloads after cancel/close, revised model descriptions, simpler consent,
contextual main-window prompts and clear disabled controls in both themes.

Final source and packaged acceptance are green on the implementation commits
listed below. The final report/changelog/ledger carry-forward changes documentation
only; the verified product source, tests and workflow are unchanged. No PR, merge
to main, published release or repository-setting change was made.

### Branches

- `m4-downloader`: Model Manager and all Owner UX corrections, source tests,
  screenshot renderer, developer documentation and this report.
- `m5-packaging-spike`: M4 changes carried forward into the accepted split bundle
  and installer spike; retains approved licenses, exact platform/CRT pins,
  installer inventory and upload ordering regression. Packaged acceptance below.
- `m6-docs`: M5 carried forward, plus user/privacy/contributor documentation;
  wording updated for unrestricted deletion and removal of cancelled partials.
- `main`: unchanged by the engineer.

### Owner actions for the morning

1. Review the new screenshot asset in the existing draft m4-screenshots release
   and the short changed-behavior checklist in section 8. The earlier six-check
   functional result is already recorded as PASS; it does not need repeating.
2. PM accepts the revised M4 report before any PR against main. Owner controls
   merges and publication.
3. M5 clean standard-user Windows 11 VM checks remain in M5-checklist.md on the
   packaging branch. Licensing ISSUE-017/018/019 decisions are resolved there;
   unsigned installers remain CI artifacts, never published releases.
4. Keep the real Surface Vulkan smoke test as a required pre-M7 check. Hosted
   runner and ThinkPad results do not replace that hardware check.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Catalog and local integrity | met | Five transcription models plus Voice detection; Installed/Not installed/Damaged/Downloading, sizes, free disk space and Verify all. Local TLS/Qt tests cover hash failures and re-hashing same-size/mtime tampering. |
| Catalog layout | met | Bold name once, quality line, smaller note; narrow Best for column; quiet accuracy warning below the list. Recommended suffix follows the name. |
| Consent and download progress | met | Single named GitHub/MB question, including Voice detection when needed; separate child JSON-lines progress. |
| Cancel and close | met | Child Job Object is terminated/joined before GUI removes the manifest-owned partial. Ctrl+C/cooperative CLI cancellation also removes it. Next user attempt starts fresh. |
| Delete every model | met | Selected, last and in-use Voice detection are deletable after confirmation. Selected-model deletion clears Options without replacement; last-model deletion returns to the no-models state. |
| Selection | met | Only newly installed models can fill an empty choice. An existing choice is never replaced by another download. Cleared selection persists across relaunch. |
| Main-window prompts | met | Recommendation only when no transcription model is installed; missing VAD has its own action. Empty selection has Choose a transcription model and an Options button. Ready when you are appears only if Start is enabled. |
| Layout and disabled controls | met | Full-width Start with reason above; Choose folder adjacent to path; name-first Options labels. Actual light/dark renders test gray disabled text/borders and text contrast of at least 4.5:1. |
| Separate process and no-network policy | met | Dev and split-package resolution tested; GUI never imports dusty_fetch; static no-network rule has zero exceptions. WFP counts below. |
| Owner hardware result | met | All six original packaged M4 ThinkPad checks PASS functionally; latest UX changes verified automatically and supplied for screenshot review. |

## 3. What was built and approved changes

The PM's 2026-10-23 UX decision supersedes the Owner brief's earlier selected/last
model deletion protections and resume-after-cancel wording. The brief and SPEC
remain unchanged. HTTP Range validation remains available after network failures;
explicit user cancellation/normal app close removes the partial instead.
A forced OS crash cannot execute cleanup, but an orphan prefix cannot become a
final model without the complete size and SHA-256 check.

Files: app/model_manager.py (catalog/worker/consent), app/window.py (selection
and prompts), app/theme.py (disabled/selected rendering), queue/storage.py
(explicit empty selection), dusty_fetch/downloader.py (cancel cleanup), focused
Qt/local-TLS tests, render_models.py and docs/dev/downloader.md. M6 user/privacy
docs describe the same behavior.

All UI wording remains in messages.py. No catalog, dependency, network host or
app license-policy exception was added. Audit hook ADR 0017, exact platform
primitive pins ADR 0021 and the split runtime layout remain in force.
ModelRegistry private cache access and other non-urgent audit items remain in
AUDIT-NOTES.md; enterprise proxy support remains in BACKLOG.md.

## 4. Test results

| Check | Result |
|---|---|
| M4 final implementation CI | [39993285087](https://github.com/dusty-corporation/dusty/actions/runs/39993285087), 51e6d2a: green; 156 passed, 2 expected skips in 309.99 s; real-network Tiny integration passed separately. |
| M4 strict-package coverage | 94.2% total; core 93.7%, export 98.5%, models 94.4%, queue 93.0%, privacy 95.2%. |
| M4 local full suite | 154 passed, 1 CI-only skip in 172.46 s; the later two selection-render tests and backend-choice regression passed separately. Final CI above runs all additions together. |
| Final carry-forward local suite | 204 passed, 1 CI-only skip in 191.96 s; final backend-choice regression passed separately. |
| M5 synchronized CI | [39993290851](https://github.com/dusty-corporation/dusty/actions/runs/39993290851), 545dac4; 204 passed, 2 expected skips in 300.88 s; 94.5% coverage. All four jobs green, including installer-wide license, installed-payload/lifecycle/WFP and upload-order regression gates. |
| M6 synchronized CI | [39993330554](https://github.com/dusty-corporation/dusty/actions/runs/39993330554), e0e34e2; source checks and all app packaged gates pass. All four jobs green, including installer-wide and installed-app acceptance. |
| Carry-forward strict coverage | 94.5%; core 93.7%, stdlib export 98.6%, models 95.2%, queue 93.0%, privacy 96.2%. |
| Ruff / format / mypy | Passed locally and in CI; 98 formatted files/58 source files on M4; 124/69 on the packaging/docs branches. |
| Three source policy checks | Passed, zero static no-network exceptions and no app license-policy expansion. |
| Final packaged review bundle (M6 run) | 216 files, 161,991,287 bytes; 64 PE files checked, no findings; unchanged exact platform/Owner CRT pins; no excluded networking modules. |
| Packaged license and GUI | Bundle license check passed; packaged GUI smoke passed; source and split-layout downloader resolution exercised. |
| Visual regression | Actual disabled-control borders and rendered glyph contrast >=4.5:1 in both themes; selected three-line labels >=4.5:1 against selection. |

Early CI failures in the new exact-foreground-pixel assertion were corrected:
Windows antialiasing blends thin glyphs. The final check requires glyph pixels
near the intended gray AND rendered contrast >=4.5:1; light disabled text is
darker for margin. Exact gray border checks remain. No test was disabled.
The selected-row label fix also passed visual inspection before the final upload.

The ordinary suite skips the explicit CI-only real-network test. CI runs that
Tiny release download separately. A hosted runner can also skip Vulkan transcript
comparison when no usable GPU exists; this does not replace hardware acceptance.
The earlier M6 checkpoint run 39987905683 timed out in a 30-second real CPU
self-test guard subprocess. No test threshold or assertion was weakened.
Final carry-forward results are recorded above.

### WFP evidence

| Scenario | Processing / GUI events | Fetch allowed | Fetch blocked | Calibration |
|---|---:|---:|---:|---|
| Final source self-test, headless and GUI processing | 0 | outside audit | outside audit | passed |
| Final source Model Manager download | 0 | 4 | 0 | passed |
| Final packaged self-test | 0 | outside audit | outside audit | passed |
| Final packaged Model Manager download | 0 | 4 | 0 | passed |

Source evidence: m4-download-audit in 39993285087. Final packaged evidence:
packaging-spike-audit in 39993330554, including offline-pe.json (64 checked,
no findings), license-findings.txt and the redacted WFP summaries.

Both source and packaged Model Manager scenarios drive the real consent/controller
path, verify the model and Voice detection, and confirm the audit hook is installed.
The positive blocked control calibrates auditing. Source attribution separates
actual GUI/fetch PIDs despite a shared Python image; the packaged GUI image is
firewall-blocked while the sibling downloader is allowed. No host/address data
is retained in the redacted evidence.

### Screenshots

[Draft screenshot release](https://github.com/dusty-corporation/dusty/releases/tag/untagged-6184fb70591dd06d1c63).
New asset: `m4-screenshots-b884fae.zip`, 84 PNGs, 4,097,039 bytes.
SHA-256: `05387171a91849629a6e755b0511935a2575b0f833d02af0a9c3a4c3bc3295cc`.

21 states in light/dark at 100%/150% cover the main prompts, Options, catalog,
selected/last deletion, Voice detection confirmation, consent, progress,
cancelled-part removal, hash mismatch, disk/network errors and Verify all.
These synthetic widget captures contain no user data or actual downloads;
42 GB free space is illustrative. Native title bars are outside the captures.
The release remains draft; previous assets are retained.

## 5. Deviations from SPEC

The PM-approved UX changes are described in section 3. Network isolation,
host allowlisting, full-file hashing, voice auto-include and offline processing
remain mandatory. No source static-check exceptions were introduced.
M5 installer licensing exceptions remain confined to the already approved
packaging branch/context and do not expand the app's license allowlist.

## 6. Issues

| ID | Severity | Status | Summary |
|---|---|---|---|
| ISSUE-018 | S1 | Resolved on M5 | PM-approved installer-only component terms, retained notices and reviewed upstream source evidence. |
| ISSUE-019 | S1 process | Resolved on M5 | Owner containment completed; installer upload depends on complete gates, with a failing-gate-prevents-upload regression. |

No new S0/S1 privacy, licensing or correctness issue was found in these M4 fixes.
The M5 checkpoint was clean/pushed before switching to M4; its final run
39987858934 is green. ISSUE-018 and process S1 ISSUE-019 are resolved with
installer notices/source evidence and a failing-gate-prevents-upload regression.
See M5-interim-7.md on the packaging branch for that separate milestone's evidence.
Clean-machine installer acceptance remains Owner work, not a claim of this report.

Cold startup without a model cannot complete the speech-based backend probe;
the CPU-safe recommendation applies until a model permits the real probe.
Literal static checks are not an obfuscation defense; runtime, PE and calibrated
WFP layers remain required.

## 7. Decisions needed from PM/Owner

1. PM screenshot/report acceptance (recommended). No unresolved M4 correctness,
   privacy, licensing or install decision. Do not open a PR until acceptance.
2. Owner handles the later clean Windows 11 VM and real Surface checks listed
   above; neither is claimed by the hosted-runner results.

## 8. Actions needed from the Owner: changed-behavior check list

Use the [final audited app review artifact](https://github.com/dusty-corporation/dusty/actions/runs/39993330554/artifacts/12519212190).
No repo clone or Python is needed:

```powershell
gh run download 39993330554 --repo dusty-corporation/dusty --name m4-review-bundle --dir Dusty-M4-review-polish
$dustyReviewPreviousLocal = $env:LOCALAPPDATA
try {
    $env:LOCALAPPDATA = Join-Path $PWD 'Dusty-M4-review-polish-data'
    Start-Process .\Dusty-M4-review-polish\dusty\dusty.exe -Wait
} finally {
    $env:LOCALAPPDATA = $dustyReviewPreviousLocal
}
```

Use an isolated review profile if testing no-models behavior; keep dusty,
dusty-fetch, bin, resources and licenses together. Do not replace the normal
profile or remove its models just for testing. About 10 minutes plus downloads.

1. In both themes at 150%, inspect the three-line Model Manager rows, Best for,
   recommendation suffix, accuracy note and clearly gray unavailable controls.
2. Confirm the one-sentence named GitHub/MB consent. Cancel or close during an
   incomplete download: no .part remains; the next attempt starts from zero.
3. Download another model while one is selected: selection stays. Delete the
   selected model: confirm the specific warning, empty Options selection and
   disabled Start with Choose a transcription model plus an Options button.
4. Delete the last model: no-models recommendation prompt returns. Download a
   model: it fills an empty selection. A main recommendation prompt disappears
   as soon as any transcription model is installed.
5. With Skip silent parts on, delete Voice detection after its warning. Start
   explains how to download it or turn the option off; the download button opens
   Voice detection even if a recommended transcription model is absent.
6. Check name-first Options labels, Choose folder next to the output path, and
   Ready when you are only when Start can actually run.

## 9. Risks for the next milestone

Clean-machine installer acceptance and the real Surface Vulkan check remain
Owner actions. Private cache use, selection/protocol boundaries and layered
network isolation need the planned independent M6 audit. No optional refactor
was added here.

### Provenance and repository checks

Existing Persian fixture: [original recording](https://archive.org/download/rubaiyat_bilingual_1207_librivox/rubaiyat_01_khayyam_whinfield_64kb.mp3),
exact interval [107, 122) s (00:01:47.000 to 00:02:02.000), Owner-verified by
listening as a complete spoken Farsi quatrain on 2026-10-22.
Canonical provenance: tests/fixtures/AUDIO_SOURCES.md. No audio added here.

Long-dash verification command: `rg -n '[\x{2013}\x{2014}]' .`
Output: none; exit 1 (no matches). SPEC and the Owner brief were not edited.

## 10. Time/effort notes

Most work concerned preserving deliberate selection, safe child shutdown/cleanup,
plain catalog presentation and proving disabled controls through actual rendering.
Forward merges preserve M5 license and runtime pins. No engineering-hour estimate
or unperformed hardware result is asserted. Non-essential improvements remain
in BACKLOG.md rather than being implemented.


## Polish round (2026-10-23)

- Commit `789e56b` (UI changes `7c7d5cf`); [M4 CI 39998311028](https://github.com/dusty-corporation/dusty/actions/runs/39998311028)
  is green: 169 passed, 2 expected skips, 94.2% coverage. Local full suite:
  170 passed/1 CI-only skip. Quality/policy gates pass; no em/en dash matches.
- All seven polish items implemented: short recommendation names, and-joined
  consent with unbreakable MB/GB units, named deletion/re-download advice,
  download labels without duplicate percentages, explicit Verify all feedback
  only with installed models, and one existing Options button.
- **Voice detection behavior:** deleting it while Skip silent parts is on blocks
  Start until it is downloaded again or that option is turned off. It does not
  automatically continue with silence skipping disabled. The confirmation says so.
- New [draft screenshot asset](https://github.com/dusty-corporation/dusty/releases/tag/untagged-6184fb70591dd06d1c63):
  `m4-screenshots-polish-789e56b.zip`, 28 PNGs, 759,997 bytes. Only 14 changed
  states in light-1/dark-1, generated after CI passed and visually inspected.
  SHA-256: `e3b3b14e25ff1c2af290468790ad1aab33ac31498ebb068310e8794dbb38476c`.
- Matching review bundle: **m4-review-bundle**, run **39998318413**,
  [artifact 12520629143](https://github.com/dusty-corporation/dusty/actions/runs/39998318413/artifacts/12520629143).
  All four workflow jobs are green, including PE/license/GUI/WFP and installed
  acceptance. Changes also carried to M6, green run 39998323956. No PR opened.


## Final Owner acceptance and PR preparation (2026-10-23)

- Owner ThinkPad changed-behavior check of review bundle run **39998318413**:
  **all seven steps PASS**, reported 2026-10-23.
- Final implementation: `e75dd79`, following partial-lifetime commit `6752599`.
  Best for wording wraps within two lines; Turbo has the requested newer/older
  computer note. The dynamic recommended suffix is unchanged. In-use Voice
  detection deletion now states exactly that Start is unavailable until another
  download or turning off Skip silent parts in Options. Verify all is disabled
  when no transcription model or Voice detection is installed.
- Crash/forced-close decision: keep recent partials for size/SHA-256-verified
  resume. At GUI startup remove regular .part files older than seven days;
  the exact seven-day boundary is retained. Normal Cancel and normal close
  still remove their active partial immediately. Developer documentation updated;
  M6 user documentation is deferred as requested.
- **Forced GUI termination regression PASS**, locally and in Windows CI:
  TerminateProcess kills the actual GUI interpreter while the real downloader
  is blocked on a gated local HTTPS response. The downloader process handle
  signals within five seconds without releasing that response; neither GUI nor
  downloader cleanup handler runs. The retained 131,072-byte partial stops
  growing. A new GUI retains it, requests Range bytes=131072-, and verifies the
  full size and SHA-256 before creating the final model. Closed stdout cannot
  explain this result because the child is blocked reading HTTPS at termination.
- [Source CI 40008197028](https://github.com/dusty-corporation/dusty/actions/runs/40008197028)
  is green: **175 passed, 2 expected skips, 94.4% coverage**. Local suite:
  176 passed, 1 expected skip. Ruff, formatting, mypy and all three policy checks
  pass. No tests removed or disabled.

| WFP download scenario | GUI connections | Fetch allowed | Fetch blocked | Evidence |
| --- | ---: | ---: | ---: | --- |
| Source, final implementation | 0 | 4 | 0 | CI 40008197028, m4-download-audit |
| Packaged, accepted review baseline | 0 | 4 | 0 | CI 39998318413, m4-review-bundle |

Both audits passed calibration and model verification. The packaged row is the
accepted review baseline, not a new packaged build of this final source round.
Per PM instruction, m5-packaging-spike and m6-docs are unchanged and not rebased.

- After source CI passed, regenerated and visually inspected only states
  **06, 08, 21 and 27**, each in **light-1 and dark-1**: eight PNGs.
- New asset on the existing [draft m4-screenshots release](https://github.com/dusty-corporation/dusty/releases/tag/untagged-6184fb70591dd06d1c63):
  **m4-screenshots-final-e75dd79.zip**, 290,143 bytes.
  SHA-256: `f1b3abf27b55c12cdc80b7fed5460fd82c5a168d3113a1c377c9c5a88a35c072`.
  Previous assets retained; release remains draft.
- Draft PR is authorized with title M4_model_manager, head m4-downloader and
  base main. It must remain draft and unmerged. No follow-on branch work here.
- Repository long-dash check: `rg -n '[\x{2013}\x{2014}]' .`
  Output: none; exit 1 (no matches). SPEC and the Owner brief remain unchanged.
