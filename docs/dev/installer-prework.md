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
No compiler or installer has been installed on the maintainer's computer.
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
  the conservative Small default. The maintainer hardware review must confirm the wording
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
the maintainer desktop. The installed-app WFP audit reuses its downloaded models.

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

## PM page review round (2026-10-24)

Verified against the pinned Inno Setup 6.7.3 source already retained for ADR 0023:

- Shared.ScriptFunc.pas exposes FileSize64(Name, var Size: Int64). Download progress
  polls the active manifest partial during transfer and the final file during
  checking. It adds completed model sizes, including voice detection. Setup never
  opens a socket and no Inno downloader API is used.
- Setup.WizardForm.pas GetPreviousPageID deliberately stops at wpInstalling.
  A separate, initially skipped post-copy model page lets Back revisit the same
  model controls before download. It cannot return through file copying. The
  page is skipped again after a valid selection; Back is disabled once started.
- Setup.WizardForm.pas calls the script NextButtonClick before finishing wpFinished.
  Only at that final, non-busy point does Setup clear its completed outer Job's
  kill-on-close limit. The requested postinstall GUI may then outlive Setup.
  All transfer/test children are stopped first; active download protection is
  unchanged. A failure disables auto-launch and explains Start menu use.
- The postinstall run entry uses runasoriginaluser, nowait and skipifsilent, with
  its checkbox checked by default. The desktop task is checked by default too.
- CreateCustomForm's size handling is in Setup.ScriptFunc.pas and
  Setup.SetupForm.pas InitializeFont. The compact uninstall form fixes client
  dimensions after creation, lays out controls inside them and makes Cancel the
  default button. Its size helper is UTF-8 decoded to preserve the shared
  nonbreaking space between values and decimal MB/GB units.
- Production text is generated from messages.py. Consent becomes a persistent
  download heading; Next starts the transfer and becomes Next after completion.
  Voice detection wording uses its catalog size. Success has singular/plural
  forms; failures never get the success message.
- Review-only Retry/processor/Finish-without handlers are no-ops. Their enabled
  appearance reflects the real failure page without permitting a transfer or
  settings change. Preview counters derive from the selected catalog totals;
  they are explicitly examples, not measurements or acceptance results.

The native window inspection and the fresh standard-user VM remain separate
from compiler/source checks. The VM must confirm Open Dusty now survives Setup
exit, Back changes models before download, and uninstall works at both scales.

### Post-copy normal cancellation

Pinned Setup.MainForm.Close handles only ssPreInstall and ssInstall, and native
button visibility disables Cancel after wpInstalling. Both post-copy model pages
therefore explicitly enable Cancel/Close and bind Cancel.OnClick and OnCloseQuery
to a shared stop routine. The previous handlers remain for all earlier pages.
The stop path uses Inno's ordinary Finish processing with every postinstall run
unchecked, never ExitProcess; custom exit code is 130. Failed defaults are cleared
before finishing. A CI-only explicit TESTCANCEL parameter is gated by silent mode
and GITHUB_ACTIONS=true; it stops only after real prefix bytes arrive, exercising
the same routine under calibrated WFP before retry/uninstall acceptance.

### Versioned own-license upgrade copies

The first true tagged upgrade (.4 to .8) exposed old version-named copies of
Dusty's LICENSE/NOTICE. The exact installed-file gate rejected them; it stays
unchanged. Inno's pinned PrepareToInstall event runs before copying files and
may return an error string to stop installation. It now invokes the guarded
extracted current app for a narrow migration. Only exact obsolete versioned
own-license pairs matching the new bundled bytes are removed. All old folders
are preflighted, hashes rechecked before unlink, reparse/protected/unknown or
changed contents preserved, and directories removed only when empty. A blocked
migration gives a shared plain message; models and transcripts are not targets.


## Unicode shortcut audit

The CI entry audit uses Windows Unicode IShellLinkW through IPersistFile.Load,
GetPath(SLGP_RAWPATH) and GetArguments. It never calls Resolve, launches a target
or saves a real installed link. WScript.Shell rejected an actual Unicode target
in a repository-local fixture and returned no owned entries in the runner.
Two Unicode native links and bare-route rejection are now tested through the
W interface. No new dependency or shipped component. The same required two app
shortcuts and approved uninstall arguments remain.

