# ISSUE-025 - Registered installer payload bypassed destination protection

- Severity: S0 / NN-7, isolated regression; no Owner profile touched
- Milestone: M5
- Status: Resolved; source and native protection gates passed

## Root cause

The app-data helper protected only its own root. A saved or preserved output
inside the installation folder did not retain its protection metadata. Inno
would then independently remove registered files, even if a registered filename
had been replaced by a user transcript. An isolated metadata-retention regression
failed. Previous .11/.12 gates did not cover Inno's registered-file boundary.

## Repair and evidence required

The approved PM policy already requires preserving every legacy managed
destination, including installation folders. A read-only guarded preflight now
runs in InitializeUninstall before the silent branch, size calculation, dialog,
app-data deletion or registered-file removal. Protected or uncertain metadata
stops uninstall with a plain shared message. No new exception or policy decision.

The installed CI replaces resources/models.json with synthetic transcript bytes,
records its folder as protected, and requires native uninstall exit 1 with the
app, metadata and bytes intact. It then restores the exact original manifest
and continues ordinary payload/PE/WFP/uninstall gates. Release staging requires
protected_install_destination=passed and rejects a false/missing receipt.

.11/.12 remain draft and superseded as final candidates. A new repaired .13/.14
pair follows all gates. No release/tag/run/branch is deleted or published.

## Resolution, 2026-10-24

Commit 7f7e036 / v0.5.0-m5.13 / CI 40104236818 passed every job,
including the actual native uninstaller invocation with expected exit 1.
The registered models.json replacement, app executable and protection metadata
survived unchanged; the original manifest was then restored before the ordinary
exact installed payload, PE, WFP and both uninstall gates passed.
protected_install_destination=passed is present in the acceptance receipt and
mandatory in release staging; a false/missing receipt fails the gate.
Source: 355 passed, 2 expected skips; separate network test 1 passed; required
coverage 94.7%. Draft only. The .13/.14 true-upgrade pair is the final handoff.
