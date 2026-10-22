# M3 Report - GUI (single file and batch)

## 1. Summary

The desktop GUI now runs the M2 offline coordinator for single recordings and batches, with simple defaults, background preparation, progress, cancellation, collision choices and recovery. The PM screenshot corrections are implemented, including modal Options, clearer actions and names, and measured control contrast. Automated acceptance and the regenerated screenshot matrix are complete. The Owner's desktop walkthrough has been requested but no pass/fail results have arrived, so M3 human acceptance remains pending. No M4 work has started; PR #4 remains a draft for review.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Add files/folder, local drop, duplicate handling, reorder/remove | met | pytest-qt controls and scanner tests. |
| Start/cancel, collisions/apply-all, summary, close/save/resume | met | Actual native batches through MainWindow and the shared coordinator; cancellation and output preservation asserted. |
| Model rules and simple defaults | met | Installed-model selection; backend-dependent recommendation; English-only lock; incompatible translation disabled; Medium action; slow warning; explicit replacement when a resume model is missing. |
| UI event loop gap at most 200 ms during a real batch | met | Public JFK, Tiny CPU, two threads, TXT+DOCX; 10 ms precise Qt timer and GUI-thread delivery assertions. Latest focused measurement: 11.739 ms maximum gap. This measures the tested batch, not every possible recording or workload. |
| Centralized copy, exact privacy/accuracy wording, vocabulary hints | met | app/messages.py; copy/model-control tests; multi-line hints and soft warning based on the verified approximate 800-character prompt threshold. |
| Themes, scaling, required dialogs and screenshots | met | 116 synthetic PNGs: 29 states in light/dark at 100%/150%; font glyph validation and key-image visual inspection. Native display review is pending below. |
| Owner desktop walkthrough | not met | 20-step checklist in section 8; requested, awaiting actual pass/fail evidence. |
| Approved cleanup and real-appdata test protection | met | backend_probe-only cleanup completed and verified before M3; session audit guard plus repo-local appdata for tests and child processes. |

## 3. What was built

- Archived the M2 brief and committed the Owner's M3 brief unchanged in 325973b; branch m3-gui.
- app/window.py, dialogs.py, table.py, theme.py and messages.py: drop/add interface, recording list, modal Options with collapsed Advanced, output formats, model rules, safe actions, first run, sync warning, all mapped errors, palettes and original in-memory waveform icon.
- app/workers.py: native preparation, scan/duration probes, coordinator and self-test on QThreads with Qt signal/slot handoff. Widgets collect choices and present state; decoding, transcription, exports and output planning use the M2 implementation.
- Additive numeric duration/elapsed queue fields retain schema-1 compatibility. Interrupted probe/self-test work is cleaned on startup; unknown work directories are retained.
- tests/offline/gui_batch.py extends the existing WFP acceptance window to a real GUI batch. tools/test_appdata_guard.py blocks audited Python access to real Dusty app data; tests inject repo-local paths.
- Verified read-only Google Drive streaming mount detection fills an inherited sync-warning gap. docs/dev/gui.md, docs/dev/sync-detection.md and docs/privacy.md record behavior and limits.
- No dependencies or native components added; SPEC and the M3 brief were not edited. Nice-to-have profiling is in BACKLOG.md.

### Screenshot review

