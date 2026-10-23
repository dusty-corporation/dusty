# Install Dusty

You need a Windows 10 22H2 or Windows 11 computer with a 64-bit Intel or AMD
processor. A compatible graphics card can make transcription faster; the
processor can work without one. Internet access is needed to download the app
and the models you choose. Transcribing does not need it.

The installer is still under review. Do not treat a draft or an unsigned CI
artifact as a published release. Follow the Owner's review instructions until
a release is published in the official
[Dusty repository](https://github.com/dusty-corporation/dusty).

## Check your download

Get the installer and its accompanying SHA256SUMS.txt from the same trusted
build. Do not use a checksum supplied by an unrelated download site.

1. Right-click the downloaded installer and choose Copy as path.
2. Open PowerShell. Type `Get-FileHash -Algorithm SHA256 `, paste the path, and
   press Enter. Keep quotation marks around a path containing spaces.
3. Compare the complete SHA256 value with the line for that exact installer
   filename in SHA256SUMS.txt. Letter case does not matter. Every digit must match.
4. If it differs, stop. Do not run the installer. Download it again from the
   official source and ask the Owner if the mismatch remains.

A matching hash detects a changed download. It does not independently establish
that the website or publisher is trustworthy.

## Windows SmartScreen

Review builds are unsigned. Windows may say "Windows protected your PC".
After checking the source and hash, select **More info**, then **Run anyway**.
If your organization blocks this choice, ask its administrator. Do not disable
Windows security. The warning reflects the unsigned build; it does not prove
that a file is safe.

## Run Setup

1. Read the license page. Its three buttons show Dusty's Apache-2.0 license
   and NOTICE, third-party notices, and Microsoft runtime terms. Continue only
   if you agree.
2. Choose one or more transcription models. Setup briefly checks for a usable
   graphics device without opening a model. It suggests Large v3 Turbo when a
   real graphics device works and memory meets the recommendation; otherwise
   Small. A low-memory warning does not block installation. You may change the
   choice. Voice detection is always included.
3. Keep the suggested per-user app folder unless you have a reason to change it.
   Installation should not require administrator approval.
4. Review the GitHub download confirmation. Model files can be large; wait for
   download and verification to finish. No recording is sent.
5. Setup checks downloaded files and tests each selected transcription model
   with Automatic, plus the smallest selected model once on the processor.
   A failure offers Retry. A failed graphics test also offers Retry on CPU,
   and says which device actually worked. You can choose Finish without a model
   instead. That finishes installing the app, not a successful model test.
   Verified and pre-existing files stay; a failed default choice is cleared.
   Dusty shows the warning and asks you to choose a model in Options, or download
   one if none is installed.
6. Open Dusty from the Start Menu and follow [First run](first-run.md).

## Upgrade or remove Dusty

An upgrade keeps models that still verify, avoiding another download. Uninstall
offers a choice to remove downloaded models as well as the app's settings,
unfinished-recording list, logs and temporary work. Read that choice carefully.
Your recordings and transcript folders are not removal targets. Unfamiliar
files or unsafe folder arrangements are preserved rather than guessed at.
The [privacy guide](../privacy.md) explains the locations and deletion limits.

Normal Cancel or normal close removes the active partial download. After a crash
or forced close, a recent partial may resume, but its full size and SHA-256 must
still match before use. At startup, partials older than seven days are removed.

The uninstaller's Also remove downloaded models checkbox starts checked and
shows the actual size. Uncheck it to keep verified models for reinstallation.
Your chosen transcript folders are never uninstall targets.
