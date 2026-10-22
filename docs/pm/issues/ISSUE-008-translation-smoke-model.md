# ISSUE-008 - Small is unreliable for the Persian poetry smoke fixture

- Severity: S1
- Milestone: M2
- Status: Resolved
- Environment: Windows hosted CI, engine-v2, Small, four CPU threads, VAD on

## Steps to reproduce

Run the Persian translation regression using Small on Windows CI.

## Expected

The public-domain Persian quatrain translates to English and preserves the
independently published source keyword. Acceptance must hold across runners.

## Actual

Local checks and PR run 39812231667 passed, but push run 39812242326 and PR
run 39812641455 failed the unchanged reference-keyword assertion. WFP passed.
No transcript output is retained in this issue.

## Root cause

The fixture test selected Small based on a successful local translation of
a short, difficult poetic passage. That did not establish adequate translation
margin across hosted runners. The pinned CLI enables temperature fallback in
0.2 increments and initializes sampling with seed 0; the exact numerical or
fallback difference between hosts has not been isolated. There is no evidence
of an engine flag, model hash, or translation-task wiring error. The initial
local-only acceptance missed this model/fixture sensitivity.

## Fix / proposed fix

Use Medium, already approved and explicitly recommended for Translate by
ADR 0016. Fetch it from the unchanged hash-pinned models-v1 release. Retain
the original keyword assertion and additionally require another independently
published source concept. Do not change decoding settings, skip the test,
retry failures into success, or reduce the assertion. Verify locally and on CI.

## Regression test added

`tests/integration/test_translation.py` retains Persian-script Transcribe and
English-script Translate controls with source-content checks. Both final
engine-v2 runs passed: PR 39813686035 and push 39813676982. Each passed all
checks and WFP; PR test results were 75 passed with one unavailable-Vulkan
hardware skip. The complete local suite passed 76 tests with actual Vulkan.

## Resolution

Medium is the translation acceptance model, as already recommended by the PM
in ADR 0016. The original independent keyword assertion remains mandatory,
and the additional source-content assertion passed on both hosted runs.
This resolves fixture acceptance; it does not claim to fix Small's literary
translation accuracy or prove which numerical difference caused its failure.
