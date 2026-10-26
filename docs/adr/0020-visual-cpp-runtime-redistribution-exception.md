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
Use the Owner's exact regular release CRT files installed with Community 17.14
on 2026-10-22. CI copies must match the Owner's pinned hashes and versions,
not merely another VS release's filenames. Do not select the v143 alias or
spectre directory. No other Microsoft binary is covered. Do not bundle
UCRT or api-ms-win-* files supplied by Windows 10+.

Under the Owner's decision, the runtime EULA is the protective end-user terms
for section 4.b. Include its complete text/PDF in THIRD_PARTY_NOTICES and the
installed licenses. The future M5 installer must present it alongside Dusty's
Apache-2.0 license and require agreement, as required by the installer acceptance gates.
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

## Pinned required runtime files

Owner source: `C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Redist\MSVC\14.44.35112\x64\Microsoft.VC143.CRT`.

All five filenames are imported by the bundled PEs (normal and delay imports).
The offline Qt runtime needs all five; the downloader needs only vcruntime140.dll.
Loader-local duplicate copies retain the same bytes. No other CRT filename is staged.
`crt-provenance.json` records every location, importing PE, and the collected
copy hash/version before replacement. Staging and the license gate reject a
missing importer or a changed Owner pin.

| DLL | File version | Owner SHA-256 |
|---|---|---|
| msvcp140.dll | 14.44.35211.0 | 0f885b509a685d2bbfa652fed26b5fb31d88fbdab0a978c641d1c7b8aa460aa9 |
| msvcp140_1.dll | 14.44.35211.0 | bfad5aef4c63a669e3c140655cdfdf395b6c979b400a447bd5dcb65ed8826c3d |
| msvcp140_2.dll | 14.44.35211.0 | 3ea06f0ee098b4823cb79599df3780e7f23cce52c19aac31d2a0d47efe33a5e9 |
| vcruntime140.dll | 14.44.35211.0 | d5e4d9a3e835fa679450145d6a7d94e36573a509317111904d9b3712c30d9066 |
| vcruntime140_1.dll | 14.44.35211.0 | 1f2d41c4aa5db0bc33ebf7b66d72943a817d7ce6cbe880502a9403823633093f |

The previously collected CI spectre files had the same version but different
hashes. They are replaced with the regular Owner-pinned copies; compatibility
is verified by the packaged GUI smoke test and calibrated WFP self-test.
