# M3 Owner re-test: completed

On 2026-10-22 the PM relayed the Owner's ThinkPad result: **all eight checks
PASS functionally** (i7-1365U, Iris Xe, recommended models installed).
The original test instructions below record what was tested; their speed
estimates and error advice are superseded by the final PM polish in M3-report.md.
No repeat of this eight-check walkthrough is requested.

## Historical instructions for the completed re-test

```powershell
cd C:\Users\kdash\whisper_app
git checkout m3-gui
git pull --ff-only
uv run python tools/fetch_dev_binaries.py --recommended-models
$savedDustyLocalAppData = $env:LOCALAPPDATA
$env:LOCALAPPDATA = Join-Path $PWD ("build\m3-owner-retest-" + (Get-Date -Format yyyyMMdd-HHmmss))
uv run python -m dusty
```

The fresh profile is inside the repo, leaving your real app settings untouched.
For relaunches in steps below, use `uv run python -m dusty` in the same terminal
so it keeps that same test profile. Restore the terminal environment afterwards:
`$env:LOCALAPPDATA = $savedDustyLocalAppData`.

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

Send pass/fail by number, describing only the visible failure. Do not send
recordings, transcript text, vocabulary hints or unredacted logs.
