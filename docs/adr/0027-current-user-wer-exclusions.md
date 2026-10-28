# 0027 - Current-user Windows crash-report exclusions

- Status: Accepted by PM
- Date: 2026-10-25

## Context and decision

Re-review N-1 identifies CRT abort/fail-fast reports not prevented by process
error modes or Job Object exception limits. N-5 invalidates the earlier
redirected per-user-store observation. PM approves Setup registering exactly
these executable names for the current user: dusty.exe, dusty-fetch.exe,
whisper-cli.exe, ffmpeg.exe and ffprobe.exe. No machine-wide exclusion is allowed.

Use WerAddExcludedApplication(name, False) before the model-free probe can run.
Fail Setup before continuing if registration fails. Review-only screenshot builds
never call the API. Normal pre-install cancellation removes only newly added
entries; an installed or failed self-test payload retains protection. After
uninstall's data helper exits and file removal completes, call
WerRemoveExcludedApplication(name, False) for exactly the same names. Do not
enumerate/delete unrelated entries. Report failed removal rather than claiming
it succeeded. Existing error-mode and Job Object mitigations remain.

## Verified API and consequences

[WerAddExcludedApplication](https://learn.microsoft.com/en-us/windows/win32/api/werapi/nf-werapi-weraddexcludedapplication)
and [WerRemoveExcludedApplication](https://learn.microsoft.com/en-us/windows/win32/api/werapi/nf-werapi-werremoveexcludedapplication),
reviewed 2026-10-25: False uses HKCU, True would use HKLM and is never passed.
The API is supplied by Windows Wer.dll on all supported Windows versions; no
new bundled binary or dependency. [MSVC abort](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/abort)
documents the non-debug CRT report-fault path.

These are per-account basename exclusions, so another copy/program with the same
name is also affected. They are not global diagnostic settings. A hard Setup
crash may leave entries; ordinary cancellation rolls back only new additions.
Administrative policies, custom dump collectors, OS/driver records and other
users are outside this guarantee. Privacy wording says Dusty asks Windows not to
create these reports and never sends reports itself. The source guard remains
defense in depth, not a sandbox (ADR 0017).

## Acceptance

Only disposable hosted CI may trigger deliberate crashes. Capture actual WER
roots before conftest redirects app data, restore real child profile environment,
compile a release-mode MSVC abort/SEH fixture in pytest's temp area, and exercise
all five registered names. Observe real per-user and machine queue/archive/temp
stores. Access errors fail the check, not turn a store into an empty set. Keep
explicit bounded-observation and unproven-path limitations in the report. Verify
installed entries, no HKLM changes, and exact uninstall removal while a separate
unrelated current-user fixture entry survives. No crash test on the maintainer's real WER stores.


The pinned Inno runtime is PE32 (the build gate verifies this). Its WER import
uses the absolute Windows {syswow64}/wer.dll with loadwithalteredsearchpath,
not a DLL beside Setup or in its launch folder. Windows supplies the DLL; none
is bundled. [Inno 6 DLL imports](https://jrsoftware.org/is6help/topic_scriptdll.htm)
confirm filename constants and the dependency-search flag (reviewed 2026-10-25).
