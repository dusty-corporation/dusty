# Local data and privacy

Dusty processes recordings entirely on this computer. The main app has a
Python socket audit hook and does not make network requests. Native FFmpeg is
built without network protocols, and its input protocol whitelist is
`file,pipe`. The separate future model downloader will be an explicit user
action. The development asset fetcher is not shipped.

Dusty reads source recordings but does not modify them. It writes chosen
transcript formats to the chosen output folder. A folder managed by OneDrive,
Dropbox, or Google Drive may sync those outputs; Dusty warns when it recognizes
such a folder. The sync provider's behavior is outside Dusty's control.

Local app data is under `%LOCALAPPDATA%\Dusty`:

| Location | Contents | Removal |
|---|---|---|
| `models/` | Downloaded model files | User-managed model removal; installer behavior comes in M5 |
| `settings.json` | Preferences and cached backend probe | Reset settings or uninstall |
| `state/queue.json` | Current batch, source paths, output paths, vocabulary hints, status | Delete after dismissing a finished batch with Clear history |
| `work/<job UUID>/` | Decoded WAV and temporary engine JSON | Removed after each job; abandoned UUID work directories removed at next startup |
| `logs/dusty.log*` | Numeric timings, job UUIDs, model, backend, status | Rotating 5 files of at most 1 MB each; user can remove them |

Transcript text, recording names and paths, and vocabulary hints are never
written to logs. Temporary files are deleted normally, without a secure-wipe
claim. Outputs may remain in the user-selected folder after clearing history.
