# Current milestone: M4 - Model Manager and dusty-fetch

Proceed per `docs/pm/SPEC.md` section 12 M4 and section 6.6. Branch: `m4-downloader`, rebased onto the latest `main` (M3 is merged). Archive the M3 brief to `docs/pm/briefs/M3-brief.md` first. This brief adds PM requirements on top of the spec. Where they conflict, this brief wins.

## Already done (accepted downloader prework, M4-interim-1)
`dusty-fetch` CLI: download and verify, standard library only, HTTPS to exactly github.com and release-assets.githubusercontent.com, redirect checks, resumable `.part` files, SHA-256 against the bundled manifest, disk-space check, clean cancellation, JSON-lines progress, documented exit codes, local-TLS tests, CI-only real download of Tiny. Do not redesign it; build on it.

## M3 carry-over nits (do first)
1. The Start button stays full width at all times. When disabled, show the reason just above it (centered), not beside it.
2. Label pattern: "Best quality (Large v3 Turbo), recommended" instead of "(Large v3 Turbo) (Recommended)". Apply the same pattern to every model label.
3. Raise the disabled Start text contrast in dark mode (still clearly disabled).

## Model Manager (SPEC 6.6)
- Replace the disabled "Manage models" button with a working Model Manager dialog. Also reachable from Tools.
- Lists every model in the bundled catalog with: plain label (same labels as Options), technical name secondary, size, and status: Installed, Not installed, Damaged, Downloading.
- Shows free disk space on the drive holding the models folder.
- Actions: Download, Cancel download, Delete (with confirmation), Verify all (re-hash).
- Cannot delete the model currently selected in Options without choosing another first. Cannot delete the last installed model.
- Download confirmation states plainly that Dusty will connect to github.com to download N MB, and that nothing else is sent. Use one approved sentence in messages.py.
- Progress per download (percent, MB done of total), from dusty-fetch's JSON lines. Resume works after cancel or app restart.
- A damaged model (hash mismatch) shows "Damaged" with a "Download again" action, and is never used for transcription.

## Main window integration
- When the recommended model is not installed, the main window message area says so with a one-click "Download it" action that opens the Model Manager on that model. Replace the current "Choose an installed model" text.
- If no models are installed at all, Start is disabled with the reason above it ("Download a transcription model first") and a button that opens the Model Manager.
- After a download completes, Options and the main window update immediately (no restart), and the recommended model becomes selected if nothing else was chosen.

## Process and network boundary (must hold)
- The GUI never imports `dusty_fetch`. It launches `dusty-fetch` as a child process (inside a Job Object, like the engine) and reads its JSON lines.
- Resolve the `dusty-fetch` executable for dev (`uv run`) and for the packaged split layout from M5-interim-4. Test both paths.
- Extend the WFP network-isolation test with a Model Manager download scenario: Dusty's own process must have zero connection events during the entire download, while dusty-fetch's connections are allowed. Report both counts.
- Static no-network check unchanged, zero exceptions.

## Tests
- pytest-qt: list and statuses, download with progress using the local TLS test server, cancel, resume after restart, hash mismatch to Damaged, delete rules, Verify all, disk-space display, recommended-model prompt, no-models state.
- Real-network test stays CI-only.

## Out of scope
Installer (M5). Enterprise proxy (backlog). Changing the catalog.

## Reporting
Interim report only for decisions affecting correctness, privacy, licensing, or the user experience. Final `docs/pm/reports/M4-report.md` with SPEC M4 acceptance evidence, regenerated screenshots (new asset on a draft `m4-screenshots` release) covering the Model Manager states and the main-window prompts, the WFP results for the download scenario, test and CI results, and a short Owner check list (about 6 steps) for the ThinkPad. Then stop. Do not open a PR against main until the PM accepts the report.