[Draft m3-screenshots release](https://github.com/dusty-corporation/dusty/releases/tag/untagged-679fbbf87eb800652185).
Use **m3-screenshots-pm-review-2.zip**, 2,833,268 bytes, SHA-256:
`c8c06528a475af12bf663781c1ac37c6f0e65071a53d0ae21128f4feb26c8153`.
GitHub's uploaded digest matches. Both earlier ZIPs are retained; the release is still a draft and may require authenticated access. The Owner can relay the reviewed ZIP to the PM.

Reproduce with `uv run python tools/render_gui.py`. Screens include empty/waiting/modal options/vocabulary/advanced, invalid translation selection, preparing/transcribing/saving, collision, summary, resume, welcome, sync warning and every failure-code dialog. Names and progress are synthetic, not transcription or performance evidence. Installed Windows Segoe UI is loaded only if offscreen Qt has no fonts; no font is redistributed.

### PM review verification

- Translation help and Medium action are hidden during Transcribe; regressions cover invalid Translate choices.
- Opening modal Options leaves the main table geometry unchanged. Only Text and Word remain in the main format row; SRT/VTT/JSON still persist under More formats.
- Overall progress is hidden while idle. One formatter keeps bottom/row phase labels consistent, including zero-progress preparation.
- Collision radios, filenames, Stop, nonzero summary counts, failure reasons and the primary Open folder with transcripts action are tested.
- Move actions are in the context menu with actual Alt+Up delivery tested after focus; main edit buttons are Add files, Add folder, Remove and Clear list.
- Border contrast against window/input/button backgrounds measures **4.324/4.612/4.100:1 in light mode** and **7.014/7.728/5.098:1 in dark mode**, exceeding 3:1. Actual painted-boundary tests cover check/radio, push/tool, combo/spin, text, table and scroll controls; key screens were visually reviewed in both themes. Native OS dialogs still need the Owner's desktop review.

## 4. Test results

Final revision: 3df3cae (UI changes b1d9552/d728563, renderer 26cf74b). Local Windows checks:

- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: 88 files already formatted.
- `uv run mypy`: passed, 54 source files.
- `uv run python tools/measure_coverage.py`: **99 passed in 80.15 s** (runs the entire pytest suite with tracing).
- All three policy checks passed: check_no_network.py, check_no_huggingface.py, check_licenses.py.

| Required package | Hit / executable lines | Coverage |
|---|---|---|
| core | 104/111 | 93.7% |
| export | 130/132 | 98.5% |
| models | 117/124 | 94.4% |
| queue | 429/470 | 91.3% |
| privacy | 80/84 | 95.2% |
| Combined | 860/921 | 93.4% |

Every required package exceeds 85%. These figures do not claim GUI widget line coverage; 18 dedicated Qt/theme/presentation tests cover the M3 behaviors, including three actual native batch integrations.

Final revision CI:

- [PR run 39840103768](https://github.com/dusty-corporation/dusty/actions/runs/39840103768): checks and offline passed; **98 passed, 1 skipped in 183.10 s**, strict combined coverage 93.4%.
- [Push run 39840090723](https://github.com/dusty-corporation/dusty/actions/runs/39840090723): checks and offline passed; **98 passed, 1 skipped in 171.93 s**, same coverage.
- Both WFP logs: `WFP calibration passed; selftest passed; batch passed; gui passed; connection_events=0`. Positive blocked-event calibration and cleanup passed.
- The sole skip is the existing usable-Vulkan-device comparison on hosted CI; it passes on the local desktop. No new skip was added.
- [Draft PR #4](https://github.com/dusty-corporation/dusty/pull/4) stays open, unmerged. Subsequent report-only commits may queue their own CI runs.

Original review PR run 39839743819 failed the keyboard assertion and exposed a missing active-window precondition in the
new keyboard regression (98 tests passed and that assertion failed locally).
The test now activates the window and waits for actual table focus before
sending Alt+Up. Its reorder assertion remains intact. No test was skipped,
disabled or weakened. Earlier pre-review CI evidence remains in git history.

### Persian fixture provenance requested by the Owner

The M2 fixture record in tests/fixtures/AUDIO_SOURCES.md identifies this original
[chapter MP3](https://archive.org/download/rubaiyat_bilingual_1207_librivox/rubaiyat_01_khayyam_whinfield_64kb.mp3)
from the [LibriVox bilingual Rubaiyat edition](https://librivox.org/the-rubaiyat-of-omar-khayyam-version-2-by-omar-khayyam/),
chapter 1, Persian reader MostafaRazavi. The exact source interval is
**00:01:47.000 inclusive to 00:02:02.000 exclusive**, or **[107, 122) seconds**,
a 15-second excerpt stored as audio/translate/rubaiyat-fa.wav. These are times
in the original recording, not timestamps relative to the extracted WAV.

The fixture record identifies Persian quatrain 2 and excludes the following
English reading. The independent reference is [Whinfield's 1883 bilingual
edition, quatrain 2](https://archive.org/details/quatrains1883omaruoft); the
translation smoke test checks the reference concept "burns as fire", another
source concept and English output. This is a loose translation-content check,
not a WER or literary-quality claim. The Owner can listen to that exact source
interval and compare the quatrain; no new human listening confirmation is
claimed in this report.

Prohibited-character verification (all tracked repository text):

```powershell
$pattern = [string][char]0x2013 + '|' + [char]0x2014
git grep -n -I -E $pattern -- .
```

Output: no lines; git grep exit code 1 (no matches). No history was rewritten.

## 5. Deviations from SPEC

The PM explicitly replaced the original expanding Options panel with a modal dialog, moved extra formats into it, and revised the dialogs and copy. These approved changes supersede the earlier M3 brief for those controls; no dependency or native component changed. Model Manager/download controls are disabled until M4 as the brief permits. Pending Owner walkthrough means this report is not a claim that every M3 acceptance criterion has passed. The event-loop test covers a real small batch; extended workload profiling is deferred in BACKLOG.md.

## 6. Issues

| ID | Severity | Status | Summary |
|---|---|---|---|
| ISSUE-009 | S2 | Resolved | Existing Google Drive profile-only heuristic omitted streaming mounts; documented local configuration is now read without network access. |
| ISSUE-010 | S2 | Resolved | PM screenshot corrections, including task-specific translation help and visible control boundaries. |

No new S0/S1 issue. Sync detection remains advisory: arbitrary mirrored locations may be undetectable, and stale vendor configuration may cause a conservative warning.

## 7. Decisions needed from PM/Owner

1. Review screenshots and return desktop walkthrough pass/fail results. Recommendation: retain the PR as draft until the human acceptance evidence is supplied; report any failing step for correction before M3 acceptance. No scope or dependency decision is requested.

## 8. Actions needed from the Owner

Run from the existing checkout with the M2 engine/model assets already fetched:

```powershell
cd C:\Users\kdash\whisper_app
git checkout m3-gui
git pull --ff-only
uv run python -m dusty
```

Use public fixtures and a fresh ignored build/ output folder. Initial graphics setup may take about 13 seconds while Preparing remains visible. Send pass/fail by step number and the visible problem for failures; do not send recordings, transcript text, hints or unredacted logs. These results are pending, not inferred from automation.

| Step | Action | Expected result |
|---|---|---|
| 1 | Launch for the first time. | Welcome explains local processing and the exact accuracy disclaimer; choose an output folder to continue. If already welcomed, report that the welcome was previously completed. |
| 2 | Inspect the empty window. | Large drop area with Add files/Add folder; Options button visible; no crowded settings panel. |
| 3 | Add `tests/fixtures/audio/formats/jfk.wav` using Add files. | One queued row; output location visible; Text and Word checked by default; Start available after preparation. |
| 4 | Add the same file again. | No duplicate row; duplicate count shown. |
| 5 | Add the formats folder, then try dropping a folder and using Include subfolders. | Folder options are shown; supported recordings are added, duplicates ignored, and counts reported. |
| 6 | Select a row, move it up/down using the right-click menu or Alt+Up/Alt+Down, and remove it using Remove; use Tab and Shift+Tab between controls. | Queue order/selection updates; removal does not delete the recording; keyboard focus is visible and can leave vocabulary hints. |
| 7 | Open the Options dialog. | A modal dialog opens without resizing or rearranging the main window; current choices remain summarized; only installed choices are selectable; Manage models is disabled with an explanation. |
| 8 | Select Small English if installed, then inspect language/task. | Language is English and locked; incompatible translation is disabled with a plain explanation. |
| 9 | Choose Use Medium instead if offered, or select Medium and Translate to English. | The valid combination is selected. On Processor only, the slow-choice warning appears without blocking Start. Return to Tiny and Transcribe for the remaining public English tests. |
| 10 | Enter more than about 800 characters of harmless example vocabulary hints, then shorten them. | Soft warning appears and clears; field is multi-line with helper/example text. Do not send the field contents back. |
| 11 | Choose Processor only, then Automatic. | The device choice survives preparation; Recommended labels update; preparation never reopens Welcome or Resume. |
| 12 | Choose Done in Options and Start. | Files process sequentially; Preparing is shown before progress, rows/overall progress update, and the window remains movable and responsive. |
| 13 | During an active file, click Cancel current file. | That row becomes Cancelled, remaining files continue, and the cancelled file leaves no partial output. |
| 14 | Inspect the summary and Open output folder. | Counts agree with rows; Only nonzero counts appear, failed recordings have names/reasons, and Open folder with transcripts is primary; Word/text outputs open normally; Done dismisses the saved batch history. No recording is modified. |
| 15 | Clear the queue, add the same public files again, and Start. At the collision dialog choose Keep both with apply-to-all. | Existing transcripts remain; new outputs have matching numbered suffixes; one remembered choice covers remaining collisions. |
| 16 | Clear/add `tests/fixtures/audio/bad/`, then Start. Inspect a failed row by double-clicking and try Retry failed files. | Bad files fail individually, batch finishes, plain error/action appears, and retry does not overwrite recordings. |
| 17 | Clear/add the public mostly-silence fixture plus JFK; turn off Skip silent parts for time to interact. Start, then close during processing and choose Stop and save. Relaunch and Resume. | Close is asynchronous; unfinished batch is offered; completed outputs are retained; remaining files can finish. Restore Skip silent parts on afterwards. |
| 18 | Choose Light then Dark under Options and resize the window. | Text, focus, queue, dialogs and primary action remain legible in both palettes; Start stays reachable. |
| 19 | If OneDrive/Dropbox/Google Drive is available, choose an output folder inside it and Start a public-fixture batch. | A cloud-sync warning offers Continue or another folder. Choosing another folder prevents that run from starting; acknowledging warns once per folder in this session. If unavailable, report N/A; automated coverage exists. |
| 20 | Check at Windows 100%, 150% and, if available, 200% scaling; close and relaunch. | Controls remain usable, dialogs fit, and saved preferences/output location/theme/window geometry return. Restore your preferred Windows scale afterwards. |

Detailed companion: docs/pm/M3-walkthrough.md. The Owner handles merging and publication; neither was performed.

## 9. Risks for the next milestone

- Native Windows walkthrough, keyboard behavior and actual display scaling still require Owner evidence.
- M4 must preserve the separate downloader process and the runtime/static networking boundary while replacing the disabled model-management control.
- The real Surface Vulkan smoke test remains required before M7 under the accepted M1 conditional GO; it does not block M3.
- File/history deletion is not secure erasure. Sync-folder warnings cannot disable another program's uploads.

## 10. Time/effort notes

The main work was safe asynchronous worker/dialog coordination, preserving in-progress choices and recovery, and reproducible offscreen rendering. The PM review added modal layout and copy corrections; painted-border tests caught the need to preserve native arrows and explicit check/radio marks while improving contrast. Empty offscreen font enumeration initially produced unusable glyphs; the final reviewed artifact uses installed fonts and validates glyph support. CI now exercises both headless and Qt-driven processing inside the WFP audit window. No elapsed engineering-hour estimate is asserted.
