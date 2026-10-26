# Public path reparse boundaries

Reviewed 2026-10-25: [Microsoft reparse tags](https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-point-tags)
and [IsReparseTagNameSurrogate](https://learn.microsoft.com/en-us/windows/win32/api/winnt/nf-winnt-isreparsetagnamesurrogate).
The name-surrogate bit is 0x20000000. Public recording scans and transcript
outputs reject that bit (including symlink A000000C and mount/junction A0000003),
not the reparse attribute alone. Cloud Files 9000001A/9000101A/9000F01A and
non-surrogate placeholder/WOF/app-execution tags remain eligible. Actual file I/O
can still fail if a provider cannot hydrate a recording. OneDrive's sync and
hydration run outside Dusty; make recordings available locally before offline use.
Private ownership, deletion, installer, partial and log checks retain their
conservative all-reparse rule. The public-path exception does not broaden them.


## Settings first publication

N-2 read errors retry for 0.5 s in 25 ms intervals. A fresh path whose metadata
proves absence returns a marked missing snapshot without freezing the GUI. Saving
that snapshot always re-reads. If still absent, a complete fsynced temporary is
published exclusively with os.rename on Windows (os.link on POSIX). A competing
file causes another read/merge, never a default overwrite. This is not a general
transactional merge of arbitrary concurrent changes to the same settings field.
[Python 3.12 os.rename](https://docs.python.org/3.12/library/os.html#os.rename)
documents FileExistsError for an existing Windows destination. The actual
Windows race regression verifies that behavior; no final file is opened for
partial in-place initialization (reviewed 2026-10-25).
