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
The output is an unsigned CI artifact, never an automatic release or tag.

Compiler pin: `packaging/licenses/inno/source.json`; official
[6.7.3 release](https://github.com/jrsoftware/issrc/releases/tag/is-6_7_3),
source commit c7af86b4b2fd03371185df2b09a1dca8d472ab70.
Major 6 remains the ADR 0008 choice; this prework does not upgrade to Inno 7.
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
  Silent uninstall is deliberately refused until it can express the same choice.

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
