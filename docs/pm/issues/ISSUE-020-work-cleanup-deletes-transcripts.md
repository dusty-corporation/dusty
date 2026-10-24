# ISSUE-020 - Work cleanup deletes a chosen transcript destination

- Severity: S0 (SPEC NN-7)
- Milestone: M5 self-review; underlying cleanup predates M5
- Status: Resolved (2026-10-24), PM-approved ownership repair verified
- Environment: Windows desktop, Python 3.12.11, m5-installer at 078b262

## Steps to reproduce

Repository-local synthetic data only, no Owner files or native processes:

`uv run pytest tests/unit/test_work_output_ownership.py -q --basetemp=build/issue020-repro`

The test creates a saved transcript destination under a named work area, records
it in schema-1 settings, writes a public synthetic sentinel, then invokes the
same startup cleanup or installer self-test routine used by the app.

## Expected

A user-chosen transcript destination and its files survive startup, model probes
and installer self-tests. Uncertain ownership must preserve data, not delete it.

## Actual

All three regressions fail: startup deletes both named work-area destinations;
the installer self-test deletes the selected self-test destination even when
model initialization fails before any native process launches. No warning or
user choice authorizes that transcript deletion. No real Owner data was used,
read or changed; this is a confirmed isolated reproduction, not a report of
observed production loss.

## Evidence

- 3 failed in 0.38 s. Assertions: `Startup deleted a file in the chosen transcript
  destination` and `Installer self-test deleted a chosen transcript destination`.
- `src/dusty/app/window.py:929` accepts any chosen output folder.
- `src/dusty/app/workers.py:44` invokes startup orphan cleanup unconditionally.
- `src/dusty/queue/coordinator.py:32` treats probe/selftest/UUID directory names as
  ownership evidence and recursively deletes the directory, without consulting
  saved output/source locations or unknown contents.
- `src/dusty/selftest.py:16` reuses a fixed work directory; line 70 recursively
  removes it in finally. `src/dusty/engine/backend.py` has the same named-area
  pattern and needs inclusion in the repair review.
- The existing uninstall regression already treats an internal saved output
  folder as protected. That protection does not cover these other cleanup paths.

## Root cause

Cleanup equates a reserved directory name with exclusive app ownership, while
folder selection and persisted settings allow a user destination there. Startup,
probe and self-test paths do not share the uninstaller's conservative ownership
and saved-path protections. Previous tests checked cleanup of app-owned fixtures,
but did not combine a saved internal output destination with startup/self-test.
M5's automatic installer tests increase exposure to this pre-existing assumption.

## Proposed fix, PM approval required by the S0 stop rule

Use unique owned per-invocation work areas, protect saved output and source paths
before all cleanup, and preserve uncertain/unknown content and corrupt ownership
metadata. Reject new destinations inside app-managed work areas with a plain
explanation, while preserving already-saved internal destinations before startup.
Review every recursive cleanup site, not only the two demonstrated cases. Do not
silently move or delete existing user files. No new dependency appears necessary.

## Regression tests added

- test_startup_cleanup_preserves_saved_transcript_folder[probe]
- test_startup_cleanup_preserves_saved_transcript_folder[selftest]
- test_installer_selftest_preserves_saved_transcript_folder

All remain enabled and failing. They block source CI and downstream packaging
until repaired. Further acceptance must cover UUID work areas, saved sources,
unknown contents, corrupt metadata and both uninstall choices.

## Containment

Stopped milestone implementation under AGENTS rule 2 / SPEC NN-7. Requested
cancellation of own active runs 40043241355, 40042984627, 40042648483,
40042645271 and 40042365579. No run, tag, branch, artifact or release was deleted.
Existing M5 drafts must remain unpublished and unused pending repair. The main
M4 cleanup path also needs review. Owner profile and output folders were untouched.

## PM repair decision (2026-10-23)

Approved: Dusty deletes only content it can prove it created. Unique random work,
probe and self-test folders require purpose/inventory markers. Preserve unknown,
changed, unmarked or linked content, with redacted skip logs. Reject sources and
outputs inside managed areas, preserve legacy destinations and clear their saved
selection with a one-time explanation. Cover startup, jobs, probes, self-tests and
uninstall, then source/package/installed WFP/uninstall gates. Repair is in progress;
this issue remains open until the gates pass.

## Resolution evidence

Final repair 1b62946 passed CI 40061186069: source 293 passed/2 expected skips
plus the separate real-network test; measured coverage 94.2%. Packaged PE,
license, GUI, WFP, installed WFP, same-version upgrade preservation and both
uninstall choices pass. Setup/GUI/native connection counts are 0; fetch has
4 allowed/0 blocked events, calibrated. Source/implementation parity with
m6-docs-v2 8c199b0 verified. See M5-interim-9.md for the complete delete sweep.
The three original regressions, junction/symlink tests, unknown-content tests,
and marker-loss/change continuity regressions are enabled. No Owner data touched.
Two-version release acceptance and fresh VM testing remain separate M5 tasks.
