# ISSUE-017 - Inno Setup installer license policy

- Severity: S1
- Milestone: M5 installer prework
- Status: Resolved by PM, 2026-10-23
- Environment: pinned Inno Setup 6.7.3, Windows CI, unsigned installer draft

## Expected

Every redistributed installer component has an explicitly allowed license.

## Actual

ADR 0008 accepts Inno Setup 6, but SPEC 10.2 and check_licenses.py do not include
its distinct SPDX identifier InnoSetup. It is not BSD-3-Clause or Zlib and must
not be relabeled as either. No exception has been added by the engineer.

## Evidence

- [SPDX InnoSetup license](https://spdx.org/licenses/InnoSetup.html).
- [Pinned source terms](https://github.com/jrsoftware/issrc/blob/is-6_7_3/license.txt),
  source commit c7af86b4b2fd03371185df2b09a1dca8d472ab70.
- Original source bytes SHA-256
  2e5346868c2a18434489824e11d65c3031620f792fefc415d05f19cd441abf5c;
  LF repository copy 3df23505b7ec00dc007a1e1e9ba32ee3895e7ce90043bcd1ac1b9b47155921a7.
- Full text permits use and redistribution, including commercial applications,
  subject to retained notices and origin/modified-version conditions. The
  compiler's non-commercial banner does not replace that verified source text;
  the bootstrap also checks installed/source license identity.
- Cancelled only our run 39914802080 before its installer upload step; no run
  was deleted. Earlier draft runs failed before producing an installer. New
  CI retains audit metadata only while this license is outside the allowlist.

## Root cause

Installer tool selection in ADR 0008 did not enumerate the license identifier.
The app-bundle inventory does not contain the Inno wrapper because it is created
after the PyInstaller bundle. Installer prework exposed this additional boundary.

## Proposed resolution

PM approves a narrow InnoSetup exception for the pinned Inno installer runtime
under proposed ADR 0023, with full notices and source provenance. Keep binary
upload/publication blocked until approval and completion of installer-wide
component inventory. Alternative: PM chooses another installer architecture,
which would replace ADR 0008. Recommendation: the narrow exception.

## Regression

Resolution: PM accepted ADR 0023, permitting exactly InnoSetup for the installer
wrapper with retained notices and the revenue-threshold purchase commitment.
The explicit installer context is required; app dependencies still reject it.
Updated regression asserts both the narrow approval and the denied contexts.

Historical finding before approval:

The installer policy check uses the same allowed_license function as the app
gate; it rejects InnoSetup today. The dedicated negative test prevents the
compiler wrapper from being silently treated as an allowed app component.
