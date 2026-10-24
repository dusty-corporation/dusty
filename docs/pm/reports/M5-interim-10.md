# M5 interim 10 - Second-review preservation repair

## Owner actions

Use only a disposable VM and public/synthetic files with .9/.10. Do not publish
them or use them with real data. The second review reproduced ISSUE-023: legacy
destination protection persisted in preserved_paths was omitted by uninstall's
initial inspector. A synthetic catalog-named file was removed; no Owner profile
or real recording was touched. A new repaired pair will be named in M5-report.md.

## Repair and independent work

The approved ISSUE-020 policy already requires preserving that entire subtree.
The one-key fix and enabled regression implement it without a new exception or
PM decision. Source, packaged/installed WFP and uninstall reruns follow. The
requested adversarial review continues on repository-local fixtures, including
OS locks, reparse points, Unicode/long paths, synced outputs and interrupted cleanup.

The .9 to .10 run 40068461160 passed all original gates, but did not cover this
persisted-protection state. Its result is retained honestly; it is superseded
as final-candidate evidence until the new regression is included.
