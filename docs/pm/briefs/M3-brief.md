# Current milestone: M3 - GUI (single file and batch)

Proceed per `docs/pm/SPEC.md` section 12 M3. Branch: `m3-gui`, created from the latest `main`. Archive the M2 brief to `docs/pm/briefs/M2-brief.md` first. This brief adds PM requirements on top of the spec. Where they conflict, this brief wins.

## Design goal
The primary user is a non-technical adult. She should be able to transcribe a folder of lectures without reading any instructions: drop files, press one button, get Word documents. Everything else is optional and out of her way. When in doubt, choose fewer controls, plainer words, and safe defaults.

## Carry-over from M2
- Confirm whether the approved `backend_probe` removal from the Owner's real `%LOCALAPPDATA%\Dusty\settings.json` is done. If not, do it now (that entry only), and confirm the session-wide guard that fails any test touching the real app-data folder is in place.

## Requirements beyond SPEC M3

### 1. Default screen (simple mode)
- Empty state: one large drop area ("Drop recordings or folders here") with "Add files" and "Add folder" buttons.
- Once files are queued: the queue table, an output location line, the format checkboxes (default TXT and DOCX), and one prominent **Start** button.
- Model, language, task, vocabulary hints, collision policy, and Advanced (device, threads, VAD) live in a collapsible "Options" panel, collapsed by default. A one-line summary of the current choices sits next to it (e.g. "Large v3 Turbo, auto-detect language, graphics card").

### 2. Model choice rules from ADR 0016, in the UI
- The default model follows the backend probe: Turbo q8_0 when Vulkan works, Small on CPU-only. Show it as "Recommended".
- Only installed models are selectable. Model Manager is M4: until then, a disabled "Manage models" entry with a tooltip is fine.
- Selecting Translate with Turbo or a `.en` model: disable the combination with a plain explanation and a one-click "Use Medium instead" if Medium is installed.
- On CPU-only machines, Medium and Turbo show the slow-model warning before Start (not as a blocking error).
- The first Vulkan run on a fresh machine can take about 13 s of one-time setup (M2). Progress must show a "Preparing..." state instead of looking frozen at 0%.

### 3. Vocabulary hints
- A multi-line field with helper text and an example ("Names, medications, acronyms, separated by commas").
- The soft warning at the token limit documented in M1/M2. Never logged.

### 4. Copy and tone
- All user-facing text lives in one module (`app/messages.py` or similar) so it can be reviewed and later translated.
- Plain English, no jargon. Avoid "VAD", "RTF", "backend", "inference", "model file" in simple mode. Advanced may use technical terms with a one-line explanation.
- Use the approved privacy and medical-accuracy wording from SPEC 9.6 exactly.
- No em or en dashes in any UI text (AGENTS.md rule 12).

### 5. Screenshots for PM review
- Add a script that renders each main screen headlessly via Qt and saves PNGs: empty state, queued batch, options expanded, running batch with progress, collision dialog, summary dialog, resume prompt, first-run welcome, sync-folder warning, each error message dialog. Light and dark theme, at 100% and 150% scaling.
- Attach them as a zip to a draft release `m3-screenshots` (not committed, per the repo-size rule). Include the link in the report so the PM can review the UI without running it.

### 6. Responsiveness
- The coordinator runs off the UI thread. Add an automated check that the UI event loop is never blocked for more than 200 ms during a real batch (SPEC M3 acceptance).

## Out of scope for M3
Model download and management (M4), installer and packaging (M5), in-app transcript editor, recording, speaker labels (backlog).

## Owner walkthrough
Provide a numbered checklist in the report (about 15 to 20 steps) for the Owner to run on the desktop with `uv run python -m dusty`: first run, add a folder, start, cancel one file, collision handling, close mid-batch and resume, dark mode, and a sync-folder warning (using a OneDrive folder if present). Each step states the expected result, so the Owner can answer pass or fail per step.

## Reporting
Interim report only for decisions affecting correctness, privacy, licensing, or the user experience. Final `docs/pm/reports/M3-report.md` with SPEC M3 acceptance evidence, the screenshot link, the walkthrough checklist, and test and CI results. Then stop.
