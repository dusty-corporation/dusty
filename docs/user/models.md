# Choose a transcription model

A model is a local data file that lets Dusty recognize speech. Download once,
then use it offline. A larger model can use more memory and take longer. The
recommended choice depends on whether your graphics card works with Dusty.

| Choice in Dusty | Use it for |
|---|---|
| Large v3 Turbo: Best quality | Transcription with a working graphics card; many spoken languages. It cannot translate to English. |
| Small: Balanced, all languages | A practical general choice, including processor-only computers. Technical name: Small. |
| Small English: Balanced, English only | English recordings on any computer. Technical name: Small English. It cannot translate. |
| Tiny: Fastest | Short checks or when speed matters more than accuracy. |
| Medium: Translates to English | Translate supported spoken languages to English. Slower and more memory hungry. |

Choose the spoken language if you know it. English-only models fix it to English.
Switching back to a multilingual model restores your previous language choice.
Translation is visibly unavailable when the selected model does not support it.
Processor-only use of a slow model shows a warning; no timing estimate is promised.

## Manage local models

Open **Manage models**, also available under Tools. Each model shows its size,
status and a description; the dialog shows free space on the model drive.

- **Download** asks permission to connect to github.com and shows progress.
  Voice detection is included when needed. Cancel or close Dusty during a
  download to stop it and remove its partial file. After a normal stop, the next attempt starts fresh. After a crash or forced
  close, a recent partial may resume; full size and SHA-256 are still checked.
  Startup removes partials older than seven days only when its local record
  confirms they belong to a download. Unknown or changed files are kept.
- **Installed** means the local file passed its SHA-256 check against the catalog
  bundled with your app. **Damaged** means it failed verification; Dusty will not
  use it. Choose Download again.
- **Verify all** checks the local files again. It does not download anything.
- **Delete** lets you remove any model, including the selected or last one.
  Deleting the model chosen in Options asks for a specific confirmation and
  clears that choice. Choose a transcription model in Options before starting
  again. Deleting the last model returns to the download prompt.
- Voice detection can also be deleted. If Skip silent parts is on, confirm its
  warning; Start is unavailable until you download Voice detection again or turn
  Skip silent parts off in Options.
- A newly downloaded model is selected only when no model is chosen. Downloads
  never replace your current selection. The main recommendation prompt appears
  only when no transcription model is installed; recommendations remain visible
  in Model Manager and Options once any model is installed.

Models live under `%LOCALAPPDATA%\Dusty\models`, separately from the app files.
If another program prevents partial-file removal, Dusty reports that it was kept
while the download dialog is open. Close that program before retrying. A leftover
partial cannot be used as a model without the full size and file check.
Do not substitute an arbitrary model or manifest from another website. Adding
models after installation is an explicit online action; transcription stays offline.
