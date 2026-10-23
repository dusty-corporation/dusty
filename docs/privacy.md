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
  hints, appearance, window geometry and local graphics-probe cache. Settings
  can reveal private terms and folder names even though the log is redacted.
- `%LOCALAPPDATA%/Dusty/state/queue.json`: recording/output paths and batch
  choices, including vocabulary hints, required to resume an unfinished batch.
  Clear history removes it. Dismissing a completed batch summary also removes it.
- `%LOCALAPPDATA%/Dusty/work/<job UUID>/`: temporary decoded audio and native
  transcription JSON. The coordinator removes the directory on success,
  failure and cancellation. Startup removes abandoned per-job directories.
  Short graphics-probe and self-test work also lives under the work folder.
- `%LOCALAPPDATA%/Dusty/models/`: downloaded and hash-verified model data in an
  installed app. Development models/binaries use ignored `build/` directories.
  Downloads use `.part` files until verification succeeds; cancellation may leave
  a resumable partial model. A lock file coordinates downloads. These are model
  data, not recordings.
- `%LOCALAPPDATA%/Dusty/logs/`: rotating redacted diagnostics with statuses and
  numeric timings, not recording names/paths, transcript text or vocabulary hints.
- Transcripts are saved only to the chosen destination. Clearing history or
  the queue does not delete recordings or exported transcripts.
- Corrupt or unfamiliar settings/state may be renamed with a `.corrupt-` suffix
  for safe recovery. These backups can retain the same private paths or hints.
- App files normally live under `%LOCALAPPDATA%/Programs/Dusty`, separately from
  user data. The split `dusty/` folder processes recordings; `dusty-fetch/` is
  the separate downloader. Shared `bin/` and `resources/` hold native engines,
  decoder, bundled model catalog and public-domain self-test clip, not your audio.

The app's processing package has no networking imports. A startup Python audit
hook blocks socket operations; Windows CI uses firewall rules and WFP auditing
for self-test, a headless batch and a batch driven through the Qt window.
Downloading is reserved for the separate explicit downloader, dusty-fetch. The
Model Manager asks before starting it; the installer uses it for selected models
and voice detection. It requests public model files over HTTPS from exactly
`github.com` and the verified redirect host `release-assets.githubusercontent.com`.
It uses the Windows certificate store and checks every redirect. GitHub and normal
network infrastructure can see the download connection and requested public asset.
No recording, transcript, vocabulary hint or local recording metadata is included
in that request. A bundled catalog provides expected SHA-256 values; no remote
catalog is fetched. Downloads verify before the final filename is created.

App startup, processing, translating, exporting, verifying or deleting an existing
model do not require a connection. There are no telemetry, crash uploads, update
checks, remote processing or automatic background model downloads. The app's
Python audit guard is installed at startup. Required platform DLL imports are
exactly pinned and checked separately from the network-capable downloader.
Windows CI audits offline processing and GUI-triggered download scenarios:
the downloader may connect, while processing components must have zero events.

## Removing local data

Clear history removes the saved unfinished-recording state. Dismissing a completed
summary also clears it. This does not erase settings, hints in settings, corrupt
backups, exported transcripts or recordings. Clear hints in Options to change
what future settings and unfinished-work state contain.

The draft uninstaller offers to keep or remove downloaded models. It removes
recognized app-owned settings, state, logs and work data while preserving user
output folders and recordings. It refuses unsafe links, corrupt protection
metadata or unfamiliar files rather than deleting broadly. A preservation notice
can mean manual review is needed. Installer acceptance is still in progress.

## Sync folders and device security

A cloud-sync service may upload files placed in its folders independently of
Dusty. The GUI warns for detected sync destinations before processing and lets
you choose another folder or explicitly continue. The acknowledgement lasts for
that folder in the current app session. Detection is a warning aid, not a way
to disable another program's sync behavior.

Anyone with access to your Windows account or administrator rights may be able
to read local state and outputs. Dusty does not encrypt recordings, local state
or transcripts itself. Protect the account and computer, consider disk encryption,
and follow your organization's retention and backup rules. Temporary-file deletion
is not secure erasure; copies in backups or sync services may remain. Network
isolation is not a claim of absolute security or regulatory certification.
