# M3 Report - GUI (single file and batch)

## 1. Summary

The Owner's ThinkPad re-test (i7-1365U, Iris Xe, recommended models installed)
passed all eight checks functionally, as relayed by the PM on 2026-10-22. The
final polish makes messages clearer, simplifies model copy and error dialogs,
and suppresses Welcome whenever an output folder is set. Functional human
acceptance is complete; the new screenshot asset is ready for the PM's visual review and M3 CI is green. Packaging remains on its separate
accepted spike branch; M3 does not include an installer.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Add files/folder, local drop, duplicate handling, reorder/remove | met | pytest-qt controls and scanner tests. |
| Start/cancel, collisions/apply-all, summary, close/save/resume | met | Actual native batches through MainWindow and the shared coordinator; cancellation and output preservation asserted. |
| Model rules and simple defaults | met | Installed-model selection; backend-dependent recommendation; English-only lock; incompatible translation disabled; Medium action; slow warning; explicit replacement when a resume model is missing. |
| UI event loop gap at most 200 ms during a real batch | met | Public JFK, Tiny CPU, two threads, TXT+DOCX; 10 ms precise Qt timer and GUI-thread delivery assertions. The final real-batch integration test passes the 200 ms maximum-gap assertion. This measures the tested batch, not every possible recording or workload. |
| Centralized copy, exact privacy/accuracy wording, vocabulary hints | met | app/messages.py; copy/model-control tests; multi-line hints and soft warning based on the verified approximate 800-character prompt threshold. |
| Themes, scaling, required dialogs and screenshots | met | 164 synthetic PNGs: 41 states in light/dark at 100%/150%; font glyph validation and key-image visual inspection. ThinkPad functional review passed, including 150% scaling; final polish is presented for screenshot review. |
| Owner walkthrough | met | ThinkPad original 18 passes plus all eight targeted re-tests PASS functionally, PM/Owner confirmation 2026-10-22; original steps 6/17 also passed. |
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
Use **m3-screenshots-final-polish.zip**, 3,962,955 bytes, SHA-256:
`031f699e9f6abaf2bfb0eb1d6571fe8a30da0eabe11e45b04329a6f38c540f2c`.
GitHub's uploaded digest matches. All earlier ZIPs are retained; the release is still a draft and may require authenticated access. The Owner can relay the reviewed ZIP to the PM.

Reproduce with `uv run python tools/render_gui.py`. Screens include empty/waiting/modal options/vocabulary/advanced, invalid translation selection, preparing/transcribing/saving, collision, summary, resume, welcome, sync warning and every failure-code dialog. Names and progress are synthetic, not transcription or performance evidence. Installed Windows Segoe UI is loaded only if offscreen Qt has no fonts; no font is redistributed.

### ThinkPad correction evidence

- Output location is always visible, including Not chosen yet in warning color; File offers a destination chooser. Missing destination disables Start with a plain hint, with no automatic Documents/OneDrive default.
- Transcription model replaces Accuracy and speed. Balanced (all languages) and Balanced (English only) retain technical names in the secondary details. All time estimates/extrapolation are removed. Only a CPU-only slow manifest class shows the Balanced suggestion, inside Options and beside its main summary. English-only Translate remains visibly disabled and the previous language is restored.
- Pinned native checks show AMR demuxing and amrnb/amrwb decoding enabled. FFprobe exits 0 with an audio stream and no duration; FFmpeg decodes the same file with exit 0. Unknown duration remains -- until decoding; the decoded WAV supplies duration to Whisper. Real coordinator and actual-window add/start regressions transcribe jfk.amr successfully.
- The coordinator snapshots prior outputs and reserves names per run. Same-stem WAV/AMR files auto-number even after the first Keep both choice against an older transcript; a later run asks again about pre-existing transcripts. The collision dialog names the existing .txt file and holds the current row/status at Waiting for your choice.
- Resume starts immediately; unfinished elapsed values reset. Finished-list guidance and Tools > Clear finished are present. A zero-success summary hides Open folder with transcripts and makes Done primary.
- Add counts use correct plurals and omit zeros; duplicates name/highlight the existing row briefly without a popup. Error dialogs now show only the file name and plain reason, without advice. Add folder has one title. Tab leaves the list and arrow keys navigate rows.
- `uv run python tools/fetch_dev_binaries.py --recommended-models` completed and verified both recommended models with pinned hashes, preserving the published model release. An initial concurrent fetch hit WinError 5 on a DLL used by native tests; the approved elevated retry after tests completed succeeded. No ACL, ownership, location or permission workaround was used.

