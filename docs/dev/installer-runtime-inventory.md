# Pinned installer runtime inventory

Inno Setup 6.7.3, commit 4adf37ed7f3fd2bd11c6836ba056e3de170fbabf.
This is an inventory of the upstream compiled setup runtime, not of every tool
in the Inno compiler installation. ADR 0023 records PM approval and scope.

Tag is-6_7_3 is annotated: its tag-object ID is
c7af86b4b2fd03371185df2b09a1dca8d472ab70, while its peeled commit is the
4adf37ed7f3fd2bd11c6836ba056e3de170fbabf above. GitHub raw-file URLs require
the commit, not the tag-object ID. Earlier records calling c7af86b a commit
were incorrect. Both identities are retained in the provenance JSON; every
reviewed source hash matches the peeled commit. No version or binary changed.

## Selected runtime and build evidence

- `Compiler.SetupCompiler.pas` initializes `WizardDarkStyle=wdsLight` and
  `UseSetupLdr=sl32bit`. Our script explicitly uses `WizardStyle=modern light`,
  supplies no custom style and does not change the loader setting.
- `PrepareSetupMemoryFile` chooses `Setup.e32` for light/no-style; other style
  cases choose `SetupCustomStyle.e32`. The actual compiler log must contain
  `Updating icons (Setup.e32)` and must not select SetupCustomStyle. The final
  installer PE32 check also remains in place.
- `Setup.dproj` builds Setup.dpr as Win32 Release. The setup includes ScriptRunner,
  ScriptClasses and both JEDI units explicitly. Its Release target has code
  support; compiling our Pascal script also exercises that support. The distinct
  NOCODE configuration is not our target.
- Upstream compile.bat/README identify the release build and Delphi 12.3 Athens
  with May Patch. We do not rebuild the upstream runtime. Pinned compiler-bootstrap
  SHA-256 establishes the distribution used. runtime-inputs.json records the
  original Setup.e32/SetupLdr.e32 hashes, source commit and source-review hash.
- runtime-source.json pins each reviewed source file. Build downloads those exact
  commit-addressed files and rejects changed bytes. Component records identify
  direct verified unit references; the Delphi group includes their RTL/VCL
  dependencies. This is source/build verification, not a recovered linker map or
  a claim to enumerate every compiler-generated routine.

## Components actually included

| Component | Verified units / objects and reference |
|---|---|
| Inno runtime | Setup.dpr and SetupLdr.dpr, including upstream uninstall/helper support |
| Pascal Script | ScriptRunner: uPSRuntime, uPSDebugger, uPSUtils, uPSR_dll. ScriptClasses: uPSR_std, uPSR_classes, uPSR_graphics, uPSR_controls, uPSR_forms, uPSR_stdctrls, uPSR_extctrls, uPSR_comobj |
| LZMA / 7z C SDK 25.01 | ISLzmaDec-x86.obj and IS7zDec-x86.obj linked by Compression.LZMADecompressor and Compression.SevenZipDecoder |
| Small LZMA loader | LzmaDecodeInno-x86.obj from Compression.LZMA1SmallDecompressor; historical 4.40/4.43 source |
| Hash wrappers | MD5, SHA1, SHA256; original public-domain wrappers now delegate to System.Hash |
| JEDI | NewUxTheme.pas and NewUxTheme.TmSchema.pas, both direct Setup.dpr references; FolderTreeView calls NewUxTheme APIs |
| Delphi runtime | Direct Forms/Vcl.Forms, Windows/Winapi.Windows, SysUtils/System.SysUtils, Messages/Winapi.Messages and transitive RTL/VCL dependencies of setup |

Both JEDI units are exactly the versions distributed by Inno. Their headers note
upstream simplification; Dusty makes no additional modifications. Source links
in components.json point to these exact upstream versions. The installer includes
installer-jedi-source.zip with original bytes and full MPL/notices, and a separate
installer-THIRD_PARTY_NOTICES.md with every component's notice and acknowledgement.

The LZMA author now places original SDK code in the public domain. We retain the
old loader's LGPL/CPL exception header as provenance and record PM's decision that
the later public-domain grant makes that exception moot. It is not relabeled as
MIT or LGPL-dynamic code. Pascal Script retains its exact BSD-style notice rather
than pretending it is the standard BSD-3-Clause text.

Delphi compiled redistributables remain within the upstream application and its
own copyright notices. No compiler, SDK, database driver, BPL or additional Delphi
DLL is shipped. The PM-approved basis is the Inno authors' compiled-application
redistribution; the official deployment and section 2.2 reference links are in
delphi-runtime.txt. Dusty does not claim access to the authors' individual license.

## Excluded from the shipped wrapper

SetupCustomStyle.e32 and its VCL style packs; SetupLdr.e64; ISCC/ISCmplr/ISPP;
islzma compressor helpers; optional external 7-Zip DLL. The compiler source embeds
isunzlib/isbunzip only for zip/bzip compression, while our script uses lzma2.
The built-in 7z C object above is distinct from the optional 7-Zip DLL.

## Upload regression

The production installer upload explicitly requires `success()`, successful
installer-license outcome and successful installed acceptance. Packaging waits
for source checks, offline acceptance and installer-upload-regression. That
negative CI job deliberately fails a synthetic gate and asserts the identically
conditioned upload step is skipped. A unit test ties the two expressions and
job dependencies together. Production gates have no continue-on-error behavior.
