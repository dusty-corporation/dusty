# M5 fresh Windows 11 acceptance checklist

Owner runs this on a disposable VM, not on the host installation. Allow about
90 minutes of testing after Windows and model downloads. Record PASS/FAIL per
number, installer versions, guest Windows build and screenshots of failures.
Do not send recordings, transcript contents, settings or raw Security logs.

## Owner actions before testing

1. Owner confirmed AMD SVM enabled on 2026-10-23. Check it remains enabled.
   Task Manager > Performance > CPU should say Virtualization: Enabled.
2. Use the installed VirtualBox 7.2.22 on Windows 11 Home. Full client Hyper-V
   is not supplied with Home. No Extension Pack is needed for this test.
3. Create a VM named Dusty-M5, Windows 11 (64-bit), with the Owner's Windows 11
   26H2 x64 ISO from Downloads. Choose manual installation (skip unattended).
   Settings: 8192 MB RAM, 4 CPUs (stay within VirtualBox's green range), 100%
   execution cap, EFI enabled, Secure Boot enabled, TPM version 2.0, I/O APIC
   enabled, SATA dynamically allocated VDI 80 GB, VBoxSVGA graphics, 128 MB video,
   3D acceleration off, NAT network. Keep at least 30 GB free on the host.
   Do not disable host security features if startup fails; send the exact error.
4. Boot the ISO and install normally. Select "I don't have a product key" only
   if offered; use this temporary, unactivated test VM within Microsoft's terms.
   Complete supported Windows setup/account requirements. Do not bypass TPM,
   Secure Boot, account or other Windows setup requirements. If installation
   demands a license or unsupported bypass, stop VM setup and tell the Owner.
5. After Windows setup, as the guest administrator: VirtualBox Devices > Insert
   Guest Additions CD image. Open the guest CD and run VBoxWindowsAdditions.exe
   as administrator. Complete the signed driver installation and reboot the guest.
   This is required for 1920 x 1080 and the shared folder below. No Extension Pack.
6. From the guest administrator account: Settings > Accounts > Other users >
   Add account > I don't have this person's sign-in information > Add a user
   without a Microsoft account. Create DustyTester; its Account type must be
   Standard User. Sign out, then sign in as DustyTester. Keep the administrator
   account separate. Dusty must never request its credentials.
7. Configure the read-only auto-mounted share described below before taking
   the snapshot named clean, so it is present after a revert. Shared clipboard and
   drag/drop can remain off; enable only the read-only shared folder below. The VM normally exposes no physical
   Vulkan GPU, so Small pre-selection is expected; it cannot prove Iris Xe use.
   Set the guest display to 1920 x 1080 and 100% before baseline tests, then
   use 150% for the scale checks. Do not change the host display. If the guest
   cannot provide that resolution, record the exact limitation and arrange the
   VM display drivers before testing; do not count clipped screens as a pass.

Settings checked against Oracle VirtualBox 7.2 [creation guide](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/create-vm.html)
and [VM settings](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/working-with-vms.html),
and Microsoft's [Windows 11 requirements](https://learn.microsoft.com/en-us/windows/whats-new/windows-11-requirements),
retrieved 2026-10-23. Microsoft specifies 4 GB RAM/64 GB storage minimum;
this test assigns 8 GB/80 GB. The ISO version is Owner-supplied, not independently
identified by Dusty. Do not download an unofficial Windows image.

## Transfer the exact repaired builds using one read-only share

The Owner is creating Dusty-M5: Windows 11 Home, 8 GB, 4 CPUs, 80 GB VDI,
VBoxSVGA, standard user DustyTester, snapshot clean. Keep that configuration.
Earlier: **v0.5.0-m5.11**, CI 40099284709. Later: **v0.5.0-m5.12**, CI 40100326932.
Both are successful DRAFT releases. The latter tested the real .11 to .12 upgrade.
Do not use .1 through .10. Do not publish any release.

Run on the HOST in PowerShell, using the Owner's authenticated gh:

```powershell
$vmShare = 'C:\Users\kdash\bench\m5-vm'
New-Item -ItemType Directory -Force -Path $vmShare, "$vmShare\m5.11", "$vmShare\m5.12" | Out-Null
gh release download v0.5.0-m5.11 --repo dusty-corporation/dusty --dir "$vmShare\m5.11"
if ($LASTEXITCODE -ne 0) { throw 'Earlier draft download failed' }
gh release download v0.5.0-m5.12 --repo dusty-corporation/dusty --dir "$vmShare\m5.12"
if ($LASTEXITCODE -ne 0) { throw 'Later draft download failed' }
Copy-Item -LiteralPath 'C:\Users\kdash\whisper_app\tests\fixtures\audio\formats\jfk.wav' -Destination "$vmShare\jfk.wav"
```

The downloads refuse to overwrite existing assets; if they already exist, keep
and verify them instead of adding --clobber. No gh credentials go into the guest.
In VirtualBox, Dusty-M5 > Settings > Shared Folders > add a Machine Folder:
Folder Path `C:\Users\kdash\bench\m5-vm`, Folder Name `m5-vm`, Read-only ON,
Auto-mount ON, permanent machine folder. Guest Additions must already be installed.
The guest UNC path is `\\VBOXSVR\m5-vm`; an assigned drive letter may vary.

In the GUEST, signed in as DustyTester, copy locally before running anything:

```powershell
if ($env:USERNAME -ne 'DustyTester') { throw 'Run this inside the VM as DustyTester' }
$vmDownloads = Join-Path $env:USERPROFILE 'Downloads\M5-check'
New-Item -ItemType Directory -Force -Path $vmDownloads | Out-Null
Copy-Item -LiteralPath '\\VBOXSVR\m5-vm\m5.11' -Destination $vmDownloads -Recurse
Copy-Item -LiteralPath '\\VBOXSVR\m5-vm\m5.12' -Destination $vmDownloads -Recurse
Copy-Item -LiteralPath '\\VBOXSVR\m5-vm\jfk.wav' -Destination $vmDownloads
$earlier = Join-Path $vmDownloads 'm5.11\Dusty-0.5.0-m5.11-draft-unsigned.exe'
$later = Join-Path $vmDownloads 'm5.12\Dusty-0.5.0-m5.12-draft-unsigned.exe'
if ((Get-FileHash -LiteralPath $earlier -Algorithm SHA256).Hash -ne '7dd7ac6d67a5cd175e2acec2956a0090c64fe3e05ff17a54393854efc7b4bac9') { throw 'Earlier installer hash mismatch' }
if ((Get-FileHash -LiteralPath $later -Algorithm SHA256).Hash -ne 'bf2b137b014e26723643f3512ca5ce7d57f7e25f831a27402c88af0d1b38cd54') { throw 'Later installer hash mismatch' }
Get-FileHash -LiteralPath $earlier,$later -Algorithm SHA256
```

Expected: both full hashes match, including the corresponding SHA256SUMS.txt
entries. Stop on mismatch. Run only the local Downloads copies. Keep the host
share read-only. The other assets are notices, CycloneDX SBOM and JEDI source.

## SPEC 11.6 checks (standard user)

| # | Action | Expected result |
|---|--------|-----------------|
| 1 | Run the earlier installer. If SmartScreen appears, after the hash check select More info, Run anyway. | Unsigned warning explained; no UAC/admin prompt. If policy prevents running it, record that rather than disable security. |
| 2 | Open each of the three license views. Read the catalog; choose Tiny for a fast test, leave Voice detection included. | Apache/NOTICE, third-party notices and Microsoft runtime EULA reachable; agreement required. Physical GPU probe bounded, no model opened. VM defaults Small; changing to Tiny remains respected. |
| 3 | Install to the default folder. On the model-download page, use Back to change Tiny to Small and back; then press Download. | Consent names and size change with the selection. Back is available before download and disabled during it. Consent becomes Downloading; byte totals appear below the bar. Each selected model is tested on Auto, smallest once on CPU, Voice detection verifies. Success uses the actual singular/plural result. |
| 4 | Leave Open Dusty now checked and press Finish. Close and reopen from Start Menu; test the default-checked Desktop shortcut too. | Dusty survives Setup exit and runs as DustyTester, no admin prompt. Welcome only while output folder unset. Choose a guest-local output folder and add Downloads\M5-check\jfk.wav. |
| 5 | Disconnect the VM network adapter, close Dusty and reboot guest. Open Dusty and transcribe JFK to Text and Word. | Offline startup/transcription/export work, intelligible expected speech; output saved only in chosen folder, models unchanged. VM CPU fallback works. Reconnect adapter afterwards. |
| 6 | Install the later test version over the earlier one. Before/after record model hashes and LastWriteTime with Get-FileHash/Get-Item. | Version changes; verified model bytes and modification times unchanged, no model redownload. Output folder and user settings preserved. |
| 7 | In Model Manager start an extra download. Cancel normally; repeat and close normally. | Active .part disappears immediately, no corrupt final model. Next attempt starts fresh. |
| 8 | Start an extra download and force-end Dusty in Task Manager. Relaunch and try again. | Child downloader dies; a recent .part can resume but must pass full size/SHA before final rename. Older-than-seven-day partials with a valid matching ownership receipt are removed at startup; unknown or changed files are preserved. No unverified file can run. |
| 9 | With Dusty closed, back up Tiny to a test-only folder. Change one byte in installed ggml-tiny.bin, leaving size unchanged; then Verify all and try using Tiny. Restore the backup only after the test. | Damaged state, cannot transcribe with the tampered model; explicit download repairs it and verifies before use. Never use a real recording. |
| 10 | Test Setup with network disconnected before its model download. | Plain failure, Retry and Finish without a model. No false success. Retry after reconnect succeeds. |
| 11 | Exercise Finish without a model after a failed download/self-test. | Verified/pre-existing models remain. Failed default selection cleared, warning shown, Choose a transcription model in Options state if models exist; recommendation prompt only if none exist. Record any failure that cannot safely be induced. |
| 12 | Uninstall, uncheck Also remove downloaded models. Leave a sentinel text file in the chosen transcript folder. | Compact Uninstall Dusty dialog, true model size, initially checked box, legible text and Cancel as default. App files, shortcuts, registration and known owned settings/state/logs/work removed. Chosen models remain; transcript folder and sentinel untouched. Unknown files or unsafe ownership metadata are always preserved. |
| 13 | Reinstall, select same model. | Kept verified models reused without download; shortcuts work. |
| 14 | Uninstall with Also remove downloaded models checked. | No app directory, owned app data, shortcuts or uninstall registration remain; user transcript folder and sentinel unchanged. |
| 15 | From clean snapshot, repeat license/catalog/download/error/finish screens at 150% display scale. | Readable, no clipped controls or hidden consent/buttons. Changing guest display scale is an Owner action. |
| 16 | From a disposable snapshot, begin Setup's model download three times; stop via Cancel, window X, then Escape. Retry afterwards. | Confirmation while active; child stops, active partial disappears, verified/pre-existing models survive. Setup closes normally without launching Dusty. Retry succeeds. Repeat when idle on the post-copy model page. |
| 17 | In the test profile only, put a sentinel under an old unmarked work folder, and choose an app-managed work/models folder as output or add a recording from it. | Unknown sentinel survives startup/self-test/uninstall. Managed source/output is refused with one plain choose-another-folder message. Existing legacy output settings are cleared with a notice, while their folder contents stay untouched. |
| 18 | If a real GPU self-test failure is reproducible, try Retry, Use the processor instead, and Finish without a model. Also select multiple models once. | GPU failure is stated plainly, CPU retry outcome is truthful, all selected models tested and one smallest CPU fallback test counted. Without preserves verified/pre-existing files and clears a failed default. Do not fabricate a failure; report unavailable hardware coverage. |

## Step 17 exact guest commands and managed paths

Use a disposable snapshot. Close Dusty first. Run only in the GUEST as DustyTester:

```powershell
if ($env:USERNAME -ne 'DustyTester') { throw 'Run only inside the test VM' }
$dustyData = Join-Path $env:LOCALAPPDATA 'Dusty'
$testFolders = @('work\probe', 'work\selftest', 'work\owner-sentinel', 'models', 'state', 'logs')
foreach ($relative in $testFolders) {
    $testFolder = Join-Path $dustyData $relative
    New-Item -ItemType Directory -Force -Path $testFolder | Out-Null
    $sentinel = Join-Path $testFolder 'owner-keep.txt'
    if (Test-Path -LiteralPath $sentinel) { throw 'Sentinel already exists; do not overwrite it' }
    'Owner VM sentinel: preserve this file' | Set-Content -LiteralPath $sentinel -Encoding utf8
}
Copy-Item -LiteralPath "$env:USERPROFILE\Downloads\M5-check\jfk.wav" -Destination (Join-Path $dustyData 'work\owner-sentinel\jfk.wav')
Get-ChildItem -LiteralPath $dustyData -Filter 'owner-keep.txt' -Recurse | Get-FileHash
```

Test these exact destinations with Choose folder (all must be refused):

- `C:\Users\DustyTester\AppData\Local\Dusty\work\owner-sentinel`
- `C:\Users\DustyTester\AppData\Local\Dusty\models`
- `C:\Users\DustyTester\AppData\Local\Dusty\state`
- `C:\Users\DustyTester\AppData\Local\Dusty\logs`
- `C:\Users\DustyTester\AppData\Local\Programs\Dusty`

Add the managed-source test recording
`C:\Users\DustyTester\AppData\Local\Dusty\work\owner-sentinel\jfk.wav`:
it must be refused. Repeat with Save next to each recording enabled. Do not
put private recordings in these folders. After startup, self-test and uninstall,
repeat the hash listing: every owner-keep.txt must remain unchanged. These unknown
sentinels intentionally prevent complete app-data removal. Revert snapshot clean
before the clean-uninstall checks; do not mistake deliberate preservation for a
failure or manually remove unknown files as part of Dusty behavior.

To test the repaired legacy-setting path, close Dusty first in the disposable
VM and run the following as DustyTester. This intentionally creates an old-style
setting only in the test account; do not use this on the host:

```powershell
if ($env:USERNAME -ne 'DustyTester') { throw 'Run only inside the test VM' }
$settingsFile = Join-Path $env:LOCALAPPDATA 'Dusty\settings.json'
$settings = Get-Content -LiteralPath $settingsFile -Raw | ConvertFrom-Json
$settings | Add-Member -NotePropertyName output_dir -NotePropertyValue (Join-Path $env:LOCALAPPDATA 'Dusty\models') -Force
[IO.File]::WriteAllText($settingsFile, ($settings | ConvertTo-Json -Depth 20), [Text.UTF8Encoding]::new($false))
```

Launch Dusty. Expected: a one-time choose-another-folder message; the folder
setting is cleared, all old contents stay. Close Dusty and inspect settings.json:
preserved_paths contains the models folder. Uninstall with model removal checked.
Expected: the protected folder, sentinels, verified models and protection metadata
remain, with the retained-data notice. This deliberate legacy protection is not
a normal clean-uninstall result. Revert clean before baseline uninstall tests.

Test the installation-folder boundary separately from a clean disposable
snapshot, after installing and closing Dusty. These commands create a synthetic
legacy destination in the guest only. They replace the installed catalog with a
sentinel, so do not launch Dusty afterwards; revert the snapshot after the test.

```powershell
if ($env:USERNAME -ne 'DustyTester') { throw 'Run only inside the test VM' }
$installRoot = Join-Path $env:LOCALAPPDATA 'Programs\Dusty'
$protectedResource = Join-Path $installRoot 'resources\models.json'
$settingsFile = Join-Path $env:LOCALAPPDATA 'Dusty\settings.json'
if (!(Test-Path -LiteralPath $protectedResource) -or !(Test-Path -LiteralPath $settingsFile)) { throw 'Install and close Dusty first' }
$settings = Get-Content -LiteralPath $settingsFile -Raw | ConvertFrom-Json
$settings | Add-Member -NotePropertyName preserved_paths -NotePropertyValue @((Join-Path $installRoot 'resources')) -Force
[IO.File]::WriteAllText($settingsFile, ($settings | ConvertTo-Json -Depth 20), [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText($protectedResource, 'Owner VM synthetic private transcript: preserve this file', [Text.UTF8Encoding]::new($false))
$before = (Get-FileHash -LiteralPath $protectedResource -Algorithm SHA256).Hash
$uninstaller = Get-ChildItem -LiteralPath $installRoot -Filter 'unins*.exe' | Select-Object -First 1
if (!$uninstaller) { throw 'Uninstaller not found' }
$result = Start-Process -FilePath $uninstaller.FullName -Wait -PassThru
if ($result.ExitCode -ne 1) { throw 'Expected protected-folder uninstall to stop with exit code 1' }
if (!(Test-Path -LiteralPath (Join-Path $installRoot 'dusty\dusty.exe')) -or !(Test-Path -LiteralPath $settingsFile)) { throw 'Protected uninstall removed app or metadata' }
if ((Get-FileHash -LiteralPath $protectedResource -Algorithm SHA256).Hash -ne $before) { throw 'Protected file changed' }
```

Expected: a plain cannot-confirm-safe-removal message before the uninstall
options; app, settings and exact sentinel bytes remain. This is deliberate
protection, not successful removal. Revert snapshot clean before any further
baseline install/uninstall checks. Do not try to repair or delete protected
contents as part of Dusty behavior.

For the tamper test, use a guest PowerShell window with Dusty closed:

```powershell
$p = Join-Path $env:LOCALAPPDATA 'Dusty\models\ggml-tiny.bin'
Copy-Item -LiteralPath $p -Destination ($p + '.test-backup')
$f = [IO.File]::Open($p, 'Open', 'ReadWrite', 'None')
try { $b = $f.ReadByte(); $f.Position = 0; $f.WriteByte([byte]($b -bxor 1)) } finally { $f.Dispose() }
```

Remove the test-only backup yourself before uninstall-leftover checks; Dusty must
not silently delete unknown files. Do not modify recordings or transcripts.

## Evidence still needed from the Owner

Send the numbered results, both draft tags, guest build, approximate timings,
SmartScreen/UAC outcome, upgrade before/after hashes/timestamps and the two
uninstall directory listings. Hardware-only Vulkan acceptance remains the
recorded ThinkPad probe PASS plus real-device self-tests; VirtualBox is a CPU
acceptance environment. Automated WFP calibration/audits run in CI; a standard
user is not expected to change firewall or Security audit policy in the VM.
