# M6 interim 1 - Extended path protection

## Summary

A predicate-only regression found ISSUE-028, an NN-7 path-boundary risk. Extended
and ordinary spellings of the same Windows folder did not compare as the same
protected root. No deletion was attempted, no Owner data was touched and nothing
was published. The source repair follows the already-approved ownership rule;
94 focused tests pass and native verification now checks both spellings.

## Owner actions

Keep .13/.14 frozen and use public/synthetic fixtures in the VM. Do not select
app-managed folders using extended namespace aliases. PM must decide separately
whether to backport a repair to M5; the engineer changed no M5 code or draft.
M6 native activation and the real Qt diagnostic producer remain separate gaps.

## Authorized continuation

The current PM instruction requires autonomous hardening without waiting for
the Owner. No new correctness/privacy policy is being invented: this enforces
the existing ISSUE-025 protection for all spellings. Unrelated work was paused
until source protection tests passed; only verified M6 candidate gates may
produce review artifacts. Final report will retain the finding and native result.

## Native protection result

ISSUE-028 is resolved on M6 at 8818032. Candidate 40124502580 passed both
actual protected-uninstaller refusals with sentinel/application/metadata intact,
then installed inventory, WFP/canary and PE gates. Its later UI discovery failure
means overall installer acceptance failed; replacement 40125713083 is pending.
No M5 code or frozen draft was changed. Final M6 report separates those results.
