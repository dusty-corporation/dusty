# M3 desktop walkthrough

Use public fixtures for this review; send pass/fail by step number, not
recordings, transcripts, vocabulary hints or unredacted logs. M2 binary/model
assets must already be fetched. The approved old probe-cache cleanup is done.

```powershell
cd C:\Users\kdash\whisper_app
git pull --ff-only
uv run python -m dusty
```

The working branch for this review is `m3-gui`. Initial graphics preparation
may take about 13 seconds; the window should continue repainting and responding.
Use a fresh output folder under ignored `build/` for these public test outputs.

| Step | Action | Expected result |
|---|---|---|
| 1 | Launch for the first time. | Welcome explains local processing and the exact accuracy disclaimer; choose an output folder to continue. If already welcomed, report that the welcome was previously completed. |
| 2 | Inspect the empty window. | Large drop area with Add files/Add folder; Options collapsed; no crowded settings panel. |
| 3 | Add `tests/fixtures/audio/formats/jfk.wav` using Add files. | One queued row; output location visible; Text and Word checked by default; Start available after preparation. |
| 4 | Add the same file again. | No duplicate row; duplicate count shown. |
| 5 | Add the formats folder, then try dropping a folder and using Include subfolders. | Folder options are shown; supported recordings are added, duplicates ignored, and counts reported. |
| 6 | Select a row, move it up/down and remove it using the buttons; use Tab and Shift+Tab between controls. | Queue order/selection updates; removal does not delete the recording; keyboard focus is visible and can leave vocabulary hints. |
| 7 | Expand Options. | Current choices remain summarized; only installed choices are selectable; Manage models is disabled with an explanation. |
| 8 | Select Small English if installed, then inspect language/task. | Language is English and locked; incompatible translation is disabled with a plain explanation. |
| 9 | Choose Use Medium instead if offered, or select Medium and Translate to English. | The valid combination is selected. On Processor only, the slow-choice warning appears without blocking Start. Return to Tiny and Transcribe for the remaining public English tests. |
| 10 | Enter more than about 800 characters of harmless example vocabulary hints, then shorten them. | Soft warning appears and clears; field is multi-line with helper/example text. Do not send the field contents back. |
| 11 | Choose Processor only, then Automatic. | The device choice survives preparation; Recommended labels update; preparation never reopens Welcome or Resume. |
| 12 | Collapse Options and Start a batch. | Files process sequentially; Preparing is shown before progress, rows/overall progress update, and the window remains movable and responsive. |
| 13 | During an active file, click Cancel current file. | That row becomes Cancelled, remaining files continue, and the cancelled file leaves no partial output. |
| 14 | Inspect the summary and Open output folder. | Counts agree with rows; Word/text outputs open normally; Done dismisses the saved batch history. No recording is modified. |
| 15 | Clear the queue, add the same public files again, and Start. At the collision dialog choose Keep both with apply-to-all. | Existing transcripts remain; new outputs have matching numbered suffixes; one remembered choice covers remaining collisions. |
| 16 | Clear/add `tests/fixtures/audio/bad/`, then Start. Inspect a failed row by double-clicking and try Retry failed files. | Bad files fail individually, batch finishes, plain error/action appears, and retry does not overwrite recordings. |
| 17 | Clear/add the public mostly-silence fixture plus JFK; turn off Skip silent parts for time to interact. Start, then close during processing and choose Stop and save. Relaunch and Resume. | Close is asynchronous; unfinished batch is offered; completed outputs are retained; remaining files can finish. Restore Skip silent parts on afterwards. |
| 18 | Choose Light then Dark under Options and resize the window. | Text, focus, queue, dialogs and primary action remain legible in both palettes; Start stays reachable. |
| 19 | If OneDrive/Dropbox/Google Drive is available, choose an output folder inside it and Start a public-fixture batch. | A cloud-sync warning offers Continue or another folder. Choosing another folder prevents that run from starting; acknowledging warns once per folder in this session. If unavailable, report N/A; automated coverage exists. |
| 20 | Check at Windows 100%, 150% and, if available, 200% scaling; close and relaunch. | Controls remain usable, dialogs fit, and saved preferences/output location/theme/window geometry return. Restore your preferred Windows scale afterwards. |

Return results as `1 pass, 2 pass, ...`, identifying the step and visible
problem for any failure. Native desktop behavior is Owner evidence, distinct
from the automated offscreen suite and synthetic screenshot matrix.
