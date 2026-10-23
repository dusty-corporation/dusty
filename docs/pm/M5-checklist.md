# M5 installer and release checklist

This remains an acceptance checklist. An unsigned installer draft compiles in CI;
ISSUE-017 blocks binary upload pending explicit InnoSetup policy clearance.
Audit metadata is available; this is not a published or accepted installer.

- [ ] Verify every Microsoft PE is a required vcruntime140*.dll/msvcp140*.dll
  copied unmodified from VS 2022 VC/redist release x64 Microsoft.VC143.CRT;
  record source and bundle SHA-256 identity against packaging/microsoft-runtime.json
  (MSVC/14.44.35112 regular x64, not v143 alias or spectre). Confirm each CRT
  filename has a normal/delay PE importer. Exclude debug_nonredist, onecore,
  UCRT/API-set DLLs and all other Microsoft binaries.
- [ ] The installer license page must present Dusty's Apache-2.0 LICENSE and
  NOTICE alongside the Visual C++ runtime end-user EULA (Cpp_2015-2022_ENU.1033)
  and require agreement before installation. This implements Community 2022
  section 4.b's protective-terms requirement under the Owner's decision.
- [ ] Include all three unchanged Microsoft source PDFs, provenance hashes,
  complete runtime EULA text and third-party notices in the installed app.
- [ ] Keep Microsoft's terms scoped to its Distributable Code; preserve Qt/LGPL
  replacement and reverse-engineering rights for the LGPL components.
- [ ] Verify installer download/hash failure and self-test failure cannot show
  success; run installed-app PE, license and calibrated WFP gates.
- [ ] Complete the remaining full M5 tasks and Owner fresh-machine walkthrough
  under the future M5 brief; this spike does not satisfy installer acceptance.
- [ ] Confirm standard-user install needs no UAC, license acceptance precedes
  downloads, and graphics/RAM defaults are conservative on both target machines.
- [ ] Cancel and terminate Setup during download, confirm no downloader survives,
  rerun to resume; force network/hash/self-test failures and verify retry and a
  nonzero incomplete exit. Never show a success page after failure.
- [ ] Upgrade retains verified models without HTTP; uninstall with each checkbox
  choice preserves all transcript/output folders, including unusual internal paths.
- [ ] Finish installer-wide SBOM, installed-app WFP audit and draft-only release
  automation after fresh-machine evidence. The current CI job uploads only an artifact.
