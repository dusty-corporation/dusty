# M3 Report - GUI (single file and batch)

## 1. Summary

The Owner reviewed M3 on the ThinkPad (i7-1365U, Iris Xe, Tiny, Vulkan): 16 checks passed, checks 1 and 8 failed, and checks 6 and 17 were not reported. This revision fixes the supplied output-folder, model-choice, AMR, run-flow, wording and keyboard findings; the AMR failure was a duration-preflight assumption, not a missing native decoder. All 106 local tests pass, and the regenerated screenshot asset has 136 images. A short changed-behavior re-test is still pending, so human acceptance remains partial. No M4 work has started; PR #4 remains a draft.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Add files/folder, local drop, duplicate handling, reorder/remove | met | pytest-qt controls and scanner tests. |
| Start/cancel, collisions/apply-all, summary, close/save/resume | met | Actual native batches through MainWindow and the shared coordinator; cancellation and output preservation asserted. |
| Model rules and simple defaults | met | Installed-model selection; backend-dependent recommendation; English-only lock; incompatible translation disabled; Medium action; slow warning; explicit replacement when a resume model is missing. |
| UI event loop gap at most 200 ms during a real batch | met | Public JFK, Tiny CPU, two threads, TXT+DOCX; 10 ms precise Qt timer and GUI-thread delivery assertions. The final real-batch integration test passes the 200 ms maximum-gap assertion. This measures the tested batch, not every possible recording or workload. |
| Centralized copy, exact privacy/accuracy wording, vocabulary hints | met | app/messages.py; copy/model-control tests; multi-line hints and soft warning based on the verified approximate 800-character prompt threshold. |
| Themes, scaling, required dialogs and screenshots | met | 136 synthetic PNGs: 34 states in light/dark at 100%/150%; font glyph validation and key-image visual inspection. Native display review is pending below. |
| Owner walkthrough | partial | ThinkPad: 16 passed, steps 1/8 failed and now corrected; 6/17 unreported. Eight changed-behavior re-test checks are in section 8. |
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

