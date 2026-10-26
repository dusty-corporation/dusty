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

The gated release contains:

- Dusty-<version>-Setup.exe (unsigned).
- THIRD_PARTY_NOTICES.md and a CycloneDX SBOM.
- installer-jedi-source.zip with retained reviewed source and notices.
- ffmpeg-n9.0.2-946fcce.tar.gz and the exact build_ffmpeg.sh.
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
Set-Content -LiteralPath .\Dusty-1.0.0-Setup.exe -Stream Zone.Identifier -Value "[ZoneTransfer]`r`nZoneId=3"
Get-FileHash .\Dusty-1.0.0-Setup.exe -Algorithm SHA256
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
