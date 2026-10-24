# Current M5 page implementation (2026-10-23)

The historical spike notes below are superseded where they describe registry
GPU guessing, popup consent, first-model-only testing or outstanding license
clearance. Current controls are in installer/wizard.iss, included by the generator.
Catalog names, notes, Best for, consent and decimal sizes come from messages.py
and the Model Manager formatter. The complete license page includes all notices;
three buttons expose Apache/NOTICE, third-party notices and Microsoft terms.

Pinned Inno 6.7.3 interfaces verified from its source/help:
- TNewCheckListBox captions wrap with DT_WORDBREAK and explicit line breaks.
  ItemSubItem is a single-line right column, so it must not contain descriptions.
- CreateCallback/SetTimer keep operations asynchronous; no busy UI wait loop.
- CreateProcessW uses a 68-byte Win32 STARTUPINFO and four-DWORD PROCESS_INFORMATION.
  Children start suspended and join a nested kill-on-close Job Object before resume.
- Vulkan properties are read with the fixed Vulkan 1.0 prefix. Physical integrated
  and discrete types only; software implementations are rejected. The existing
  ggml C exports initialize and clear/synchronize 4 KiB without a model.
- The guarded Dusty probe child has a five-second deadline; Setup bounds its
  supervising process to seven seconds. Default Small remains usable throughout.
- LicenseMemo uses UTF8Decode for generated UTF-8 notices. An array expression
  must not start a script line: Inno's section scanner treats it as a section.
- ReviewOnly is a separate compile define, not a production command-line bypass.
  It disables installation and downloads, uses the real native page controls,
  and shows explicit synthetic progress/error/uninstall-size states for review.
  The review artifact upload is downstream of license and installed acceptance.

Full installer download-event attribution, clean-machine acceptance, final tags,
version mapping and release automation remain separate M5 work after page review.

---

# Installer prework (M5 draft only)

## Reproduce on disposable Windows CI

Build and audit the split bundle first, including inventory, licenses, PE pins,
GUI smoke, offline self-test and Model Manager download WFP gates. Then run:

```powershell
./tools/build_installer.ps1
```

The bootstrap refuses non-CI execution, downloads only the pinned official
Inno Setup 6.7.3 compiler installer and checks its SHA-256 before execution.
No compiler or installer has been installed on the Owner's computer.
The compilation output is unsigned. ISSUE-017 currently blocks the installer
binary artifact: InnoSetup is not in the redistribution allowlist. CI retains
only installer audit metadata until PM clearance, never an automatic release or tag.