API references: [IShellLinkW](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nn-shobjidl_core-ishelllinkw),
[GetPath](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ishelllinkw-getpath),
[GetArguments](https://learn.microsoft.com/en-us/windows/win32/api/shobjidl_core/nf-shobjidl_core-ishelllinkw-getarguments).
The read buffer covers the Windows Unicode string limit; possible truncation
fails. Fixture writers exist only in tests and never alter real shortcuts.

## M7 model cards and optional download

The pinned Inno 6.7.3 script class registrations expose TSetupForm AutoScroll,
TPanel BevelKind, TNewCheckBox and TFont.Style. A child, borderless scrollable
form contains one bordered panel per catalog model. Its full-width checkbox
caption supplies the bold accessible name and size; description labels are
separate. The checking line is above the viewport and Skip for now is below it.
All rows are created before the model-free probe begins. Programmatic selection
uses SetModelChecked because VCL checkbox setters can emit OnClick; they must
not count as user choices or recursively clear the skip choice.

Skip for now sets FinishedWithout, not InstallationReady, and bypasses both the
download plan and download/test children. Existing models/settings are kept.
No new tested-default receipt is written. Silent CI exercises /SKIPMODELS=yes
and verifies no models/settings were created, the app was installed, and the
transcript sentinel survived uninstall. The normal path still includes voice
detection automatically, even though the app's Skip long silences default is off.

Both PyInstaller EXEs and the Inno installer carry real Windows version resources
from project metadata. CI checks numeric and display versions. Preparing 1.0.0
metadata creates no tag and publishes nothing.

The embedded form explicitly disables CenterOnShow. Inno's TSetupForm normally
centers itself when shown; using that default inside a page relocates the list
and pushes the controls below it outside the page. Native review metadata and
CI now require the checking line, list, skip choice, notices and checkboxes to
fit their containers. Monitor positioning for DPI review also disables wizard
centering, in review builds only. No system display settings are modified.

Model controls are laid out again when their notebook page becomes current,
using its final dimensions; initialization-time size is not assumed final.
Review metadata includes the relevant rectangles to diagnose a failed fit.
The pinned Setup manifest is system-DPI-aware (SetupLdrAndSetup.XPTheme-x86.manifest),
not per-monitor-aware. On the mixed 175%/150% development desktop, the review-only
thread opts into per-monitor V2 before creating the wizard. This produces a
real 144-DPI window without changing desktop settings or the production manifest.
Review-only spacing compensates for the original global font metrics after a
monitor move. See Microsoft's [SetThreadDpiAwarenessContext reference](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setthreaddpiawarenesscontext),
verified 2026-10-24: it changes the calling thread's default context, returns its
previous context and is supported from Windows 10 1607. No bitmap is resized.

The review hook snapshots bounds and scales fonts/controls through registered
properties once after a monitor move. The pinned compiler does not expose
ScaleBy, even though the generic Pascal Script class source lists it.
Setup.SetupForm.pas:460 documents its custom scaling and the wizard DFM sets
Scaled=False. A per-monitor context alone leaves the original font metrics, so
a window-DPI value is insufficient evidence. Captures require both the requested
window DPI and the expected 10-point font height (13 px at 96 DPI, 20 px at 144),
plus all rectangle-fit checks. Snapshot order avoids inherited-font and anchor double scaling.
This normalization is review-only; the production
installer uses the system DPI chosen at startup, as before.


## Audit self-test deadlines

Setup bounds each post-download child independently: Tiny 120 s, Small/Small
English 180 s, Turbo 300 s, Medium/unknown 360 s, plus 120 s for an explicitly
CPU-only attempt. A timeout terminates the Job Object and enters the existing
failed-test Retry/Finish without a model state, never the success state.
The model-free probe retains its separate 7 s parent deadline.


## Native helper-failure review capture

Pinned Inno 6.7.3 source 4adf37ed7f3fd2bd11c6836ba056e3de170fbabf confirms
Setup.ScriptFunc routes SuppressibleMsgBox through LoggedMsgBox in Setup.MainFunc,
then Shared.CommonFunc.Vcl's native MsgBox. The production failure and review
call one shared ShowUninstallHelperUnavailable procedure with identical wording,
icon and buttons. Review-only code captures only the active popup owned by its
own process, while the native modal message loop dispatches its existing timer.
It records the popup's actual GetDpiForWindow value and native client size. No
reconstruction, image scaling, installation, network or system-DPI change occurs.
The standard model-card font/bounds checks remain unchanged for those pages.


Silent failure verification (ISSUE-048): pinned Inno's post-install exception
handler logs a failed next-page transition and shows the wizard even when the
exception message is suppressed. Do not use RaiseException for this exit path.
The documented GetCustomSetupExitCode event is invoked after normal completion;
an explicit SilentFailed flag yields exit 10, skips the custom download page,
leaves success false, disables launch and retains failure wording. Interactive
retry/finish handling is unchanged. Real CI tests require exact codes and the
original 30-second outer bound. Source: pinned Setup.MainFunc.pas and
https://jrsoftware.org/ishelp/topic_scriptevents.htm#GetCustomSetupExitCode.
