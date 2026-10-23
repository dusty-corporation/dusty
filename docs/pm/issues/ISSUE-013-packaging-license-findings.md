# ISSUE-013 - Packaging audit has unapproved and unresolved native licenses

- Severity: S1
- Milestone: M5 packaging spike
- Status: Open
- Environment: Windows x64, Python 3.12.11, PyInstaller 6.16.0, Qt 6.9.2, engine-v2

## Steps to reproduce

Run the build/inventory/bundle-license commands in docs/dev/packaging-spike.md.

## Expected

Every redistributed component meets SPEC 10.2, with complete native notices.

## Actual

Local audit staging includes Microsoft runtime DLLs governed by non-allowlisted
terms. lxml wheel notices disclose LGPL iconv, with static linkage requiring
review under the current policy. Mesa/software OpenGL, libffi and other embedded
native attribution are unresolved. Collected lxml Schematron resources have
separate ISO/skeleton terms and transforms described as unlicensed in the wheel
notice. The bundle license gate correctly fails.
The bundle is not published or uploaded; CI uploads audit metadata only.

## Evidence

Actual-file SHA-256 inventory, validated CycloneDX SBOM, draft notices and license
findings are generated in build/packaging/audit; CI evidence is linked in the
M5 interim report. Original available copyright/license texts are preserved.

## Root cause

The earlier checker audited locked Python distribution licenses only. Native
dependencies inside Python, Qt and binary wheels were not inspected before
packaging. PyInstaller's native dependency collection exposes these components.
The spike adds an actual-file inventory and fail-closed bundled-content gate.

## Fix / proposed fix

PM decision required before any distributable bundle. Per spike instructions,
list findings without swapping binaries, dependencies or license policy. Complete
source-level linkage and copyright reconciliation before deciding an approach.

## Regression test added

Bundle tests reject unknown licenses, static LGPL, unmapped files, inventory
hash mismatch and file additions/removals. Existing bootloader exception remains
exactly scoped to ADR 0014. No new allowlist exception is granted.