Compiler pin: `packaging/licenses/inno/source.json`; official
[6.7.3 release](https://github.com/jrsoftware/issrc/releases/tag/is-6_7_3),
source commit c7af86b4b2fd03371185df2b09a1dca8d472ab70.
Major 6 remains the ADR 0008 choice; this prework does not upgrade to Inno 7.
The pinned source's ISCC.versionandicon.res has fixed version 0.0.0.0; ISCC is
a launcher. The actual engine version is checked against the compilation banner
(ISCC.dpr calls ISDllGetVersion and prints the engine title/version). Checking
the launcher's Windows FileVersion as 6.7.3 was incorrect and failed closed.
The unmodified Inno copyright and website notices are retained; its full license
is included in the installer terms and installed licenses folder.

## Verified interfaces and design

- [LicenseFile](https://jrsoftware.org/ishelp/topic_setup_licensefile.htm)
  accepts Unicode text. Generated terms include the full Apache LICENSE, NOTICE
  and full runtime EULA, with Microsoft's terms explicitly scoped to its code.
  Acceptance is required. The three original Microsoft PDFs remain in the bundle.
- [CreateInputOptionPage](https://jrsoftware.org/ishelp/topic_isxfunc_createinputoptionpage.htm)
  supplies the model checkboxes. Model IDs, names and sizes come from models.json;
  the manifest is not rewritten. UI wording comes from messages.py.
- [CreateCustomForm](https://jrsoftware.org/ishelp/topic_isxfunc_createcustomform.htm)
  requires width, height and both keep-size flags since Inno 6.6. The uninstall
  model-choice form uses that current constructor, not the old writable-size API.
- [Exec](https://jrsoftware.org/ishelp/topic_isxfunc_exec.htm) waits for an actual
  process exit code. The split dusty-fetch executable verifies before downloading,
  downloads/resumes through its existing allowlist and hashes, and verifies again.
  Voice detection is included. No Inno HTTP API is called (ADR 0022).
- The separate post-install download page cannot advance until every chosen
  model plus VAD verifies and dusty.exe --self-test succeeds. Failures stay on
  that page for retry; exit code 10 prevents an incomplete run reporting success.
  Silent installation does not bypass explicit network consent.
- The default model is Small unless at least 16 decimal GB RAM, a Vulkan loader
  and an enabled, existing registered ICD are found. Those conditions select
  Turbo as a candidate, not proof of a working backend. The real offline self-test
  performs the Vulkan probe; CPU fallback remains allowed. Unknown drivers use
  the conservative Small default. Owner hardware review must confirm the wording
  and behavior before M5 acceptance. `/MODELS=tiny` selects the small CI/smoke model;
  only IDs already in the catalog can be selected.
- Models live in the user's Dusty data folder, outside the install folder;
  verified upgrades skip HTTP requests. No [InstallDelete]/[UninstallDelete]
  wildcard ever targets app data or output directories.
- Uninstall asks whether to remove downloaded models (checked initially).
  The offline cleanup entry point deletes only recognized data and empty folders;
  unknown files, saved outputs and source recordings are preserved. Corrupt
  metadata, links/junctions or overlapping output paths fail closed with a message.
  Silent uninstall requires an explicit /REMOVEMODELS=yes or /REMOVEMODELS=no.

## Silent acceptance and inventory

The pinned ISHelp/isx.xml confirms NextButtonClick is called on silent installs,
but rejection automatically exits only before installation starts. Silent
post-install work therefore runs in CurStepChanged(ssPostInstall) and raises on
failure. /ACCEPTTERMS=yes and /ALLOWDOWNLOAD=yes are mandatory explicit consent;
/SUPPRESSMSGBOXES alone never approves either. Models still verify before reuse.

tools/test_installer.ps1 runs only in disposable CI, with no pre-existing user
data. Inno resolves {localappdata} through Windows known folders, not an environment
override. The harness checks both roots agree, uses a repository-local install
directory and checks real runner-user model/settings cleanup. It never runs on
the Owner desktop. The installed-app WFP audit reuses its downloaded models.

tools/inventory_installer.py extends the actual app inventory and validated
CycloneDX 1.6 SBOM with the wrapper and separately identified static components.
packaging/licenses/inno/components.json pins source hashes and retained notices.
This source-level attribution cannot prove the Delphi RTL/VCL binary's provenance;
ISSUE-018 records that limit and additional license findings. Installer artifacts
remain gated. Compression=lzma2 does not embed isunzlib/isbunzip DLLs; the pinned
Compiler.SetupCompiler.pas selects those only for zip/bzip compression. No optional
external 7-Zip library is selected. ISCC, ISPP and compression helpers are build-only.

## Child lifetime and outstanding acceptance

Setup joins a private, non-inheritable kill-on-close Job Object before starting
children. Win32 layout is pinned to Inno 6's PE32 Setup and asserted by the build
gate: extended-limit information 112 bytes, LimitFlags DWORD at offset 16, value
0x2000. These derive from Microsoft's
[basic](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information)
and [extended](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information)
records; [nested jobs](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs)
are supported on the Windows 10+ baseline. Confirmed cancellation during download
terminates this job; terminating Setup also closes its only handle. Atomic .part
handling keeps final model files valid; app files may remain for a retry.

Compilation and unit tests do not establish that a fresh-machine installation
works. M5 still requires the standard-user Windows 11 VM checklist: visible license
acceptance, driver/RAM defaults, actual cancel/resume and failure/retry, shortcuts,
upgrade reuse, both uninstall choices and installed-app WFP acceptance. The CI
artifact contains the existing app-bundle SBOM; a final installer-wide SBOM and
release workflow remain M5 release work, not completed acceptance in this draft.

- DialogFontSize belongs in [LangOptions], not [Setup], in pinned 6.7.3.
  Compiler source Shared.LangOptionsSectionDirectives.pas and the successful
  native build verify this; the generator regression checks section placement.
