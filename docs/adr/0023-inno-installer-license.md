# 0023 - Inno Setup installer license

- Status: Accepted by PM
- Date: 2026-10-23

## Context

ADR 0008 selects Inno Setup 6. Its SPDX InnoSetup license permits redistribution
but is not present in SPEC 10.2's list. See ISSUE-017 and the pinned original
source/provenance in packaging/licenses/inno/.

## Decision

Allow InnoSetup only for the Inno Setup 6.7.3 installer runtime, with the pinned
compiler bootstrap and exact license text. Retain the original copyright and
website notices, include the full license, and identify the upstream source.
Complete the installer-wide component inventory before binary distribution;
this decision does not grant blanket approval to compiler-bundled third parties.

PM approved exactly SPDX InnoSetup for the installer wrapper only on 2026-10-23.
Since 6.5 the author requests a paid license from commercial users with annual
revenue over USD 5000, including donations. Dusty is free with no revenue, so
none is needed. If Dusty ever exceeds that threshold, the Owner buys a license.
Sources checked 2026-10-23: https://jrsoftware.org/isorder.php and
https://github.com/jrsoftware/issrc/blob/is-6_7_3/license.txt .
The upstream purchase page describes this as a request, not a strict condition
on redistribution. The purchase commitment above is the PM's project policy.

## Consequences

The exact wrapper exception is enabled only in the installer gate. The app gate
still rejects InnoSetup. All installer components need inventory, notices and
approved licenses before the unsigned CI artifact is uploaded.

## Alternatives considered

Relabeling the license as BSD/Zlib would be incorrect. Replacing Inno Setup
would require a separate architecture decision and verification effort.
