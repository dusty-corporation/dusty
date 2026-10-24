# M6 manual offline check - desktop and ThinkPad

Owner performs this on both machines. Allow about 20 minutes per machine after
installation/model downloads. The Surface check belongs to M7. Use public test
audio and a fresh output folder. Do not send private settings, paths, transcripts
or raw logs. Do not change the frozen M5 .13/.14 drafts.

Use only the M6 gated build and SHA-256 identified in M6-report.md after its
native activation gap is resolved. If that report still marks ISSUE-026 or a
packaged gate pending, record this checklist as pending, not PASS. The M5 VM
checklist is separate and still required for the frozen pair.

| # | Owner action | Expected result / send back |
|---|---|---|
| 1 | With internet available, verify the installer hash and install for the current standard account. Complete model download/test with an already approved model and Voice detection. | Actual build/hash and model; no admin prompt; truthful test outcome. Installation time is outside the 20-minute offline test. |
| 2 | Use a local public JFK WAV and AMR plus a second copy with a Persian or accented filename. Choose a new local output folder and TXT + DOCX. Keep a separate sentinel text file there. | Files added, model/language/device choices visible, no private material. Record whether account/profile contains spaces or non-ASCII characters. |
| 3 | Disconnect every connection: desktop Ethernet unplugged and Wi-Fi off, or ThinkPad airplane mode with Ethernet disconnected. Reboot. Reopen Dusty from Start Menu. | Starts without a connection or request to download a model. Do not reconnect for steps 4 to 7. |
| 4 | Process the public recordings with Automatic, then repeat one with Processor only into a different local output folder. | All good files finish, TXT/Word open, expected JFK speech; actual graphics/processor outcome truthful. Record model, device and approximate time. |
| 5 | Start another public run. Cancel during a recording. Start a new run, close normally and accept saving progress. Reopen and choose Resume. | Cancel leaves no partial transcript, original recordings stay unchanged; Resume starts immediately and keeps finished outputs. |
| 6 | Choose a test folder under OneDrive-style Documents if available. Decline the sync warning, then choose it again and Continue with this folder. Use public audio only. | Warning before processing; decline does not save there; explicit continue writes readable outputs. Another program may upload them independently. Do not use confidential files. |
| 7 | Reopen Options and Model Manager while still offline. Verify all, then transcribe one more public file. Check output sentinel. | Local verification/options work, no model download needed, original recordings and sentinel unchanged. Delete a disposable model only if wanted; this is not required for offline acceptance. |
| 8 | Reconnect after recording results. | Send machine, Windows build, app build/hash, model/device, numbered PASS/FAIL, any plain error and timing. Confirm the network stayed disconnected through reboot and processing. Do not send recordings, outputs or local JSON state. |

The automated forced-kill/Job Object, canary and calibrated WFP tests complement
this checklist. The Owner need not change firewall or Security audit policy.
Actual physical GPU failure/retry coverage must be named as available or not
available; do not manufacture PASS for a failure screen that was not exercised.

## Separate fresh-account path check

This is additional VM evidence, not part of the 20-minute offline run. Finish
the frozen M5 .13/.14 VM checklist first. Use a separate snapshot for M6 after
the engine decision and gated build are approved.

1. In the VM's administrator account, open Settings > Accounts > Other users.
   Add a local account without a Microsoft account, with a name containing a
   space and non-ASCII letters, for example Dusty Test گفتگو. Keep it a Standard
   user. Sign in once to create its profile.
2. Open PowerShell and inspect `$env:USERPROFILE`. Windows may normalize the
   account name. Record whether the actual profile path has a space and non-ASCII
   letters. Do not rename a profile folder or edit the registry to force it.
3. From that standard account, install the approved M6 build, download/test a
   model, and transcribe public JFK audio with a non-ASCII filename. Choose an
   output folder with spaces and non-ASCII letters. Check TXT and DOCX.
4. Reopen Dusty and check the selected model and folder persist. Uninstall through
   Windows Settings > Apps, keeping a transcript-folder sentinel. Confirm the
   chosen model-removal behavior and that recordings/transcripts/sentinel stay.

Send numbered PASS/FAIL, build/hash and the two profile-character flags. Do not
send the full profile path or private recordings. If Windows normalized away
either character class, mark actual-profile coverage partial. Synthetic M6
source/install-path tests do not replace this account-level evidence.
