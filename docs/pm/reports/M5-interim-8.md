# M5 interim 8 - S0 transcript preservation stop

## 1. Summary

Adversarial review confirmed ISSUE-020, an NN-7 data-loss path. A chosen
transcript folder under Dusty's work areas is recursively removed by startup
cleanup or an installer self-test. Three isolated synthetic regressions failed;
no Owner files or real recordings were used. M5 implementation is stopped under
AGENTS rule 2 and SPEC section 2, overriding the overnight autonomy instruction.

## Owner actions for the morning

1. Keep all M5 test releases draft and do not run the installer/VM checklist
   until the repair is approved. No release or artifact was deleted.
2. If any real recordings/transcripts were placed under Dusty's app-managed work
   folders, do not launch/update the app first. Back them up manually to an
   ordinary user folder before any further use. The agent has not inspected or
   modified the real profile and cannot claim whether it is affected.
3. PM: approve the repair scope below. Existing M4/main startup cleanup is also
   in scope for the safety repair, not only installer code.

## 2. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| NN-7 transcript preservation | Not met | Three enabled regressions fail by deleting repository-local synthetic sentinels. |
| Final M5 release/upgrade acceptance | Blocked | Current runs cancelled/requested cancelled; final receipt-based release not accepted. |
| Native page review | Delivered, scale gap remains | M5-interim-2.md; 21 PNGs + README on draft m5-screenshots. |
| Owner VM acceptance | Not run, blocked | M5-checklist.md must wait for S0 repair. |

## 3. What was built

Only incident regression tests and documentation at this stop. No safety fix was
implemented without the PM's response. M6 docs prework remains pushed but carries
the same underlying app code and is not release-ready.

## 4. Test results

`uv run pytest tests/unit/test_work_output_ownership.py -q --basetemp=build/issue020-repro`
returned **3 failed in 0.38 s**. Startup preservation fails for probe and selftest;
installer self-test preservation fails even on a synthetic unavailable model.
No native process or network access is needed for the reproduction.
Historical pre-S0 source/packaging PASS evidence remains factual but does not
supersede these new failures or establish milestone acceptance.

## 5. Deviations

Stopped the autonomous run because S0 handling is mandatory. Source of truth and
Owner brief were not edited. No PR, merge, published release or deletion.

## 6. Issues

| ID | Severity | Status | Summary |
|---|---|---|---|
| ISSUE-020 | S0 | Open | Named work-area ownership assumption can delete a saved transcript destination. |

## 7. Questions for the PM

Approve a focused safety repair across startup, probe, self-test and coordinator
cleanup. Recommend unique owned work directories, saved output/source protection,
conservative handling of uncertain content/metadata, and a plain rejection of
new destinations inside app-managed work areas. Existing internal destinations
must be preserved before any startup cleanup, never silently moved or deleted.
No new dependency is proposed. Keep the new regressions enabled and require all
source, packaged, installed WFP and uninstall gates again after repair.

## 8. Containment

Own active M5/M6 and tag runs were requested cancelled; IDs are in ISSUE-020.
Adding the failing preservation regressions prevents downstream packaging from
passing on this source branch. Existing drafts remain unpublished, unchanged;
Owner-only deletion/publication/settings actions were not taken.

## 9. Risks

This behavior predates M5 and can affect startup as well as installer self-test.
A high coverage percentage missed the ownership/destination interaction.
Standard output destinations outside app-managed areas were not shown affected;
that is not a guarantee for all paths or permission/reparse-point cases.

## 10. Effort notes

The isolated reproduction uses tiny public synthetic text under build/ only.
The uninstaller already has conservative internal-output protection, but the
startup/probe/self-test paths need the same ownership boundary. Continuing normal
M5 work before this decision would violate the S0 stop instruction.
