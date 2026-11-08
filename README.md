# Dusty

Private transcription that never leaves your computer.

Dusty turns recordings of lectures, meetings and conversations into text, right
on your own Windows PC or Mac. It works offline, it is free and open source, and
your recordings and transcripts are never uploaded anywhere.

**[Download the latest release](https://github.com/dusty-corporation/dusty/releases/latest)**

## Download

| | Windows | Mac |
| --- | --- | --- |
| File to download | `Dusty-<version>-Setup.exe` | `Dusty-<version>-macos-arm64.dmg` |
| Works on | Windows 10 22H2 or Windows 11, 64-bit Intel or AMD | A Mac with Apple silicon (M1 or later), macOS 13.3 or later |
| Faster with | A Vulkan graphics card, with the processor as a fallback | The Mac's built-in GPU (Metal), with the processor as a fallback |
| Install guide | [Install Dusty on Windows](docs/user/install.md) | [Dusty on a Mac](docs/user/mac.md) |

Download only from this repository's Releases page. Each release also has a
SHA256SUMS.txt file so you can check that your download was not changed.

## What Dusty does

- Transcribes audio and video recordings: one file, many files, or a whole folder.
- Saves transcripts as plain text and Word documents, with SRT and VTT captions
  and JSON as extra choices.
- Understands many spoken languages, and can translate them into English.
- Lets you pick a model, from Tiny (fastest) to Large v3 Turbo (most accurate).
  You download only the models you choose, once.
- Can skip long silent parts, and accepts vocabulary hints for names and terms.
- Keeps working through a long list one recording at a time, and can pick up
  again after a crash or power cut.

Automatic transcripts can contain mistakes, especially with names, numbers and
medical terms. Always review a transcript before relying on it.

## Opening Dusty the first time

Dusty is free and its downloads are not signed with a paid certificate, so your
computer shows a one-time warning. First check your download (see below).

**Windows.** If you see "Windows protected your PC", choose More info, then Run
anyway. Setup does not need administrator rights.

**Mac.** Drag Dusty to Applications and open it. When macOS says Dusty was not
opened, choose Done. Then open System Settings, Privacy & Security, scroll down
and choose Open Anyway next to the Dusty message. Your Mac remembers this.

If your organization manages your computer and blocks these steps, ask its
administrator. Never turn off your computer's security to install Dusty.

## Check your download

Compare your file's SHA256 value with the line for that exact file name in the
release's SHA256SUMS.txt. Every character must match. If it differs, do not
open the file.

On Windows, in PowerShell:

```powershell
Get-FileHash "$env:USERPROFILE\Downloads\Dusty-<version>-Setup.exe" -Algorithm SHA256
```

On a Mac, in Terminal:

```bash
shasum -a 256 ~/Downloads/Dusty-<version>-macos-arm64.dmg
```

A matching value shows the file was not changed after the release was built.
It does not prove on its own that a file is safe.

## Your privacy

- Transcription runs entirely on your computer, with no account and no internet
  connection needed.
- Dusty has no telemetry or analytics. It connects to the internet only when you
  ask it to download a model, and it checks every downloaded file before using it.
- Your recordings are never changed. Transcripts are saved only where you choose.
- Dusty's short local log never contains transcript text or your file names.

Read [Privacy and local data](docs/privacy.md) before using confidential material.

## Help

- [User guide](docs/user/README.md): first run, transcribing, models and vocabulary hints
- [Troubleshooting](docs/user/troubleshooting.md) and [frequently asked questions](docs/user/faq.md)
- [Report a problem](https://github.com/dusty-corporation/dusty/issues)

## For developers

Release downloads are built by this repository's CI from the public source in
this repository, and the maintainer reviews each build before publishing it.
See [How it was built](docs/how-it-was-built.md) for the development and audit
process, [CONTRIBUTING](CONTRIBUTING.md) for local checks, the
[source build guide](docs/dev/build-from-source.md) and the
[release process](docs/dev/release-process.md).

## License

Dusty's own code is [Apache-2.0](LICENSE), with [NOTICE](NOTICE). Third-party
components keep their own licenses. Each release includes complete third-party
notices, a software bill of materials and the corresponding sources where
licenses require them.
