# 0023 - Inno Setup installer license

- Status: Proposed, PM decision needed
- Date: 2026-10-23

## Context

ADR 0008 selects Inno Setup 6. Its SPDX InnoSetup license permits redistribution
but is not present in SPEC 10.2's list. See ISSUE-017 and the pinned original
source/provenance in packaging/licenses/inno/.

## Proposed decision

Allow InnoSetup only for the Inno Setup 6.7.3 installer runtime, with the pinned
compiler bootstrap and exact license text. Retain the original copyright and
website notices, include the full license, and identify the upstream source.
Complete the installer-wide component inventory before binary distribution;
this proposal does not grant blanket approval to compiler-bundled third parties.

## Consequences

The installer license gate continues failing and binary uploads remain blocked
until the PM accepts this decision. The already audited app bundle is unaffected.

## Alternatives considered

Relabeling the license as BSD/Zlib would be incorrect. Replacing Inno Setup
would require a separate architecture decision and verification effort.
