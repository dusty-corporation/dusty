# Dusty

Private transcription that never leaves your computer.

Dusty is a free, open-source Windows app that turns recordings into text, Word
documents and captions with whisper.cpp. It supports folders of recordings,
many spoken languages, translation into English with a compatible model, and
graphics acceleration with a processor fallback. Your original recordings stay
unchanged. No Python installation is needed for the packaged app.

**Current status:** prerelease engineering review. M3 is accepted; Model Manager
and downloader work are on m4-downloader. Packaging and installer acceptance are
on m5-packaging-spike; these draft user docs are on m6-docs. There is no accepted
V1 installer yet. Installer static-license review ISSUE-018 and clean-machine
checks remain open. CI artifacts and draft releases are not published releases.

## Start here

- [User guide](docs/user/README.md): install, first run, folders, models and help.
- [Privacy and local data](docs/privacy.md): storage, downloads and deletion limits.
- [Contributing](CONTRIBUTING.md) and [developer guides](docs/dev/).
- [Engineering specification](docs/pm/SPEC.md) and [current task ledger](docs/pm/LEDGER.md).

Dusty processes your recordings entirely on this computer. After installation, it
never needs an internet connection, and it never sends your audio or transcripts
anywhere. Adding a model is an explicit optional download from GitHub through a
separate downloader. There are no telemetry, update checks or cloud transcription.
Other software may sync files you save in cloud-backed folders.

Automatic transcripts can contain mistakes, especially with names, medications,
and numbers. Always review a transcript before relying on it for medical,
legal, or other important decisions.

## Windows SmartScreen warning

Review installers are unsigned. After confirming the official source and full
SHA-256 hash, Windows' "Windows protected your PC" screen may require **More
info**, then **Run anyway**. Do not disable Windows security. An unsigned warning
is not proof that a file is safe; see the [install guide](docs/user/install.md).

Compare the entire hash with the entry for the exact filename in the same build's
SHA256SUMS.txt. Replace the placeholder with your downloaded file:

```powershell
Get-FileHash -LiteralPath '.\Dusty-your-build.exe' -Algorithm SHA256
```

Stop if the hashes differ. The Owner controls installer publication; currently
only reviewed app bundles and installer audit metadata are available.

## License

Dusty's own code is [Apache-2.0](LICENSE), with [NOTICE](NOTICE). It includes an
explicit patent grant for contributors. Bundled components retain their own
licenses. Release builds include component notices, source links, an inventory
and a CycloneDX software bill of materials. Microsoft runtime terms apply only
to those runtime components, not to Dusty's own code or LGPL libraries.
