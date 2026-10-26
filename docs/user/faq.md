# Frequently asked questions

## Does Dusty send my recording anywhere?

Dusty processes your recordings entirely on this computer. After installation, it never needs an internet connection, and it never sends your audio or transcripts anywhere.

An optional model download is a separate, explicit online action. It sends a
request for a public model file to GitHub, not your recording or transcript.
Another program, such as OneDrive, may upload files saved in its folders.

## Is it suitable for HIPAA workflows?

Dusty is designed for confidential workflows and keeps all processing on your device. It is not certified as HIPAA-compliant; compliance depends on how your organization secures its computers and data (for example, account security, disk encryption, and backups).

## Can I rely on every word?

Automatic transcripts can contain mistakes, especially with names, medications, and numbers. Always review a transcript before relying on it for medical, legal, or other important decisions.

## Do I need Python or a terminal?

The packaged app includes its runtime. Normal transcription does not need a
terminal. The installer hash check uses a short PowerShell command; see Install.

## Can I translate Persian into English?

Choose Medium and Translate to English. Transcribe writes the spoken language;
Translate to English writes English. Automatic translation can make mistakes.
Dusty does not translate into arbitrary other target languages or label speakers.

## Does it record sound or edit transcripts?

No. Add an existing recording. Open the exported text or Word file in your
preferred editor. Dusty does not modify the recording.

## Is it free? Why the Windows warning?

Dusty is free and open source. Its own code uses Apache-2.0; bundled components
have their own notices. The installer is unsigned, so SmartScreen may warn.
Follow the source and checksum checks in [Install](install.md), not a blind bypass.

## Where can I read the licenses?

Open Help > About Dusty, then Third-party notices. These notices open from the
installed app, without a download. About also shows the app version, Apache-2.0
license and a repository address you can select and copy. Privacy and accuracy
has the separate privacy and transcript warning.

## Does clearing the list erase my recordings?

No. It removes the app's list. Finished transcripts stay in your chosen folder.
Uninstall is also designed to preserve recordings and transcript folders.
Deleting app data is not secure erasure, and cloud backups are outside Dusty's
control. Read [Privacy](../privacy.md) before using confidential material.

## Should I turn on Skip long silences?

It is off by default. Faster on recordings with long pauses. May miss quiet or distant speech.
For a lecture recorded from the back of a room, leave it off. Quiet questions
and sentence endings can be lost when voice detection is on. An option you
previously saved stays as you chose it. Voice detection is still downloaded
automatically, so it is available if you choose to use it.


When upgrading from an older test build, Skip long silences is reset off once.
After that, Dusty remembers the choice you make in Options.
