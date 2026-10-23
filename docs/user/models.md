# Choose a transcription model

A model is a local data file that lets Dusty recognize speech. Download once,
then use it offline. A larger model can use more memory and take longer. The
recommended choice depends on whether your graphics card works with Dusty.

| Choice in Dusty | Use it for |
|---|---|
| Best quality (Large v3 Turbo) | Transcription with a working graphics card; many spoken languages. It cannot translate to English. |
| Balanced (all languages) | A practical general choice, including processor-only computers. Technical name: Small. |
| Balanced (English only) | English recordings on any computer. Technical name: Small English. It cannot translate. |
| Fastest (Tiny) | Short checks or when speed matters more than accuracy. |
| Best for translating to English (Medium) | Translate supported spoken languages to English. Slower and more memory hungry. |

Choose the spoken language if you know it. English-only models fix it to English.
Switching back to a multilingual model restores your previous language choice.
Translation is visibly unavailable when the selected model does not support it.
Processor-only use of a slow model shows a warning; no timing estimate is promised.

## Manage local models

Open **Manage models**, also available under Tools. Each model shows its size,
status and a description; the dialog shows free space on the model drive.

- **Download** asks permission to connect to github.com and shows progress.
  Voice detection is included when needed. Cancel safely leaves a partial file
  that a later download can resume, including after restarting Dusty.
- **Installed** means the local file passed its SHA-256 check against the catalog
  bundled with your app. **Damaged** means it failed verification; Dusty will not
  use it. Choose Download again.
- **Verify all** checks the local files again. It does not download anything.
- **Delete** asks for confirmation. First choose a different installed model if
  the one you want to remove is selected. You cannot remove the last installed
  transcription model through the manager.

Models live under `%LOCALAPPDATA%\Dusty\models`, separately from the app files.
Do not substitute an arbitrary model or manifest from another website. Adding
models after installation is an explicit online action; transcription stays offline.
