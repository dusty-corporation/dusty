# ISSUE-023 - Uninstall omitted persisted legacy destination protection

- Severity: S0 (NN-7), isolated synthetic regression; no Owner data touched
- Milestone: M5
- Status: Resolved, 2026-10-24; installed preservation gate passed

## Root cause and containment

After sanitize_output moved a legacy internal output to preserved_paths,
uninstall's initial metadata inspector omitted that key. A synthetic file at a
catalog filename under the preserved destination was removed. The regression
test failed on .9/.10 implementation. No real profile was accessed.

.9/.10 remain draft, not final candidates after this review finding. Their VM
checks use disposable synthetic files only. No publication or deletion of any
release, tag, run or artifact. A repaired pair follows all gates.

## Approved repair scope

The existing PM decision requires preserving every saved legacy destination
subtree and its protection metadata. Include preserved_paths in the initial
uninstall inspection before any deletion, not only work cleanup. No new policy,
permission or exception is requested. The new enabled regression and original
ISSUE-020 tests must pass with full source/package/installed/uninstall gates.

## Resolution

f9b39f9 / v0.5.0-m5.11, CI 40099284709: every job passed. The actual new
installed exe refused uninstall-data for a sanitized preserved destination,
retained its metadata, and preserved verified model hashes/write times.
Receipt preserved_legacy_destination=passed is mandatory for final release
staging; a false/missing receipt is rejected. Packaged/installed PE/license/WFP,
normal cancel/retry, model-preserving true upgrade, both normal uninstalls and
unrelated transcript sentinel pass. Full local source: 339 passed/1 skip, 94.2%
required coverage. Final .11 to .12 safe-pair run follows as separate acceptance.
