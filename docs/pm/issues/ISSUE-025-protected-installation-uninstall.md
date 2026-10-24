# ISSUE-025 - Registered installer payload bypassed destination protection

- Severity: S0 / NN-7, isolated regression; no Owner profile touched
- Milestone: M5
- Status: Repair implemented under existing ownership policy; native gates pending

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