[Draft m3-screenshots release](https://github.com/dusty-corporation/dusty/releases/tag/untagged-c09275afcc8084a0f275).
Use **m3-screenshots-thinkpad-fixes.zip**, 3,693,812 bytes, SHA-256:
`340623ad93b4abe209b606482ba9249871a803895fa488f2665413052911a48f`.
GitHub's uploaded digest matches. All earlier ZIPs are retained; the release is still a draft and may require authenticated access. The Owner can relay the reviewed ZIP to the PM.

Reproduce with `uv run python tools/render_gui.py`. Screens include empty/waiting/modal options/vocabulary/advanced, invalid translation selection, preparing/transcribing/saving, collision, summary, resume, welcome, sync warning and every failure-code dialog. Names and progress are synthetic, not transcription or performance evidence. Installed Windows Segoe UI is loaded only if offscreen Qt has no fonts; no font is redistributed.

### ThinkPad correction evidence

- Output location is always visible, including Not chosen yet in warning color; File offers a destination chooser. Missing destination disables Start with a plain hint, with no automatic Documents/OneDrive default.
- Purpose-first names retain technical identifiers. A local probe and manifest speed class select conservative M1 ThinkPad estimates, explicitly labelled as similar-laptop estimates; docs/dev/gui.md records all source RTFs and rounding. English-only Translate is visibly unavailable with an explanation; the previous multilingual language is restored, and the slow warning is inside Options.
- Pinned native checks show AMR demuxing and amrnb/amrwb decoding enabled. FFprobe exits 0 with an audio stream and no duration; FFmpeg decodes the same file with exit 0. Unknown duration remains -- until decoding; the decoded WAV supplies duration to Whisper. Real coordinator and actual-window add/start regressions transcribe jfk.amr successfully.
- The coordinator snapshots prior outputs and reserves names per run. Same-stem WAV/AMR files auto-number even after the first Keep both choice against an older transcript; a later run asks again about pre-existing transcripts. The collision dialog names the existing .txt file and holds the current row/status at Waiting for your choice.
- Resume starts immediately; unfinished elapsed values reset. Finished-list guidance and Tools > Clear finished are present. A zero-success summary hides Open folder with transcripts and makes Done primary.
- Add counts use correct plurals and omit zeros; duplicates name/highlight the existing row briefly without a popup. Corrupt-file advice is now appropriate to MP3. Add folder has one title. Tab leaves the list and arrow keys navigate rows.
- `uv run python tools/fetch_dev_binaries.py --recommended-models` completed and verified both recommended models with pinned hashes, preserving the published model release. An initial concurrent fetch hit WinError 5 on a DLL used by native tests; the approved elevated retry after tests completed succeeded. No ACL, ownership, location or permission workaround was used.

### PM review verification

- Translation help and Medium action are hidden during Transcribe; regressions cover invalid Translate choices.
- Opening modal Options leaves the main table geometry unchanged. Only Text and Word remain in the main format row; SRT/VTT/JSON still persist under More formats.
- Overall progress is hidden while idle. One formatter keeps bottom/row phase labels consistent, including zero-progress preparation.
- Collision radios, filenames, Stop, nonzero summary counts, failure reasons and the primary Open folder with transcripts action are tested.
- Move actions are in the context menu with actual Alt+Up delivery tested after focus; main edit buttons are Add files, Add folder, Remove and Clear list.
- Border contrast against window/input/button backgrounds measures **4.324/4.612/4.100:1 in light mode** and **7.014/7.728/5.098:1 in dark mode**, exceeding 3:1. Actual painted-boundary tests cover check/radio, push/tool, combo/spin, text, table and scroll controls; key screens were visually reviewed in both themes. Native OS dialogs still need the Owner's desktop review.

## 4. Test results

Final code revision: 1ff2327, following d58e629, 62dc03d and b4c9ae5. Local Windows checks:

- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: 88 files already formatted.
- `uv run mypy`: passed, 54 source files.
- `uv run python tools/measure_coverage.py`: **106 passed in 89.06 s** (runs the entire pytest suite with tracing).
- All three policy checks passed: check_no_network.py, check_no_huggingface.py, check_licenses.py.

| Required package | Hit / executable lines | Coverage |
|---|---|---|
| core | 104/111 | 93.7% |
| export | 130/132 | 98.5% |
| models | 117/124 | 94.4% |
| queue | 462/497 | 93.0% |
| privacy | 80/84 | 95.2% |
| Combined | 893/948 | 94.2% |

Every required package exceeds 85%. These figures do not claim GUI widget line coverage; 23 dedicated Qt/theme/presentation tests cover the M3 behaviors, including four actual native GUI integrations.

Final revision CI:

- [PR run 39854200159](https://github.com/dusty-corporation/dusty/actions/runs/39854200159): checks and offline passed; **105 passed, 1 skipped in 196.01 s**, coverage 94.2%.
- [Push run 39854194307](https://github.com/dusty-corporation/dusty/actions/runs/39854194307): checks and offline passed; **105 passed, 1 skipped in 265.02 s**, same coverage.
- Both WFP logs: `WFP calibration passed; selftest passed; batch passed; gui passed; connection_events=0`. Positive blocked-event calibration and cleanup passed.
- The only skip is the existing usable-Vulkan-device comparison on hosted CI; all 106 tests pass on the desktop, including that comparison. No skip was added.
- [Draft PR #4](https://github.com/dusty-corporation/dusty/pull/4) remains open and unmerged. Subsequent report-only commits may queue their own CI runs.

Previous revisions and their evidence remain in git history. No test was
skipped, disabled or weakened to make these corrections pass.

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
| ISSUE-011 | S1 | Resolved | AMR audio was rejected solely because FFprobe omitted source duration; native decode works. |
| ISSUE-012 | S2 | Resolved | ThinkPad workflow/copy corrections with targeted regressions and re-test checklist. |

No new S0/S1 issue. Sync detection remains advisory: arbitrary mirrored locations may be undetectable, and stale vendor configuration may cause a conservative warning.

## 7. Decisions needed from PM/Owner

1. Return pass/fail on the eight targeted re-tests below. Recommendation: keep PR #4 as draft until the corrected behavior is confirmed; no dependency, native pin or new scope decision is needed.

## 8. Owner results and focused re-test

Owner evidence received 2026-10-22, ThinkPad i7-1365U / Iris Xe, Tiny, Vulkan:

| Original walkthrough steps | Owner result |
|---|---|
| 2, 3, 4, 5, 7, 9, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20 | Passed |
| 1 | Failed: Welcome X left an empty screen without a visible output-folder choice; persistence itself already worked. |
| 8 | Failed: English-only Translate looked selectable and did nothing. |
| 6, 17 | Not reported; no pass is inferred. |

Step 15 explicitly verified Keep both, Replace and Skip. Step 20 was at 150%
scaling and confirmed settings and the output folder persist across launches.
The additional AMR failure and other requested corrections are covered by the
new regressions and remain subject to the focused re-test, not retroactively
counted as Owner passes.

Close Dusty before fetching so Windows releases its native DLLs. Use a fresh
repo-local test profile to check Welcome X without editing your real settings:

```powershell
cd C:\Users\kdash\whisper_app
git checkout m3-gui
git pull --ff-only
uv run python tools/fetch_dev_binaries.py --recommended-models
$savedDustyLocalAppData = $env:LOCALAPPDATA
$env:LOCALAPPDATA = Join-Path $PWD ("build\m3-owner-retest-" + (Get-Date -Format yyyyMMdd-HHmmss))
uv run python -m dusty
```

Relaunch with `uv run python -m dusty` in that same terminal/profile. Afterwards
restore `$env:LOCALAPPDATA = $savedDustyLocalAppData`. The app chooses no output
destination automatically; select a fresh folder deliberately in the UI.

| Check | Changed behavior and expected result |
|---|---|
| 1 | Close Welcome with X. The empty screen still shows Save transcripts to, Not chosen yet in warning color, Choose folder, and the choose-output hint. File > Choose where to save transcripts also works. No destination is automatically chosen. Select a fresh folder for these public test outputs. |
| 2 | Open Options. Purpose labels lead, technical names are secondary, and the speed estimate/caution is visible. Choose Medium with Processor only: the slower-than-recording warning must be visible inside Options. |
| 3 | Pick Persian, then Balanced, English only. Language locks to English; Translate is visibly unavailable with a reason. Pick Balanced again: Persian returns. Restore Auto-detect, Transcribe, Fastest (Tiny), and Automatic for the English fixture checks. |
| 4 | Add jfk.wav and jfk.amr from tests/fixtures/audio/formats. AMR may initially show --. Both must transcribe successfully; same-run outputs get matching numbered suffixes without a collision prompt for the second recording. |
| 5 | Clear list and add those two recordings again. Only the first name collision should ask, naming the existing .txt file. While the dialog is open the current row/bottom line say Waiting for your choice. Choose Keep both without apply-to-all; the second same-name recording is numbered without another prompt. |
| 6 | After completion, the disabled Start has the everything-is-done explanation. Tools > Clear finished removes completed/skipped rows. Add the same recording twice: singular/plural counts omit zeros, its name says already in the list, and the existing row highlights briefly without a popup. Tab leaves the list; arrow keys move between rows. |
| 7 | Run only a corrupt MP3 from tests/fixtures/audio/bad. Advice says it may be damaged and suggests saving again as WAV if another player can open it. With zero successes, Open folder with transcripts is hidden and Done is primary. Add folder has its description only once. |
| 8 | Add the public mostly-silence recording plus JFK; disable Skip silent parts to allow time. Start, close during processing with Stop and save, relaunch, then choose to pick up where you left off. It starts immediately without another Start click; unfinished elapsed times reset. Restore Skip silent parts afterwards. |

Send pass/fail by check number and only the visible problem for failures; no
recordings, transcripts, vocabulary hints or unredacted logs. Companion:
docs/pm/M3-retest.md. The original script remains in M3-walkthrough.md for
reference. The Owner handles merging and release publication.

## 9. Risks for the next milestone

- The ThinkPad already passed 150% scaling and persistence. Changed behavior needs the eight targeted re-tests; original steps 6/17 were unreported.
- M4 must preserve the separate downloader process and the runtime/static networking boundary while replacing the disabled model-management control.
- The real Surface Vulkan smoke test remains required before M7 under the accepted M1 conditional GO; it does not block M3.
- File/history deletion is not secure erasure. Sync-folder warnings cannot disable another program's uploads.

## 10. Time/effort notes

The main work was safe asynchronous worker/dialog coordination, preserving in-progress choices and recovery, and reproducible offscreen rendering. The PM review added modal layout and copy corrections; painted-border tests caught the need to preserve native arrows and explicit check/radio marks while improving contrast. Empty offscreen font enumeration initially produced unusable glyphs; the final reviewed artifact uses installed fonts and validates glyph support. CI now exercises both headless and Qt-driven processing inside the WFP audit window. No elapsed engineering-hour estimate is asserted.
