# M5 installer and release checklist

This remains an acceptance checklist. An unsigned installer draft compiles in CI;
ISSUE-017 is resolved by ADR 0023. ISSUE-018 blocks binary upload pending review
of separately licensed static subcomponents and Delphi provenance.
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

## Automated runner acceptance added overnight

tools/test_installer.ps1 runs only on a disposable GitHub runner, refuses any
pre-existing Dusty user data, and checks silent per-user install, Tiny/VAD download,
installed PE gate and calibrated WFP self-test, upgrade with the downloader
blocked and unchanged model hashes/mtimes, both model-retention uninstall choices,
and an unchanged transcript-folder sentinel. See the latest report for actual
outcomes; the existence of this harness is not a passing result.

Silent install requires /ACCEPTTERMS=yes /ALLOWDOWNLOAD=yes /MODELS=tiny in
addition to /VERYSILENT /SUPPRESSMSGBOXES /NORESTART. These flags explicitly accept
the complete bundled license page and GitHub download. Uninstall requires
/REMOVEMODELS=yes or /REMOVEMODELS=no. Missing consent fails closed. Inno's
PrivilegesRequired=lowest selects per-user mode even though /CURRENTUSER has no
effect unless an override is enabled. No administrative override is enabled.

## Owner actions for a clean Windows 11 VM

Use a fresh standard user, not the development account. Wait for ISSUE-018
clearance and a passing unsigned artifact before distributing the installer.

1. Verify the exact installer SHA-256 against its CI SHA256SUMS.txt. Review
   SmartScreen's More info / Run anyway; confirm no UAC elevation is requested.
2. Read the Apache LICENSE/NOTICE and Microsoft runtime EULA on the license page.
   Confirm declining stops installation before downloads. Check the full notices.
3. Review recommended model choices, sizes and voice detection. Install Tiny
   first. Confirm the download consent, self-test and Start Menu shortcut work.
4. Disconnect networking, reboot, then transcribe a folder and open Text/Word
   outputs. Test CPU and Auto on available hardware. Confirm no network is needed.
5. Interrupt and terminate Setup during a model download. Confirm its child
   downloader exits; rerun and confirm resume. Test offline download failure,
   a damaged model and self-test failure: no false success, clear retry path.
6. Upgrade an existing install. Confirm verified models are retained without
   redownloading and settings/outputs remain. Test both uninstaller checkbox
   choices, then reinstall. Confirm no app-owned leftovers except retained models
   or deliberately preserved unfamiliar content, and user outputs are untouched.

Send Windows version, account type, model/device, pass/fail per step and exact
visible errors. Do not send private audio, transcript text, paths or diagnostics
containing personal information. Installer interaction, SmartScreen, standard-user
behavior and real hardware remain manual gates; CI's elevated disposable runner
does not prove these.
