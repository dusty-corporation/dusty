# 0040 - Extension points

- Status: Proposed, for PM review
- Date: 2026-11-10

## Context

An optional feature had been built straight into shared code. It needed its
own field in batch options, a job status, segment and transcript fields,
rendering in every format, an option, a dialog and messages in the window, a
catalog section and downloader rule for its model, and resolvers for its
helper program. Even with the option off, saved queues and settings gained a
key for it.

Optional features must be removable from shared code. Dusty without them
must behave exactly as Dusty 1.2.0 did.

## Decision

1. `dusty.extensions` defines the extension points: options, stages after
   transcription, output decorations, actions on finished files, extra models
   and helper programs, plus the texts an extension shows.
   `docs/dev/extensions.md` lists the shared code that uses each point.
2. An extension is one package. It is imported statically, so the offline
   checks see exactly what is imported. If it is not installed, every list is
   empty. If it fails to import for any other reason, that is an error.
3. Shared types carry generic values only:
   - `BatchOptions.extension_options`, the keys of options that are on;
   - `JobStatus.PROCESSING`, with the stage's own status text;
   - `annotations` on segments and transcripts;
   - `Job.stage_status` and `Job.stage_failed`.

   Saved queues and settings hold `extension_options` only while an option is
   on, so no extension key can collide with a core setting. Options not
   installed or not supported on this computer load as off, and their stages
   never run.
4. Labels from decorations are rendered generically:
   - TXT and DOCX start a new paragraph where the label changes, with the label in bold;
   - SRT cues start with "label: ";
   - VTT uses the label as the cue voice;
   - JSON gets the fields the decoration returns.
5. An extension model has its own catalog file in the resources folder, marked
   `"kind": "extension"`. Its file name matches `dusty-*.onnx`, and the
   downloader accepts that name only from such a file, so the bundled manifest
   accepts what 1.2.0 accepted. It is verified by size and SHA-256 like every
   other model. A catalog file that is
   not there leaves its model out; a damaged one is an error.
6. Goldens made from the 1.2.0 source (49f698e) prove the second half of the
   context: every format through `write_outputs`, a saved queue and the
   window's settings. Dusty with no extensions must match them byte for byte,
   and outputs must still match with the extension present but off. DOCX
   entries carry the time they were written, in 1.2.0 too, so DOCX goldens are
   compared entry by entry.

## Consequences

- An optional feature registers through these points and leaves nothing of
  its own in shared app code; only the loader names its package.
- Helper programs reach the app builds through one optional file,
  `packaging/addons/programs.json`, read by `tools/helper_programs.py`.
  Without it, the specs, bundle checks, notices, installer and CI build and
  check exactly the programs of 1.2.0. A public build fails if its GUI holds
  an add-on module.
- `rewrite_outputs` and the in-memory `Job.transcript` and `Job.written` stay
  shared. They are a generic safe rewrite for an action.
- Tests of the extension points use a made-up extension, so they still run
  with the optional feature removed.

## Amendment 2026-11-11: About lines, Help commands, changing reasons

Three more points, each empty and inert in public Dusty:

- `about`: functions that return lines About shows after the version;
- `commands`: Help menu entries;
- an option's `unsupported` text may be a function, asked again on every
  refresh of Options.

## Amendment 2026-11-11: engine hints

`engine_hints` give the engine a prompt while an option is on, only for the
listed languages, only while the option is supported, and only when the user
gave no hints of their own. A hint may keep steering through the whole
recording (`--carry-initial-prompt`). If the user gave hints, the engine gets
exactly the user's prompt as in 1.2.0: carrying the user's hints with a hint's
text can start repetition loops. Neither text is ever logged. Without an
active hint, the engine gets exactly the arguments of 1.2.0.
