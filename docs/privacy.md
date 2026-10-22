# Privacy and local data

Dusty processes your recordings entirely on this computer. After installation,
it never needs an internet connection, and it never sends your audio or
transcripts anywhere.

Automatic transcripts can contain mistakes, especially with names, medications,
and numbers. Always review a transcript before relying on it for medical,
legal, or other important decisions.

## What is stored

- `%LOCALAPPDATA%/Dusty/settings.json`: selected model, language, task, formats,
  output folder, collision policy, device, threads, silence detection, vocabulary
  hints, appearance, window geometry, welcome state and local graphics-probe cache.
- `%LOCALAPPDATA%/Dusty/state/queue.json`: recording/output paths and batch
  choices, including vocabulary hints, required to resume an unfinished batch.
  Clear history removes it. Dismissing a completed batch summary also removes it.
- `%LOCALAPPDATA%/Dusty/work/<job UUID>/`: temporary decoded audio and native
  transcription JSON. The coordinator removes the directory on success,
  failure and cancellation. Startup removes abandoned per-job directories.
- `%LOCALAPPDATA%/Dusty/models/`: downloaded and hash-verified model data in an
  installed app. Development models/binaries use ignored `build/` directories.
- `%LOCALAPPDATA%/Dusty/logs/`: rotating redacted diagnostics with statuses and
  numeric timings, not recording names/paths, transcript text or vocabulary hints.
- Transcripts are saved only to the chosen destination. Clearing history or
  the queue does not delete recordings or exported transcripts.

The app's processing package has no networking imports. A startup Python audit
hook blocks socket operations; Windows CI uses firewall rules and WFP auditing
for self-test, a headless batch and a batch driven through the Qt window.
Downloading is reserved for the separate explicit downloader; model management
is not enabled in the M3 interface. There are no telemetry or update checks.

## Sync folders and device security

A cloud-sync service may upload files placed in its folders independently of
Dusty. The GUI warns for detected sync destinations before processing and lets
you choose another folder or explicitly continue. The acknowledgement lasts for
that folder in the current app session. Detection is a warning aid, not a way
to disable another program's sync behavior.

Anyone with access to your Windows account or administrator rights may be able
to read local state and outputs. Temporary-file deletion is not secure erasure.
Full user documentation and release checklists are completed in M6.
