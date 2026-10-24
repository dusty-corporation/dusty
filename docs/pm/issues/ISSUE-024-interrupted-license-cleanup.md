# ISSUE-024 - Interrupted obsolete-license cleanup could not resume

- Severity: S1
- Milestone: M5
- Status: Fixed, final native gates pending

The second-review child exited abruptly with os._exit(91) after the first actual
unlink. The remaining NOTICE survived, but a subsequent upgrade refused the
incomplete pair. A purpose/directory/hash ownership receipt is now exclusively
created before removal. It permits missing previously removed files on retry,
while modified receipt/content, unknown files and reparse points still preserve
and block. The receipt is removed only after its known contents are gone.
An empty unmarked version folder is preserved rather than guessed app-owned.

Actual abrupt-process-exit recovery and changed receipt/remaining-file/unknown
entry tests pass. No external/private files or Owner profile touched. The
strict installed-file and license gates remain unchanged.
