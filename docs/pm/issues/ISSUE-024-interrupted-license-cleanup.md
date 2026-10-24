# ISSUE-024 - Interrupted obsolete-license cleanup could not resume

- Severity: S1
- Milestone: M5
- Status: Resolved, final native gates passed in CI 40099284709

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

f9b39f9 / .11 passed every native/source/license/installed gate, with a true
upgrade and no leftover migration receipt in the exact installed inventory.
All 49 adversarial cases, including actual abrupt child exit and safe retry,
pass. The .11 to .12 paired draft run is separate final-candidate evidence.
