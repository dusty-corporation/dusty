# ISSUE-018 - Installer static subcomponent license review

- Severity: S1
- Milestone: M5 installer prework
- Status: Open, Owner/PM morning review
- Environment: pinned Inno Setup 6.7.3 source and compiler

## Expected

Every redistributed installer component has an approved, correctly identified
license. ADR 0023 approves InnoSetup for the wrapper only.

## Actual and root cause

The wrapper license says "Except where otherwise noted". Reviewing Setup.dpr,
SetupLdr.dpr and their linked source units identifies additional static code:
RemObjects Pascal Script has an attribution clause; LZMA SDK 25.01 and hash
utilities are public-domain code (the current policy permits public-domain data
only); the old LZMA loader has LGPL/CPL terms with a linking exception; JEDI
theme declarations offer MPL-1.1 or LGPL terms. The pinned compiler is built with
Delphi RTL/VCL, whose redistribution basis is not established by our source
inventory. These cannot be relabeled InnoSetup by the engineer.

The previous gate covered the wrapper and app payload, not these static units.
No installer binary is uploaded while these findings remain. This is a policy
review before distribution, not an observed unapproved shipment.

## Evidence

packaging/licenses/inno/components.json records exact pinned source URLs,
source hashes and retained notices. CI extends the actual app file inventory and
CycloneDX SBOM with these components. The dedicated license gate rejects each
unapproved identifier and the unresolved Delphi provenance.

Compression=lzma2 includes the LZMA decoder; zlib/bzip decompressor DLLs are
selected only for their respective compression methods in Compiler.SetupCompiler.
No external SevenZipLibrary is selected. The statically linked 7z C decoder is
part of the recorded public-domain LZMA SDK, not the optional 7-Zip DLL.

## Decision needed

PM reviews narrow installer-static exceptions and Delphi runtime provenance,
or chooses another installer architecture. Do not widen the app allowlist.
Keep unsigned installer binary artifacts blocked until this review is resolved.

## Regression

Installer inventory comparison, pinned notice hashes and exact contextual license
checks fail closed. Static inventory limitations are explicit in the audit output.
