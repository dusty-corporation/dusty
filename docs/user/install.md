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

1. Read the license page, including Dusty's Apache-2.0 terms, NOTICE and the
   Microsoft Visual C++ runtime end-user terms. Continue only if you agree.
2. Choose a transcription model. Small: Balanced, all languages is a conservative choice on a computer
   without a working graphics card. Voice detection is included automatically.
3. Keep the suggested per-user app folder unless you have a reason to change it.
   Installation should not require administrator approval.
4. Review the GitHub download confirmation. Model files can be large; wait for
   download and verification to finish. No recording is sent.
5. Setup runs a local self-test. A download, verification or self-test failure
   must be resolved before installation can report success.
6. Open Dusty from the Start Menu and follow [First run](first-run.md).

## Upgrade or remove Dusty

An upgrade keeps models that still verify, avoiding another download. Uninstall
offers a choice to remove downloaded models as well as the app's settings,
unfinished-recording list, logs and temporary work. Read that choice carefully.
Your recordings and transcript folders are not removal targets. Unfamiliar
files or unsafe folder arrangements are preserved rather than guessed at.
The [privacy guide](../privacy.md) explains the locations and deletion limits.
