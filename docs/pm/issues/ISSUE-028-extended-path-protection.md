# ISSUE-028 - Extended Windows namespace bypassed path protection comparisons

- Severity: S0 / NN-7 boundary risk, found without deleting any data
- Milestone: M6
- Status: Source repair verified; native validation pending
- Environment: Windows, extended drive path compared with ordinary drive path

## Root cause and finding

Path.resolve preserves a caller-supplied extended namespace. pathlib therefore
compared an extended path and ordinary spelling of the same managed folder as
different anchors. The managed-destination predicate returned false for the
extended spelling. A legacy saved protected path in that spelling could also
miss the installer-root comparison. Existing reparse and long-output tests did
not compare both namespace spellings at the protection boundary.

The reproducer only evaluated predicates. No source/transcript was deleted,
no Owner profile was accessed and no release was changed. Unrelated work stopped
while the existing ownership policy was repaired and tested. This changes no
PM decision: every spelling of a protected destination must remain protected.

## Repair

work_area.canonical resolves then normalizes supported Windows namespace
spellings only for comparisons. Actual I/O paths keep their extended form for
long-path support. Unsupported device namespaces fail closed. Managed roots,
saved protection metadata, uninstall, obsolete-license cleanup, partial cleanup
and source/output collision checks share this comparison convention.

## Evidence and remaining action

94 boundary/ownership/cleanup/upgrade/adversarial tests pass, 6.71 s. The new
test creates only synthetic files, proves extended managed paths are refused,
and requires uninstall_allowed/cleanup to preserve the registered sentinel and
its protection metadata. The native installed test now repeats the real
protected-uninstall case with ordinary and extended saved paths.

The Owner explicitly froze M5 code/.13/.14; they remain unchanged. PM decides
whether a separate M5 repair is needed. Until that decision, do not use those
drafts for private data or choose app-managed folders via namespace aliases.
Only M6 is repaired. No new exception, dependency, network path or publication.
