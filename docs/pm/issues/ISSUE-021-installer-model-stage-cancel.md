# ISSUE-021 - Native Cancel ignored after app file installation

- Severity: S1
- Milestone: M5
- Status: In progress, fix implemented; native CI acceptance pending
- Environment: pinned Inno Setup 6.7.3, post-install custom model page

## Root cause

Inno's Setup.WizardForm.UpdateCurPageButtonState hides Cancel after wpInstalling.
Setup.MainForm.Close handles only ssPreInstall and ssInstall, so making the button
visible alone is insufficient. The original automated acceptance used silent
installation and never clicked the interactive post-copy Cancel/X controls.
Pinned-source inspection during the PM page round identified this before VM use.

## Fix

Explicitly enable Cancel and the Close system-menu item on both post-copy model
pages. Route button, Escape and window Close through one controlled stop routine.
It stops the child Job, removes only its active manifest partial, clears a failed
default selection when required, skips all postinstall launches and exits through
Inno's ordinary Finish/cleanup path with code 130. No ExitProcess shortcut and
no removal of verified or pre-existing models. Pre-install/review cancellation
continues through Inno's original handlers.

## Regression evidence

Generator invariants cover both callback bindings, visible Cancel/Close, normal
cleanup and disabled postinstall launch. A disposable-CI-only explicit silent
TESTCANCEL mode invokes the same stop routine after a real model prefix arrives.
Installer acceptance checks exit 130, no partial remains, any retained final
model verifies, WFP processing/Setup counts remain zero, retry succeeds and
uninstall leaves no owned data or changed transcript sentinel. Final release
staging requires its passing receipt. Actual button/X behavior remains in the
Owner's standard-user VM checklist; it is not claimed from synthetic screenshots.
