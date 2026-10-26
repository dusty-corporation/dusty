# Dusty

Private transcription that never leaves your computer.

Dusty is a free, open-source Windows app for transcribing recordings locally.
It supports Text, Word, subtitle and JSON exports, Vulkan acceleration with CPU
fallback, and optional silent-part skipping. Models download only when requested
in Setup or Model Manager. Recordings and transcripts are not uploaded.

The intended audience is a non-technical adult who records lectures and
conversations, sometimes in languages other than English, on a typical Windows
laptop. Review every transcript before relying on it.

Release installers are built by CI from this public source snapshot. The
maintainer reviews the final installer before publication. See
[How it was built](docs/how-it-was-built.md) for the development and audit process.

## Windows SmartScreen warning

Dusty is free and open source. The installer has no code-signing
certificate, so Windows may show "Windows protected your PC". First check the
installer against the SHA256SUMS.txt supplied with the same build:

```powershell
Get-FileHash .\Dusty-1.0.0-Setup.exe -Algorithm SHA256
```

Compare the entire SHA256 with the entry for that exact filename. If it differs,
do not run the installer. A checksum detects a changed file; it does not prove
that the original file is safe.

After checking the expected build, select "More info", then "Run anyway" in the
SmartScreen dialog. If your organization prevents this, ask its administrator;
do not turn off Windows security. Dusty installs for your Windows account and
does not need administrator privileges.

## License

Dusty's own code is [Apache-2.0](LICENSE), with [NOTICE](NOTICE). Third-party
components retain their licenses. Each release includes complete
THIRD_PARTY_NOTICES.md, a CycloneDX SBOM and retained installer component sources.
The Visual C++ runtime protective terms are also reachable in Setup.

## User guide and developer checks

Start with [Install](docs/user/install.md) and [First run](docs/user/first-run.md).
The [user guide](docs/user/README.md) covers folders, models, vocabulary hints
and troubleshooting. Read [Privacy and local data](docs/privacy.md) before using
confidential material. Developers can use [CONTRIBUTING](CONTRIBUTING.md).
The [source build guide](docs/dev/build-from-source.md) includes the verified
model-conversion recipe. [Release process](docs/dev/release-process.md) explains
the license, hash and offline gates. The Owner publishes accepted builds.
