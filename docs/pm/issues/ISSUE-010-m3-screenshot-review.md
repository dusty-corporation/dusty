# ISSUE-010 - M3 screenshot review corrections

- Severity: S2
- Milestone: M3
- Status: Resolved
- Environment: PySide6 6.9.2, Windows, both themes

## Steps to reproduce

Select Turbo with Transcribe, inspect the original options and dialogs, then
review unchecked controls in dark appearance.

## Expected

Translation guidance appears only for an invalid selected Translate task.
Options is modal, status matches the active phase, and controls/dialogs follow
the PM's revised copy, contrast and action requirements.

## Actual

The translation warning depended on model capability alone. The first M3
implementation expanded options into the main layout, displayed idle overall
progress, and used the earlier dialog/copy design. Light borders and native
indicator styling did not give reliable control-boundary contrast.

## Root cause

The rules conflated capability with the selected task. Tests asserted that
warning during Transcribe instead of the correct behavior, and screenshots
were reviewed without numeric control contrast assertions. The PM identified
these gaps and supplied the revised interaction requirements before the
Owner walkthrough.

## Fix / proposed fix

Task-specific guidance; a modal Options dialog; only Text/Word on the main
screen; contextual move actions and shortcuts; one shared phase formatter;
named collisions/errors; collision radio buttons; nonzero summaries with
failure reasons and a primary output action; plain copy and measured borders.
All recording names remain UI-only and are never logged.

## Regression test added

GUI regressions exercise the modal without layout reflow, stored extra formats,
keyboard reorder, selected-task warning, phase consistency including zero
progress, named dialogs, radio selection, summary counts and primary action.
Theme tests verify painted borders for every app control class in both themes
and sRGB contrast above 3:1. Final local suite: 99 passed, strict coverage 93.4%. PR 39840103768 and push 39840090723 passed (98 passed, 1 unavailable-Vulkan skip); WFP gui passed with zero connections.

## Resolution

Closed after the PM corrections, visual review of the regenerated matrix and
successful final local/CI checks. The keyboard regression initially lacked
active-window focus in offscreen Qt; 3df3cae supplies that precondition and
retains the actual reorder assertion. No tests were disabled or weakened.
The new draft asset m3-screenshots-pm-review-2.zip contains 116 synthetic PNGs;
previous assets remain available. Owner desktop walkthrough is still pending.