### PM review verification

- Translation help and Medium action are hidden during Transcribe; regressions cover invalid Translate choices.
- Opening modal Options leaves the main table geometry unchanged. Only Text and Word remain in the main format row; SRT/VTT/JSON still persist under More formats.
- Overall progress is hidden while idle. One formatter keeps centered-message/row phase labels consistent, including zero-progress preparation.
- Collision radios, filenames, Stop, nonzero summary counts, failure reasons and the primary Open folder with transcripts action are tested.
- Move actions are in the context menu with actual Alt+Up delivery tested after focus; main edit buttons are Add files, Add folder, Remove and Clear list.
- Border contrast against window/input/button backgrounds measures **4.324/4.612/4.100:1 in light mode** and **7.014/7.728/5.098:1 in dark mode**, exceeding 3:1. Actual painted-boundary tests cover check/radio, push/tool, combo/spin, text, table and scroll controls; key screens were visually reviewed in both themes. Native OS dialogs still need the Owner's desktop review.

## 4. Test results

Final UI code revision: 4997333; final screenshot renderer and Owner-result documentation: a01c6fb. Local Windows checks:

- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: 88 files already formatted.
- `uv run mypy`: passed, 54 source files.
- `uv run python tools/measure_coverage.py`: **112 passed in 98.15 s** (runs the entire pytest suite with tracing).
- All three policy checks passed: check_no_network.py, check_no_huggingface.py, check_licenses.py.

| Required package | Hit / executable lines | Coverage |
|---|---|---|
| core | 104/111 | 93.7% |
| export | 130/132 | 98.5% |
| models | 117/124 | 94.4% |
| queue | 462/497 | 93.0% |
| privacy | 80/84 | 95.2% |
| Combined | 893/948 | 94.2% |

Every required package exceeds 85%. These figures do not claim GUI widget line coverage; 29 dedicated Qt/theme/presentation tests cover the M3 behaviors, including four actual native GUI integrations.

Final polish CI:

