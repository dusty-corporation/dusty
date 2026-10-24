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

## PM amendment: unmodified compiled runtime, 2026-10-23

Accepted by PM for ISSUE-018. The exception covers only components compiled
into Inno Setup's unmodified upstream setup runtime. It is not permission to
bundle these components independently, rebuild them differently, or add them to
Dusty's processing app or downloader. The app allowlist is unchanged.

| Runtime component | Terms and retained material |
|---|---|
| RemObjects Pascal Script | Its original BSD-style attribution license, retained verbatim; visible acknowledgement and project URL in installer notices |
| LZMA SDK and size-optimized loader | Igor Pavlov's public-domain grant; retain historical headers, with the old linking exception moot under the later grant |
| Public-domain hash wrappers | MD5, SHA1, SHA256 units in the same upstream runtime; retain original public-domain notices |
| JEDI theme units | Exactly NewUxTheme and NewUxTheme.TmSchema, under MPL-1.1; original notices, full MPL, pinned upstream links and exact unmodified source archive distributed with the installer |
| Delphi RTL/VCL | Embarcadero compiled-application redistribution terms, as exercised by the Inno authors; compiled into their runtime, not standalone compiler/SDK/runtime packages |

Verification: pinned commit 4adf37ed7f3fd2bd11c6836ba056e3de170fbabf,
Setup.dpr/Setup.dproj, SetupLdr.dpr, Setup.ScriptRunner/Setup.ScriptClasses and
the compression units. The upstream README identifies Delphi 12.3 Athens with
the May Patch. Default light style and no external style select Setup.e32;
the 32-bit loader selects SetupLdr.e32. CI checks that selection, records hashes
of those upstream runtime inputs and verifies reviewed source hashes. Normal
Inno icon/version-resource configuration is allowed; no runtime-code patching.
See docs/dev/installer-runtime-inventory.md for exact units, proof and limits.

No SetupCustomStyle runtime, VCL style packs, IDE/compiler, optional external
7-Zip DLL, zlib/bzip decompressor DLL or separate Delphi package is included by
this exception. Compiler-only tools may exist in CI and are not distributed.

MPL source is included on the same media, with exact upstream bytes and its
full license. Separate app/Microsoft terms do not restrict rights in that source.
The runtime is used as received from the pinned Inno distribution; the Owner
does not need a Delphi development license to run Inno's distributed compiler.
Rebuilding Inno itself is outside this approval.

Primary references checked 2026-10-23:

- https://github.com/jrsoftware/issrc/tree/is-6_7_3
- https://www.7-zip.org/sdk.html (public-domain grant)
- https://www.mozilla.org/en-US/MPL/1.1/ (sections 3.2, 3.5, 3.6)
- https://docwiki.embarcadero.com/RADStudio/Athens/en/Deploying_Applications_Overview
- https://github.com/Embarcadero/pa-radserver-docker/blob/7d666264ae4e9e8426f9562c0f45f867a14e7dc3/LICENSE.md (section 2.2, official reference for compiled redistribution; not a claim that Dusty owns a Delphi license)

The installer gate checks the exact component/license pairs and retained notices.
It must pass before unsigned CI artifact upload. No release publication is
authorized by this ADR. If terms prohibit this use or cannot be met, stop.
