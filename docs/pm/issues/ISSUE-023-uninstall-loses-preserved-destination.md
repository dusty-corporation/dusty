# ISSUE-023 - Uninstall omitted persisted legacy destination protection

- Severity: S0 (NN-7), isolated synthetic regression; no Owner data touched
- Milestone: M5
- Status: Repair in progress under the approved ISSUE-020 ownership decision

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
