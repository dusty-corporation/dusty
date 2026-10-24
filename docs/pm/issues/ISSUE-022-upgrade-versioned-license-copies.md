# ISSUE-022 - Obsolete versioned license copies survive upgrade

- Severity: S1
- Milestone: M5
- Status: In progress, fix implemented; true-upgrade rerun pending

## Evidence and root cause

Release v0.5.0-m5.8, CI 40066137913, passed source and packaged gates but failed
the installed inventory after upgrading .4. Two old files remained under
licenses/dusty/dusty-0.5.0.dev4.dist-info/licenses: LICENSE and NOTICE.
Package metadata paths include the version, so Inno's normal overwrite did not
replace these names. The strict installed gate correctly rejected them; it is
unchanged. No draft release or installer upload followed this failed gate.

## Fix

Before file installation, the extracted guarded current app checks obsolete
Dusty metadata-license folders. Only the exact two own-license files, in a
strict versioned namespace, byte-identical to the current bundled LICENSE and
NOTICE, are eligible. All folders are preflighted; linked/protected paths,
unknown entries, changed bytes or unreadable metadata preserve the files and
block upgrade with a plain explanation. Recheck each hash immediately before
unlink; remove only the now-empty two directories. No wildcard or recursive
deletion, no model/data/output removal, no installed inventory exception.

Unit regressions cover matching copies and changed/unknown/linked/protected
content. The original true-upgrade gate must pass before any safe-build claim.
