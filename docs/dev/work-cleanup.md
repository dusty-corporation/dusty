# Work ownership and safe destinations

ISSUE-020 repair, approved by PM on 2026-10-23.

`dusty.work_area.OwnedWork` exclusively creates a random purpose-prefixed folder.
Its `.dusty-owned.json` records schema 1, the exact directory name, purpose and
SHA-256 hashes of explicitly named files produced by Dusty's operation. Purposes
are job, probe, selftest and device-probe. Every cleanup checks the full flat
inventory, reparse ancestors and saved protection references before removing any
file. Unknown content, changed files or invalid metadata preserves the folder.
No recursive work deletion is used. The only skip log is the exact enum
`work_cleanup=preserved`, admitted by the privacy redaction filter.

Settings and queue metadata protect output folders, sources and output files.
Malformed metadata blocks cleanup. Startup moves no files: an old internal
output selection is cleared, its location is retained in `preserved_paths`, and
a one-time message asks for another folder. Logging also refuses to create or
rotate files in a protected log subtree. The GUI and coordinator reject new
managed-area source/destination choices, including resolved aliases and outputs
saved beside a recording. `RuntimePaths.install_dir` covers the complete frozen
installation. Development builds protect native/resource/model folders without
treating the whole build directory as an installation.

The uninstaller shares the work inventory check. Its other removals are limited
to schema-checked app metadata, named log files and manifest model files, after
all protection and reparse checks. Unknown work directories are retained even
when empty; unknown app-data files cause a kept-data notice.

Stale model prefixes need an exact hash receipt in the matching `.lock` file:
byte zero is reserved for the OS lock, followed by JSON with schema 1, purpose
model-download, the partial filename and its SHA-256. Transfer attempts record
the receipt before releasing the lock. Automatic cleanup requires age over seven
days and a matching receipt. A forced crash before receipt creation can leave an
unproven prefix; it is preserved, even after seven days. A recent prefix can
still resume and must pass the final full size/hash check. Normal user cancel
removes only the current manifest partial after the child has stopped.

Windows junction and symbolic-link regressions use synthetic targets outside
the test work area. Both targets must survive. Current checks use pathname
preflight, not handle-relative traversal; concurrent malicious path replacement
is listed in AUDIT-NOTES.md for the independent audit.
