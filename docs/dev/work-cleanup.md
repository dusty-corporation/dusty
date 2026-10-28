# Work ownership and safe destinations

ISSUE-020 repair, approved by PM on 2026-10-23.

`dusty.work_area.OwnedWork` exclusively creates a random purpose-prefixed folder.
Its `.dusty-owned.json` records schema 1, the exact directory name, purpose and
SHA-256 hashes of explicitly named files produced by Dusty's operation. Purposes
are job, probe, selftest and device-probe. The lock is flushed to disk before
use. A generated file is flushed before its hash is written. Marker updates are
written to a temporary file, flushed, then atomically renamed. Queue and
settings files already use the same flush and replace pattern.

A crash can leave `audio.wav` or `raw.json` before its hash is recorded. Cleanup
accepts only those two pending names in an owned job folder after acquiring and
holding its exclusive OS lease; it still verifies every recorded file's hash.
A recorded file already removed by an interrupted cleanup may be absent. A
temporary marker from a failed atomic rename may also be removed.

The published v1.0.0 build wrote markers in place without a durability flush.
The maintainer observed a job marker with 270 zero bytes and a lock with one zero
byte after a VM host crash. Recovery for that legacy case requires a direct
child of the managed `work` root named `job-<uuid>`, an all-zero marker of one
of the three exact v1.0.0 job-marker sizes (189, 270 or 350 bytes), an available
exclusive lease with the expected one-byte content, and only the marker, lock,
`audio.wav` and optional `raw.json` as regular non-reparse files. The resolved
parent must equal the exact managed work root supplied by the startup or
uninstall caller; a different folder merely named `work` cannot qualify. A
zero-filled marker still requires its existing lock. For a valid JSON marker
whose lock was already removed by v1.0.0 cleanup, Dusty may recreate the
expected one-byte lock exclusively, acquire it and repeat the normal checks.
Protection
references still take precedence. This is restricted to the private app-owned
work root, which Dusty never accepts as a recording or output destination. It
does not infer ownership for an arbitrary name-matched folder elsewhere.

Every cleanup checks reparse ancestors and saved protection references before
removing any file. Unknown content, changed recorded files or other invalid
metadata preserves the folder. No recursive work deletion is used. No age
threshold applies to owned work; startup and uninstall attempt the same check.
The only skip log is the exact enum
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
was examined during the independent audit; see the cleanup regression tests.
