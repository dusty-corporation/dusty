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


## ThinkPad installed-app endurance: two cases

PM approved the ThinkPad proxy; the Surface run belongs to M7. Use an approved
installed M6 build, not an M5-only build for real use. Input preparation can run
now. Download/test Small, Large v3 Turbo and Voice detection in Manage models
first. Plug in power, prevent sleep for this test, finish any real work, select
Tools > Clear history, and close Dusty. This removes its saved list, not recordings
or transcripts. Allow 5 GB free on both the benchmark and app-data drives.

Use PowerShell 7, already used for the earlier bench kit. No Python or clone is
needed. These explicit preparation downloads are outside the processing app.
Choose a fresh folder; commands refuse an existing one:

```powershell
$bench = 'C:\bench\m6-endurance'
if (Test-Path -LiteralPath $bench) { throw 'Choose a new benchmark folder' }
New-Item -ItemType Directory -Path $bench | Out-Null
$revision = '95351993067875df3ff3b00d55324b321d3165b5'
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/dusty-corporation/dusty/$revision/tools/bench/thinkpad-endurance.ps1" -OutFile "$bench\thinkpad-endurance.ps1"
if ((Get-FileHash "$bench\thinkpad-endurance.ps1" -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'da6edabd4c03076b5e00595fdf20bf6aff318835fb1d1b1c030081abb9642322') { throw 'Script hash mismatch' }
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/dusty-corporation/dusty/$revision/tests/fixtures/audio/bench/swineherd.mp3" -OutFile "$bench\swineherd.mp3"
if ((Get-FileHash "$bench\swineherd.mp3" -Algorithm SHA256).Hash.ToLowerInvariant() -ne '17d68d8940e92907f13e6e2bedc5f997fa1b41fa9fca9e0aefd89760f97175b6') { throw 'Source audio hash mismatch' }
$install = Join-Path $env:LOCALAPPDATA 'Programs\Dusty'
& "$bench\thinkpad-endurance.ps1" -SourceMp3 "$bench\swineherd.mp3" -Work "$bench\run" -InstallRoot $install -PrepareOnly
Get-FileHash "$bench\run\long.wav" -Algorithm SHA256
```

Expected long.wav hash:
`8455996fe6970d43828600d976712ab4b37c40b22863d4fa0031f4bc47921de3`.
It is exactly the desktop input: 12 copies of the public-domain LibriVox
Swineherd fixture, decoded with the installed pinned FFmpeg to mono 16 kHz s16le,
written with a canonical 44-byte WAV header. Duration **7920.1875 seconds**
(2 hours 12 minutes). Source URL and public-domain provenance are in
`tests/fixtures/AUDIO_SOURCES.md`; this is repeated content, not an accuracy test.
The hash was independently reproduced by this PowerShell helper on the desktop.
If the hash differs, stop; do not run a different input and call it comparable.

Run both installed-app cases (same PowerShell session, or reassign bench/install):

```powershell
$bench = 'C:\bench\m6-endurance'
$install = Join-Path $env:LOCALAPPDATA 'Programs\Dusty'
& "$bench\thinkpad-endurance.ps1" -SourceMp3 "$bench\swineherd.mp3" -Work "$bench\run" -InstallRoot $install
Get-Content "$bench\run\vulkan\summary.json"
Get-Content "$bench\run\cpu\summary.json"
Get-ChildItem (Join-Path $env:LOCALAPPDATA 'Dusty\work') -Force
```

The helper launches **the installed dusty.exe**, using its shared headless
coordinator, first Turbo q8_0 on Vulkan and then Small on CPU, VAD on, automatic
language, TXT export, normal hardware-derived thread default (recorded in JSON).
It uses installed models without copying them or changing settings. It refuses
pre-existing saved jobs and unrelated state; its second case may replace only
its own first completed public job. Separate fresh output folders prevent
transcript replacement. No files are deleted by the helper.

Leave the app closed and do not start other transcription while measuring.
The two cases may take a substantial part of the afternoon; they are separate
from the 20-minute offline checklist. No unmeasured completion time is promised.
Keep the generated recording/transcripts local. Send only the two summary
objects plus ThinkPad/Windows/app build identity and whether AC power/sleep
prevention was used. Required results:

- Each case exit 0, status done, actual backend matches Vulkan or CPU requested.
- Wall seconds and RTF = wall seconds / 7920.1875.
- Sampled peak process-tree working-set bytes and temporary-work bytes. About
  one sample/second plus CIM overhead; not GPU VRAM, may miss shorter peaks or
  double-count shared pages. Comparable method to desktop, not exact peak RAM.
- Work folder has zero entries afterwards, TXT exists and opens, source unchanged.
- Installed executable SHA-256 and actual threads (both recorded automatically).

A fallback, failure or retained work is a FAIL with its actual summary, not a
Vulkan success. Preserve evidence; do not delete uncertain work manually. If you
must abort, terminate the public-test Dusty process in Task Manager; its native
children must die. Do not reuse result folders or report an interrupted run as
complete. No ThinkPad endurance result is claimed until the Owner sends it.

## Final clean-snapshot VM recheck after M6 fixes

Use Dusty-M5's clean snapshot and the final gated M6 candidate identified in
M6-report.md, not frozen .13/.14. This is a test-only candidate until engine-v3
publication/pin activation and normal CI pass. Copy the artifact from the
read-only host share into guest Downloads, verify its reported SHA-256, and add
Mark of the Web as in M5-checklist.md. Do not warm the trust store by running
Invoke-WebRequest or another Windows-native request to GitHub first.

1. Fresh standard-user Setup: all five transcription choices appear immediately;
   Checking this computer... is visible, Next disabled until the bounded check
   ends. No real VM GPU means Small recommendation. Check three license views,
   no UAC, then Tiny plus automatic Voice detection. Download succeeds from the
   cold store, tests pass, Finish launches with Tiny selected. Report the root
   count before/after if convenient; do not install roots by hand.
2. Choose Documents/Transcripts explicitly. Re-run Setup with Tiny, Small and
   Small English selected after pre-installing Tiny and Small. Only Small English
   is named/counts as a download if Voice detection is already verified. The
   bytes and bar reach the same total. All selected models are still tested.
   Repeat with everything installed: names are already downloaded, Check and
   test, no misleading download amount. No network access is needed for checks.
3. Keep the chosen folder through Model Manager download/cancel/normal close,
   Task Manager forced death and resumed partial, tampered Tiny detection and
   Download again, offline Setup Finish without a model, then online Setup retry.
   Reopen after each phase; folder stays Documents/Transcripts. Only explicitly
   choosing a new folder changes it. Use public recordings and fresh outputs.
4. Check empty/stale model selection after successful Setup becomes its tested
   default, while a valid previously chosen installed model stays selected.
   Verify About has separate privacy content, selectable repository and working
   local Third-party notices, without opening a network link automatically.
5. Uninstall through Windows Settings > Apps. This time actually UNCHECK Also
   remove downloaded models. Exactly one Dusty confirmation, no generic second
   confirmation. Models remain byte-identical; app/settings/state/logs/work are
   removed; public outputs/sentinels remain. Reinstall uses those models, then
   repeat with removal checked and verify owned models/data/app are gone while
   recordings and outputs remain. Manual keep-models was not tested in M5.

Return numbered PASS/FAIL, candidate run/hash, Windows version and any plain
error text. Do not send private filenames, paths, recordings or settings.
The desktop/ThinkPad offline and endurance protocols remain separate below/above;
this VM recheck does not substitute for real-device Vulkan or actual account
path tests. The real Surface smoke remains M7.