- [PR run 39889192873](https://github.com/dusty-corporation/dusty/actions/runs/39889192873)
  at a01c6fb: checks and offline passed; 111 passed, one hosted-Vulkan skip in 193.22 s; coverage 94.2%.
- [Earlier code PR run 39888876056](https://github.com/dusty-corporation/dusty/actions/runs/39888876056)
  at 4997333: checks and offline passed; 111 passed, one unavailable-Vulkan skip
  in 192.97 s, 94.2% coverage.
- WFP calibration passed; selftest, headless batch and GUI passed with
  connection_events=0. The desktop full suite has no skips; CI's single Vulkan
  comparison skip is unchanged. No test was disabled or weakened.
- [Draft PR #4](https://github.com/dusty-corporation/dusty/pull/4) was accepted by the PM and merged by the Owner as e66788b.

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
not a WER or literary-quality claim. On 2026-10-22 the Owner confirmed by
listening that the exact source interval [107, 122) seconds is a complete
spoken Farsi quatrain. The fixture is now Owner-verified.

Prohibited-character verification (all tracked repository text):

```powershell
$pattern = [string][char]0x2013 + '|' + [char]0x2014
git grep -n -I -E $pattern -- .
```

Output: no lines; git grep exit code 1 (no matches). No history was rewritten.

## 5. Deviations from SPEC

The PM explicitly replaced the original expanding Options panel with a modal dialog, moved extra formats into it, and revised the dialogs and copy. These approved changes supersede the earlier M3 brief for those controls; no dependency or native component changed. Model Manager/download controls are disabled until M4 as the brief permits. The Owner has now passed all eight targeted functional re-tests; the final screenshot polish follows that accepted behavior. The event-loop test covers a real small batch; extended workload profiling is deferred in BACKLOG.md.

## 6. Issues

| ID | Severity | Status | Summary |
|---|---|---|---|
| ISSUE-009 | S2 | Resolved | Existing Google Drive profile-only heuristic omitted streaming mounts; documented local configuration is now read without network access. |
| ISSUE-010 | S2 | Resolved | PM screenshot corrections, including task-specific translation help and visible control boundaries. |
| ISSUE-011 | S1 | Resolved | AMR audio was rejected solely because FFprobe omitted source duration; native decode works. |
| ISSUE-012 | S2 | Resolved | ThinkPad workflow/copy corrections with targeted regressions and re-test checklist. |

No new S0/S1 issue. Sync detection remains advisory: arbitrary mirrored locations may be undetectable, and stale vendor configuration may cause a conservative warning.

## 7. Decisions needed from PM/Owner

None. The PM accepted M3 and the Owner merged PR #4; the engineer did not merge.

## 8. Owner results

The original ThinkPad walkthrough used i7-1365U / Iris Xe, Tiny and Vulkan:
18 passed, with initial output-folder/English-only-Translate failures at steps
1/8. The PM corrected the record for steps 6 and 17: both passed. Step 15
verified Keep both, Replace and Skip; step 20 passed at 150% scaling and confirmed
settings/output-folder persistence.

**2026-10-22 final re-test: all eight targeted checks PASS functionally**, on the
ThinkPad with recommended models installed. This includes output choice,
model/language rules, AMR decoding, same-run numbering, existing-output collision
handling, finished-list and keyboard behavior, zero-success summary, and immediate
recovery. The completed script is retained in M3-retest.md as a historical record.
The remaining PM feedback is visual/copy polish implemented in this revision,
not a request to repeat the functional walkthrough.

## 9. Risks for the next milestone

- ThinkPad functional re-test, 150% scaling and persistence have passed; final visual changes remain for PM screenshot review.
- M4 must preserve the separate downloader process and the runtime/static networking boundary while replacing the disabled model-management control.
- The real Surface Vulkan smoke test remains required before M7 under the accepted M1 conditional GO; it does not block M3.
- File/history deletion is not secure erasure. Sync-folder warnings cannot disable another program's uploads.

## 10. Time/effort notes

The main work was safe asynchronous worker/dialog coordination, preserving in-progress choices and recovery, and reproducible offscreen rendering. The PM review added modal layout and copy corrections; painted-border tests caught the need to preserve native arrows and explicit check/radio marks while improving contrast. Empty offscreen font enumeration initially produced unusable glyphs; the final reviewed artifact uses installed fonts and validates glyph support. CI now exercises both headless and Qt-driven processing inside the WFP audit window. No elapsed engineering-hour estimate is asserted.

## Final PM polish after the functional re-test

- Centered 16 px status/general-warning area directly under the recording list.
  Output-required/finished-list and other Start blockers appear beside Start.
- All dialogs use the native title bar only; no duplicate body heading. Error
  content is exactly the file name and plain reason, without recovery advice.
- Transcription model and distinct Balanced labels; no per-hour estimates or
  similar-laptop caveats. CPU-only slow choices warn in both Options and the main window.
- Welcome checks for an output folder, including older settings without
  welcome_seen. Re-entry/once-per-window guards and synchronous dialog execution
  ensure Welcome finishes before recovery. Already-chosen folders suppress it.
- New regressions cover message position/font, all titleless dialog bodies,
  reason-only errors, model labels/no estimates/CPU warning matrix, folder-based
  Welcome suppression and re-entrant welcome-before-resume order.

