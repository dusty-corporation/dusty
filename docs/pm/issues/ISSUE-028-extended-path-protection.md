# ISSUE-028 - Extended Windows namespace bypassed path protection comparisons

- Severity: S0 / NN-7 boundary risk, found without deleting any data
- Milestone: M6
- Status: Resolved on M6; source and native protection regression passed
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

## Resolution, 2026-10-24

Commit 8818032 repairs the comparison boundary. Candidate run 40124502580
passed the full source suite (392 passed, two expected skips) and both real
registered-uninstaller protection attempts: ordinary and extended saved paths
returned exit 1, with the synthetic protected bytes, application and metadata
unchanged. The manifest was restored before installed-file inventory, installed
WFP/canary and all 64 installed PE checks passed. The later new UI-driver failure
was separate; that overall run is failed and is not full installer acceptance.
Replacement candidate 40125713083 reruns the entire lifecycle.

This closes the M6 protection defect, not a claim that frozen M5 is repaired or
that M6 has been published. The M5 backport remains an explicit PM decision.

Final candidate 40125892713 (fc2c6e5) passed every job, both installed-protection
spellings, the actual one-confirmation UI, installed inventory/PE/WFP/canary,
both uninstall choices, cancellation/retry and unchanged output sentinels.
The complete native lifecycle now has a passing receipt; M5 remains frozen.

## PM distribution decision, 2026-10-24

No M5 backport. M5 merges after the Owner VM pass, then M6 merges immediately.
No M5-only build is distributed to anyone. The first build for real use is M7
from main after M6. Frozen .13/.14 are test-only and not for distribution.
