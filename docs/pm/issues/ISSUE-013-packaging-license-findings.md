# ISSUE-013 - Packaging audit has unapproved and unresolved native licenses

- Severity: S1
- Milestone: M5 packaging spike
- Status: Resolved
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

PM decision, 2026-10-22: narrow required Visual C++ runtime exception (ADR 0020),
exclude Windows UCRT/API-set runtime DLLs and Mesa, include libffi's MIT notice,
and remove runtime lxml (ADR 0019). These approved changes are pending the
explicit required-platform PE-import stop in ISSUE-015. No clearance is claimed.

The initial spike listed findings without changing binaries, dependencies or
license policy. The approved changes above must be implemented and verified
before any distributable bundle or license-clearance claim.

## Regression test added

Bundle tests reject unknown licenses, static LGPL, unmapped files, inventory
hash mismatch and file additions/removals. Existing bootloader exception remains
exactly scoped to ADR 0014. No new allowlist exception is granted.

## Resolution, 2026-10-22

Earlier proposed fixes and pending statements above describe the initial stop.

The PM-approved removals and narrow exceptions are implemented. Runtime
python-docx/lxml, Mesa, UCRT and API-set DLL copies are absent; libffi MIT,
Qt LGPL/GPL reference, FFmpeg LGPL and downloader-only OpenSSL Apache notices
are retained. ADR 0020 uses the Owner's Community section 4 basis and the three
unchanged PDFs, protective EULA and exact Owner CRT hashes. ADR 0021 separately
pins only the two required platform primitive import sets. The former generic
native-review placeholder was a scope warning, not an identified component;
real unknown file providers still fail the gate and its negative tests.

Run 39884809028, packaging-spike job 120190381823: bundle license gate passed;
205 actual files, 12 provider components, schema-valid CycloneDX 1.6, all file
hashes and provider mappings covered. Full source notices and CRT import/source
receipts accompany the audit artifact. No new unapproved license remains at
this component/provider inventory scope. This is a draft SBOM, not a claim to
reverse-engineer every source unit statically linked inside upstream libraries.
