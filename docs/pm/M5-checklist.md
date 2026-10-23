# M5 fresh Windows 11 acceptance checklist

Owner runs this on a disposable VM, not on the host installation. Allow about
45 minutes of testing after Windows and model downloads. Record PASS/FAIL per
number, installer versions, guest Windows build and screenshots of failures.
Do not send recordings, transcript contents, settings or raw Security logs.

## Owner actions before testing

1. Enable AMD SVM in the desktop firmware, then restart. Owner action only.
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
5. From the guest administrator account: Settings > Accounts > Other users >
   Add account > I don't have this person's sign-in information > Add a user
   without a Microsoft account. Create DustyTester; its Account type must be
   Standard User. Sign out, then sign in as DustyTester. Keep the administrator
   account separate. Dusty must never request its credentials.
6. Take a clean VM snapshot before installing Dusty. Shared clipboard, drag/drop
   and host shared folders can remain off. The VM normally exposes no physical
   Vulkan GPU, so Small pre-selection is expected; it cannot prove Iris Xe use.

Settings checked against Oracle VirtualBox 7.2 [creation guide](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/create-vm.html)
and [VM settings](https://docs.oracle.com/en/virtualization/virtualbox/7.2/user/working-with-vms.html),
and Microsoft's [Windows 11 requirements](https://learn.microsoft.com/en-us/windows/whats-new/windows-11-requirements),
retrieved 2026-10-23. Microsoft specifies 4 GB RAM/64 GB storage minimum;
this test assigns 8 GB/80 GB. The ISO version is Owner-supplied, not independently
identified by Dusty. Do not download an unofficial Windows image.

## Get the two draft installers into the guest

Draft releases require the Owner's authenticated GitHub access. On the host,
use `gh release list --repo dusty-corporation/dusty` to identify two successful
`v0.5.0-m5.N` drafts. Do not publish either. Download all five assets for each
version into separate host folders:

```powershell
gh release download v0.5.0-m5.1 --repo dusty-corporation/dusty --dir .\m5-test-1
gh release download v0.5.0-m5.2 --repo dusty-corporation/dusty --dir .\m5-test-2
```

Use the actual successful tag numbers from the M5 report if these two failed.
In the guest browser, sign in to GitHub yourself, open the draft release and
save the installer and SHA256SUMS.txt in Downloads. Alternatively make a read-only
ISO containing the host download folders, mount it in VirtualBox's optical drive,
and copy to guest Downloads. Never copy your gh authentication file into the VM.
Check the entire installer SHA against its exact SHA256SUMS entry:

```powershell
Get-FileHash .\Dusty-*-draft-unsigned.exe -Algorithm SHA256
```

Expected: exact match. Do not run a mismatching file. The other assets are
THIRD_PARTY_NOTICES.md, the versioned CycloneDX SBOM and installer-jedi-source.zip.

## SPEC 11.6 checks (standard user)

| # | Action | Expected result |
|---|--------|-----------------|
| 1 | Run the earlier installer. If SmartScreen appears, after the hash check select More info, Run anyway. | Unsigned warning explained; no UAC/admin prompt. If policy prevents running it, record that rather than disable security. |
| 2 | Open each of the three license views. Read the catalog; choose Tiny for a fast test, leave Voice detection included. | Apache/NOTICE, third-party notices and Microsoft runtime EULA reachable; agreement required. Physical GPU probe bounded, no model opened. VM defaults Small; changing to Tiny remains respected. |
| 3 | Accept the inline download consent and finish installation to the default folder. | Only github.com downloads through dusty-fetch; selected model and Voice detection verify. Each selected model tested on Auto, smallest once on CPU. Plain progress; no failed test called success. |
| 4 | Launch from Start Menu; test optional Desktop shortcut if selected. | Both open Dusty, no admin prompt. Welcome only while output folder unset. Choose a guest-local output folder and add the public JFK fixture from the repository's tests/fixtures/audio/formats/jfk.wav. |
| 5 | Disconnect the VM network adapter, close Dusty and reboot guest. Open Dusty and transcribe JFK to Text and Word. | Offline startup/transcription/export work, intelligible expected speech; output saved only in chosen folder, models unchanged. VM CPU fallback works. Reconnect adapter afterwards. |
| 6 | Install the later test version over the earlier one. Before/after record model hashes and LastWriteTime with Get-FileHash/Get-Item. | Version changes; verified model bytes and modification times unchanged, no model redownload. Output folder and user settings preserved. |
| 7 | In Model Manager start an extra download. Cancel normally; repeat and close normally. | Active .part disappears immediately, no corrupt final model. Next attempt starts fresh. |
| 8 | Start an extra download and force-end Dusty in Task Manager. Relaunch and try again. | Child downloader dies; a recent .part can resume but must pass full size/SHA before final rename. Partials older than 7 days are removed at next startup. No unverified file can run. |
| 9 | With Dusty closed, back up Tiny to a test-only folder. Change one byte in installed ggml-tiny.bin, leaving size unchanged; then Verify all and try using Tiny. Restore the backup only after the test. | Damaged state, cannot transcribe with the tampered model; explicit download repairs it and verifies before use. Never use a real recording. |
| 10 | Test Setup with network disconnected before its model download. | Plain failure, Retry and Finish without a model. No false success. Retry after reconnect succeeds. |
| 11 | Exercise Finish without a model after a failed download/self-test. | Verified/pre-existing models remain. Failed default selection cleared, warning shown, Choose a transcription model in Options state if models exist; recommendation prompt only if none exist. Record any failure that cannot safely be induced. |
| 12 | Uninstall, uncheck Also remove downloaded models. Leave a sentinel text file in the chosen transcript folder. | Real model size shown. App files, shortcuts, registration, settings/state/logs/work removed. Only chosen models remain under %LOCALAPPDATA%\Dusty; transcript folder and sentinel untouched. |
| 13 | Reinstall, select same model. | Kept verified models reused without download; shortcuts work. |
| 14 | Uninstall with Also remove downloaded models checked. | No app directory, owned app data, shortcuts or uninstall registration remain; user transcript folder and sentinel unchanged. |
| 15 | From clean snapshot, repeat license/catalog/download/error/finish screens at 150% display scale. | Readable, no clipped controls or hidden consent/buttons. Changing guest display scale is an Owner action. |

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
