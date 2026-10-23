# 0020 - Visual C++ runtime redistribution exception

- Status: Accepted by PM
- Date: 2026-10-22

## Context

CPython's Windows distribution needs Microsoft Visual C++ runtime DLLs, whose
vendor redistribution terms are outside the general SPEC 10.2 license allowlist.
The packaging spike identified this as part of ISSUE-013.

## Decision

The Owner holds a licensed Visual Studio 2022 Community individual license
(section 1.a), confirmed by the Owner on 2026-10-22. The legal redistribution
basis is **Community license section 4.a.i**, together with the **Visual C++
Runtime Files** section of the redistribution list. This permits unmodified
files in [VisualStudioFolder]/VC/redist, excluding debug_nonredist and other
listed exceptions. The runtime end-user EULA alone does not grant redistribution.

The PM approves only required `vcruntime140*.dll` and `msvcp140*.dll`, app-locally.
Prefer the Owner's VC/redist; builds must record byte identity with release x64
VC/redist source files. CI may use its installed VS 2022 release VC/redist and
record that provenance. No other Microsoft binary is covered. Do not bundle
UCRT or api-ms-win-* files supplied by Windows 10+.

Under the Owner's decision, the runtime EULA is the protective end-user terms
for section 4.b. Include its complete text/PDF in THIRD_PARTY_NOTICES and the
installed licenses. The future M5 installer must present it alongside Dusty's
Apache-2.0 license and require agreement, as recorded in docs/pm/M5-checklist.md.
Keep these terms scoped to Microsoft's code, preserving LGPL rights elsewhere.

## Supplied evidence

Retrieved by the Owner on **2026-10-22**, moved unchanged into
packaging/licenses/microsoft. Full extracted text accompanies each original PDF.

| Document | Source | SHA-256 |
|---|---|---|
| runtime-eula.pdf, Cpp_2015-2022_ENU.1033 | https://visualstudio.microsoft.com/license-terms/vs2022-cruntime/ | 80234896ac3bbeadd05a4445ae38c8018d400fe50bf55cf40164b04cb5fd78ec |
| community-2022.pdf, VS_Comm_2022_ENU.1033 | https://visualstudio.microsoft.com/license-terms/vs2022-ga-community/ | ec7bae304de6f0dd3d1513c924ca1f52b9eadb89a50e09d44d2fca4f702c1236 |
| redistribution-2022.pdf, Visual C++ Runtime Files, page 6 | https://aka.ms/vs/17/redistribution | f85d744f1188631c2039b826d3aeb0c168dbbd2cb65cc3cfc261393d6661fae3 |

## Consequences

The bundle checker verifies each CRT's permitted filename, release source path
and SHA-256 byte identity, records every Microsoft PE, and requires the notices
and evidence PDFs. Missing provenance, a changed copy, an unknown Microsoft PE
or missing protective terms fails. ADR 0021 separately resolves platform socket
primitive imports; it does not broaden this licensing exception.

Vendor redistribution reference:
https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files .

## Alternatives considered

Treat every Microsoft runtime as forbidden; the PM instead approved this narrow
exception. Bundling Windows UCRT/API-set runtime files was rejected.
