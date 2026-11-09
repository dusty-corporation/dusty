# Building a release from public source

The public repository contains one source snapshot commit per release. Its own
release.yml invokes the complete ci.yml source, offline, bundle, installer,
license and installed acceptance gates. Private development history is not a
release input. Native and model assets are pinned by hash, not branch names.
Only the maintainer publishes; workflows create drafts and never publish.

## Release policy

For v1.0.0, fresh install and same-version reinstall must reuse verified models
with the downloader blocked during reinstall. Both uninstall choices must
preserve user outputs. Calibrated source, packaged and installed WFP tests must
show zero processing connections, including the model-free graphics probe.
The allowed separate downloader must complete a real hash-verified download.
The earlier distinct-version upgrade test is retained in the private archive;
it is not presented as a public release dependency.

Starting with v1.0.1, acceptance downloads the preceding published public release,
checks its installer against its SHA256SUMS.txt, requires increasing versions,
and proves true upgrade with models preserved and the downloader blocked.
A missing prior release or receipt fails staging. Drafts never satisfy the
previous-public-release rule. Do not replace old release assets.

Starting with v1.1.0, a public release ships Windows and Mac together from the
same snapshot (ADR 0029). The macos CI job builds Dusty.app from the pinned
Mac engine (engine-macos-v2 from 1.1.3), audits it, builds and verifies the disk image, runs the
headless self-test, upgrade, removal and moved app scenarios and writes the Mac
SBOM. Staging checks those receipts and fails the whole draft when any Mac input
is missing or did not pass. A v1.0.x servicing release stays Windows only.
The draft's text is docs/release-notes/<tag>.md, which must exist.

A pushed snapshot is tagged only after its public CI passes in full. If it
fails, that snapshot is never tagged or released. The exporter allows one
snapshot per version and never rewrites public history, so the fix ships as
the next patch version, exported on top, and the changelog marks the skipped
version as not released. 1.1.0, 1.1.1 and 1.1.2 were skipped this way, so the
first release with Windows and Mac is 1.1.3, and its upgrade gate still starts
from 1.0.1. To avoid skipping versions, a candidate first runs the same public
CI in dusty-corporation/dusty-staging, which is free: push the reviewed dry
run's tree to a branch there and push it to dusty only when every job passes.
dusty-staging never gets tags or releases.

The gated release contains:

- Dusty-<version>-Setup.exe (unsigned).
- THIRD_PARTY_NOTICES.md and a CycloneDX SBOM, dusty-<version>-sbom.json.
- installer-jedi-source.zip with retained reviewed source and notices.
- ffmpeg-n9.0.2-946fcce.tar.gz and the exact build_ffmpeg.sh.
- From v1.1.0: Dusty-<version>-macos-arm64.dmg (signed ad hoc, not notarized),
  THIRD_PARTY_NOTICES-macos.md, dusty-<version>-macos-arm64-sbom.json and the
  exact Mac FFmpeg build script, build_ffmpeg-macos.sh. The Mac FFmpeg is built
  from the same ffmpeg-n9.0.2-946fcce.tar.gz.
- SHA256SUMS.txt covering every asset above.

FFmpeg corresponding-source and build-script bytes are checked against pins.
Bundle and installer-wide licenses must pass before any installer is uploaded.
The synthetic failing-license test proves upload stays blocked on failure.
The installer is built with pinned Inno Setup 6.7.3. No portable bundle is released.

## Local gates

Use the commands in CONTRIBUTING.md. Native build reproduction is documented in
build-native.md; model conversion in build-from-source.md. Installed acceptance,
firewall rules, WFP calibration, deliberate abort/SEH crash tests and real WER
store inspection run only on disposable GitHub-hosted Windows runners.
Per-user WER exclusions and their limits are documented in ../privacy.md.

## SmartScreen testing

A file downloaded with gh may lack Windows' internet zone tag. In a disposable
VM, add it before checking the actual prompt:

```powershell
Set-Content -LiteralPath .\Dusty-1.0.1-Setup.exe -Stream Zone.Identifier -Value "[ZoneTransfer]`r`nZoneId=3"
Get-FileHash .\Dusty-1.0.1-Setup.exe -Algorithm SHA256
```

Compare with the exact release checksum first. Windows reputation and policy
still determine the prompt. Never turn off security to force a pass.

## Uninstall and helper failure

Windows Settings > Apps is the supported route. Its registered arguments show
Dusty's own confirmation once and suppress Inno's duplicate generic prompt.
The protected-installation check runs first. If the app helper cannot start,
uninstall stops with a distinct message. Do not delete user folders manually;
repair/reinstall the same verified build, then retry Settings > Apps.
Directly running internal unins*.exe without registered arguments is unsupported.
