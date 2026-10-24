# ISSUE-021 - Native Cancel ignored after app file installation

- Severity: S1
- Milestone: M5
- Status: Resolved, automated native acceptance passed; actual controls remain VM acceptance
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

## Resolution (2026-10-24)

CI 40065869279 on 7b8d28b is fully green. Real-prefix normal stop exits 130,
removes the active partial, retries successfully and leaves output sentinel
unchanged through uninstall. Calibrated cancellation WFP: Setup 0, GUI 0,
native 0, fetch allowed 2, blocked 0. Complete-download WFP: 0/0/0, fetch 4/0.
Packaged/installed PE, license, GUI and WFP gates and both uninstall variants pass.
The first compiler attempt 40064929172 failed an unnecessary saved-event
Assigned check; pinned WizardForm has no original OnCloseQuery handler, so the
check was removed, preserving native OnClose outside the custom model pages.
