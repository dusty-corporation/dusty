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
- `%LOCALAPPDATA%/Dusty/work/<purpose-random ID>/`: temporary decoded audio and
  native transcription JSON. A local ownership marker records the purpose and
  hashes of the temporary files Dusty created. Cleanup removes only matching
  owned content. Unknown, changed, linked or protected content is preserved,
  including after a crash. Graphics-probe and self-test work use separate random
  folders under the same work area. The hashes are not uploaded or logged.
  An OS-held lease prevents another running instance's startup cleanup from
  removing active work. A process exit releases that lease. This does not make
  two windows' shared queue/settings a supported concurrent editing workflow.
- `%LOCALAPPDATA%/Dusty/models/`: downloaded and hash-verified model data in an
  installed app. Development models/binaries use ignored `build/` directories.
  Downloads use `.part` files until verification succeeds; cancelling or closing
  Dusty normally during a download removes the partial. A crash/forced close
  can leave a recent partial for verified resumption. Startup removes partials
  older than seven days only when a matching local ownership/hash receipt proves
  what they are. Unknown or changed prefixes remain. A lock file coordinates
  downloads and holds the receipt. These are public model data, not recordings.
- `%LOCALAPPDATA%/Dusty/logs/`: rotating redacted diagnostics with statuses and
  numeric timings, not recording names/paths, transcript text or vocabulary hints.
- `%LOCALAPPDATA%/Dusty/logs/native-diagnostic.jsonl`: passive capture of one
  exact Windows diagnostic, with module basenames/offsets, native frames, numeric
  thread ID and a fixed app-phase label only. No arguments, Python locals,
  recording paths, transcripts or prompts. Best effort, bounded to 128 KiB;
  unsafe/unwritable/full storage is left alone. Nothing is uploaded and exception
  dispatch is not suppressed. Cleanup helpers do not hold this file open.
- Transcripts are saved only to the chosen destination. Clearing history or
  the queue does not delete recordings or exported transcripts.
- App-managed folders cannot be selected for recordings or transcripts. If an
  older saved destination points there, Dusty preserves it and asks for another
  folder. Settings retain that location as a protected path so later cleanup
  does not guess that its files are disposable.
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
It uses the Windows certificate store plus four bundled, fingerprint-checked public
CA roots and checks every redirect. It does not retrieve missing Windows roots
or contact a Microsoft update host. Certificate files are local public trust data;
no certificate refresh runs at startup or in the background. GitHub and normal
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
can mean manual review is needed. Fresh-machine installer acceptance is still pending Owner confirmation.

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

## Installer graphics check

Before model selection, Setup temporarily extracts the same installed payload
and runs a bounded child in a Windows Job Object. It opens no model and makes no
network requests. It checks physical graphics support and a small local buffer
operation, then discards the probe files. A hang or crash falls back to Small.
The post-download transcription tests are separate and can fail even when the
probe passed. Setup itself does not download: it launches dusty-fetch only after
the inline model-download consent. Closing or crashing Setup kills its children.

## Interrupted writes and retained destinations

Normal cancellation removes the active public-model prefix when the filesystem
allows it. If another program locks it or access is denied, the prefix may stay;
an open download dialog or Setup reports the failed cleanup. It is not a verified
model and cannot be used until the complete size and hash match. A closed app
does not promise that an OS-denied removal succeeded.

A crash before an atomic write completes may leave a unique .dusty-tmp beside
its destination. The final file remains the previous complete file or the new
complete file. Dusty does not sweep transcript folders to remove unfamiliar
files. These local temporaries are not transmitted.

Legacy destinations recorded in preserved_paths stay protected during uninstall,
including the whole subtree and its protection metadata. In that case removal
reports retained data rather than guessing which contents are disposable.

Before native uninstall removes registered application files, a separate
preflight checks saved and preserved destinations against the installation
folder. An overlap or unreadable protection metadata stops uninstall before
application removal. No model manifest or networking is needed for this check.
