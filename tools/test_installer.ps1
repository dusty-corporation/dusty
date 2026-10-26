param([string]$Installer = '', [string]$PreviousInstaller = '')

$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Installer lifecycle runs only on the disposable CI runner' }
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $Installer) { $Installer = @(Get-ChildItem (Join-Path $repo 'build/installer/output') -Filter '*.exe')[0].FullName }
$currentInstaller = $Installer
$twoVersions = [bool]$PreviousInstaller
if ($twoVersions) {
    $older = [Diagnostics.FileVersionInfo]::GetVersionInfo((Resolve-Path $PreviousInstaller).Path).FileVersion
    $newer = [Diagnostics.FileVersionInfo]::GetVersionInfo((Resolve-Path $Installer).Path).FileVersion
    if ([version]$older -ge [version]$newer) { throw 'Upgrade acceptance requires increasing distinct installer versions' }
    $Installer = (Resolve-Path $PreviousInstaller).Path
}
$work = Join-Path $repo 'build/installer/acceptance'
New-Item -ItemType Directory -Path $work -Force | Out-Null
$install = Join-Path $work 'App install گفتگو 日本語'
# Inno uses the Windows known folder, not the LOCALAPPDATA environment override.
$local = [Environment]::GetFolderPath('LocalApplicationData')
if ($env:LOCALAPPDATA -ne $local) { throw 'Inno and app user-data roots must match' }
$data = Join-Path $local 'Dusty'
if (Test-Path -LiteralPath $data) { throw 'Refusing to change pre-existing runner app data' }
$outputs = Join-Path $work 'OneDrive/Documents/Transcript outputs گفتگو'
New-Item -ItemType Directory -Path $outputs -Force | Out-Null
$sentinel = Join-Path $outputs 'keep.txt'
'public test output sentinel' | Set-Content -LiteralPath $sentinel -Encoding utf8NoBOM
$sentinelHash = (Get-FileHash -LiteralPath $sentinel).Hash
. (Join-Path $PSScriptRoot 'uninstall_process_tree.ps1')

$werSubkey = 'Software\Microsoft\Windows\Windows Error Reporting\ExcludedApplications'
$werNames = @('dusty.exe','dusty-fetch.exe','whisper-cli.exe','ffmpeg.exe','ffprobe.exe')
function Read-WerValues([Microsoft.Win32.RegistryKey]$Hive) {
    $result = @{}
    $key = $Hive.OpenSubKey($werSubkey)
    if ($null -ne $key) {
        try { foreach ($name in $key.GetValueNames()) { $result[$name] = @($key.GetValueKind($name).ToString(), $key.GetValue($name)) } }
        finally { $key.Dispose() }
    }
    return $result
}
$werMachineBefore = Read-WerValues ([Microsoft.Win32.Registry]::LocalMachine)
$werBefore = Read-WerValues ([Microsoft.Win32.Registry]::CurrentUser)
foreach ($name in $werNames) { if ($werBefore.ContainsKey($name)) { throw 'Refusing to change pre-existing CI WER exclusion' } }
$werSentinel = 'dusty-unrelated-ci-fixture.exe'
if ($werBefore.ContainsKey($werSentinel)) { throw 'WER fixture already exists' }
$werFixture = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($werSubkey)
try { $werFixture.SetValue($werSentinel, 1, [Microsoft.Win32.RegistryValueKind]::DWord) }
finally { $werFixture.Dispose() }
$werOtherBefore = Read-WerValues ([Microsoft.Win32.Registry]::CurrentUser)
function Assert-WerExclusions([bool]$Present) {
    $values = Read-WerValues ([Microsoft.Win32.Registry]::CurrentUser)
    $expectedCount = $werOtherBefore.Count + $(if ($Present) { $werNames.Count } else { 0 })
    if ($values.Count -ne $expectedCount) { throw 'Unexpected current-user WER entry was added or removed' }
    foreach ($name in $werNames) {
        if ($values.ContainsKey($name) -ne $Present) { throw 'Current-user WER exclusion lifecycle mismatch' }
    }
    foreach ($name in $werOtherBefore.Keys) {
        if (-not $values.ContainsKey($name) -or
            (ConvertTo-Json -InputObject $values[$name] -Compress) -ne (ConvertTo-Json -InputObject $werOtherBefore[$name] -Compress)) { throw 'Unrelated WER exclusion changed' }
    }
    $machine = Read-WerValues ([Microsoft.Win32.Registry]::LocalMachine)
    if (($machine.Keys.Count -ne $werMachineBefore.Keys.Count)) { throw 'Machine WER exclusions changed' }
    foreach ($name in $werMachineBefore.Keys) {
        if (-not $machine.ContainsKey($name) -or
            (ConvertTo-Json -InputObject $machine[$name] -Compress) -ne (ConvertTo-Json -InputObject $werMachineBefore[$name] -Compress)) { throw 'Machine WER exclusion changed' }
    }
}

function Invoke-Checked([string]$Executable, [string[]]$Arguments, [int]$ExpectedExit = 0, [int]$TimeoutMs = 600000, [bool]$UninstallTree = $false) {
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $Executable
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    foreach ($arg in $Arguments) { [void]$psi.ArgumentList.Add($arg) }
    $p = [Diagnostics.Process]::new()
    $p.StartInfo = $psi
    [void]$p.Start()
    if ($UninstallTree) {
        $tracker = New-UninstallTracker $p
        $deadline = [DateTime]::UtcNow.AddMilliseconds($TimeoutMs)
        try {
            while (Update-UninstallTracker $tracker) {
                if ([DateTime]::UtcNow -ge $deadline) { throw 'Actual uninstall worker timed out' }
                Start-Sleep -Milliseconds 50
            }
            Assert-UninstallTrackerExit $tracker $ExpectedExit
        } finally { Close-UninstallTracker $tracker }
    } elseif (-not $p.WaitForExit($TimeoutMs)) { $p.Kill($true); throw 'Installer acceptance process timed out' }
    if ($p.ExitCode -ne $ExpectedExit) { throw "Installer acceptance exit_code=$($p.ExitCode) expected=$ExpectedExit" }
}
function Install-App {
    Write-Host 'acceptance: install or upgrade'
    Invoke-Checked $Installer @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/CURRENTUSER','/ACCEPTTERMS=yes','/ALLOWDOWNLOAD=yes','/MODELS=tiny',('/DIR='+$install),('/LOG='+ (Join-Path $work ('install-' + [guid]::NewGuid().ToString('N') + '.log'))))
    if (-not (Test-Path -LiteralPath (Join-Path $install 'dusty/dusty.exe'))) { throw 'Installed app missing' }
    if ($Installer -eq $currentInstaller) { Assert-WerExclusions $true }
    Invoke-Checked (Join-Path $install 'dusty-fetch/dusty-fetch.exe') @('verify','--id','tiny','--dest',(Join-Path $data 'models'),'--manifest',(Join-Path $install 'resources/models.json'))
}
function Uninstall-App([string]$Remove, [int]$ExpectedExit = 0, [string]$Log = '') {
    # Inno may choose unins001 etc. Use its own per-user registration rather
    # than assuming the generated filename across upgrade/reinstall cycles.
    $key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{7B3110E8-7983-41AC-A0ED-F6EB13DBB72A}_is1'
    $command = (Get-ItemProperty -LiteralPath $key).UninstallString
    if ($command -notmatch '^"([^"]+)" /SILENT /DUSTYCONFIRM=yes$') { throw 'Unexpected registered uninstall command' }
    $uninstaller = [IO.Path]::GetFullPath($Matches[1])
    if ([IO.Path]::GetDirectoryName($uninstaller) -ne $install -or -not (Test-Path -LiteralPath $uninstaller)) { throw 'Registered uninstaller is outside the test install or missing' }
    Write-Host ('acceptance: uninstall remove_models=' + $Remove + ' executable=' + [IO.Path]::GetFileName($uninstaller))
    $uninstallArguments = @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/REMOVEMODELS='+$Remove))
    if ($Log) { $uninstallArguments += ('/LOG='+$Log) }
    Invoke-Checked $uninstaller $uninstallArguments $ExpectedExit 600000 $true
    if ($ExpectedExit -eq 0) { Assert-WerExclusions $false }
}
function Assert-Output {
    if ((Get-FileHash -LiteralPath $sentinel).Hash -ne $sentinelHash) { throw 'User output changed' }
}
function Save-UserState {
    New-Item -ItemType Directory -Path $data -Force | Out-Null
    @{schema_version=1;output_dir=$outputs} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $data 'settings.json') -Encoding utf8NoBOM
}

. (Join-Path $PSScriptRoot 'installer_download_audit.ps1')
$audit = Start-InstallerAudit $work
try {
    # Explicitly cover the production bounded probe even in unattended setup,
    # where Windows may skip displaying the Choose model page.
    $probeResult = Join-Path $work 'probe.json'
    $p = Start-Process -FilePath (Join-Path $repo 'dist/Dusty/dusty/dusty.exe') -ArgumentList @('--probe-vulkan','--out',('"'+$probeResult+'"')) -PassThru -WindowStyle Hidden
    if (-not $p.WaitForExit(15000)) { $p.Kill($true); throw 'Installed acceptance probe exceeded outer deadline' }
    if ($p.ExitCode -notin @(0,1) -or -not (Test-Path -LiteralPath $probeResult)) { throw 'Probe did not return a supported result' }
    $probe = Get-Content -LiteralPath $probeResult -Raw | ConvertFrom-Json
    if ($probe.real_gpu_found -isnot [bool]) { throw 'Probe evidence missing boolean result' }
    Install-App
    Complete-InstallerAudit $audit $Installer $work
    Copy-Item -LiteralPath (Join-Path $work 'download-wfp.json') -Destination (Join-Path $work 'download-wfp-initial.json')
} finally { Stop-InstallerAudit $audit }
Save-UserState
$models = @(Get-ChildItem -LiteralPath (Join-Path $data 'models') -Filter '*.bin' | ForEach-Object { @{name=$_.Name;hash=(Get-FileHash -LiteralPath $_.FullName).Hash;time=$_.LastWriteTimeUtc.Ticks} })
$rule = 'Dusty-Installer-Upgrade-' + [guid]::NewGuid().ToString('N')
$Installer = $currentInstaller
try {
    New-NetFirewallRule -Name $rule -DisplayName $rule -Direction Outbound -Action Block -Profile Any -Program (Join-Path $install 'dusty-fetch/dusty-fetch.exe') | Out-Null
    Install-App
} finally { Remove-NetFirewallRule -Name $rule }
foreach ($model in $models) {
    $file = Get-Item -LiteralPath (Join-Path $data ('models/' + $model.name))
    if ((Get-FileHash -LiteralPath $file.FullName).Hash -ne $model.hash -or $file.LastWriteTimeUtc.Ticks -ne $model.time) { throw 'Upgrade did not preserve verified model' }
}
Assert-Output
# Deliberate abort/SEH belongs only on this disposable installed-app runner.
if ($env:RUNNER_ENVIRONMENT -ne 'github-hosted') { throw 'Real WER test requires a disposable hosted runner' }
$env:DUSTY_WER_ACCEPTANCE = '1'
try {
    & (Join-Path $repo '.venv/Scripts/python.exe') -m pytest -q -s tests/unit/test_crash_policy.py::test_installed_exclusions_cover_abort_and_seh_in_real_stores
    if ($LASTEXITCODE -ne 0) { throw 'Real WER stores or deliberate crash acceptance failed' }
} finally { Remove-Item Env:DUSTY_WER_ACCEPTANCE }
$werEvidence = Get-Content -LiteralPath (Join-Path $work 'wer-real-stores.json') -Raw | ConvertFrom-Json
if ($werEvidence.cases.Count -ne 10 -or $werEvidence.new_reports_observed -ne 0 -or $werEvidence.unproven_paths.Count -ne 0 -or
    $werEvidence.roots[0] -ne (Join-Path $local 'Microsoft/Windows/WER') -or
    $werEvidence.roots[1] -ne (Join-Path ([Environment]::GetFolderPath('CommonApplicationData')) 'Microsoft/Windows/WER')) { throw 'Incomplete or redirected WER-store evidence' }
Assert-WerExclusions $true
# Force each real post-download stage past a shortened CI-only deadline.
foreach ($mode in @('auto','cpu')) {
    $timeoutLog = Join-Path $work ('self-test-timeout-' + $mode + '.log')
    Invoke-Checked $Installer @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/CURRENTUSER','/ACCEPTTERMS=yes','/ALLOWDOWNLOAD=yes','/MODELS=tiny',('/TESTSELFTESTTIMEOUT='+$mode),('/DIR='+$install),('/LOG='+$timeoutLog)) 10 30000
    $stage = if ($mode -eq 'auto') { 3 } else { 4 }
    if (-not (Select-String -LiteralPath $timeoutLog -SimpleMatch ('self_test_timeout stage='+$stage) -Quiet)) { throw 'Installer did not take the required deadline failure path' }
    foreach ($model in $models) {
        if ((Get-FileHash -LiteralPath (Join-Path $data ('models/' + $model.name))).Hash -ne $model.hash) { throw 'Failed self-test changed a verified model' }
    }
    Assert-Output
}
Install-App # A normal retry must still succeed after both forced deadline failures.
# A missing GUI helper must produce its own failure, never the protected-data message.
$helper = [IO.Path]::GetFullPath((Join-Path $install 'dusty/dusty.exe'))
$heldHelper = $helper + '.test-held'
if (-not $helper.StartsWith($repo + '\') -or -not $heldHelper.StartsWith($repo + '\') -or (Test-Path -LiteralPath $heldHelper)) { throw 'Unsafe helper test paths' }
$helperHash = (Get-FileHash -LiteralPath $helper).Hash
Move-Item -LiteralPath $helper -Destination $heldHelper
try {
    $helperLog = Join-Path $work 'missing-helper-uninstall.log'
    Uninstall-App 'yes' 1 $helperLog
    $helperWording = & (Join-Path $repo '.venv/Scripts/python.exe') -c 'import json; from dusty.app.messages import INSTALLER; print(json.dumps({k: INSTALLER[k] for k in ("UninstallHelperUnavailable", "UninstallProtected")}))' | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Could not read shared helper-failure wording' }
    $helperLogText = Get-Content -LiteralPath $helperLog -Raw
    if (-not $helperLogText.Contains($helperWording.UninstallHelperUnavailable) -or $helperLogText.Contains($helperWording.UninstallProtected)) { throw 'Missing helper did not report its distinct native failure message' }
    if (-not (Test-Path -LiteralPath $heldHelper)) { throw 'Failed safety check deleted the installation' }
    Assert-Output
} finally {
    Move-Item -LiteralPath $heldHelper -Destination $helper
}
if ((Get-FileHash -LiteralPath $helper).Hash -ne $helperHash) { throw 'Restored helper bytes changed' }
# Audit the new version after upgrade, not the preceding draft's different bytes.
# Exercise the sanitized legacy-output protection with the ACTUAL new packaged app.
# The earlier installer is deliberately not trusted to contain this repair.
@{schema_version=1;output_dir=$outputs;preserved_paths=@((Join-Path $data 'models'))} | ConvertTo-Json |
    Set-Content -LiteralPath (Join-Path $data 'settings.json') -Encoding utf8NoBOM
Invoke-Checked (Join-Path $install 'dusty/dusty.exe') @('--uninstall-data','remove-models') 1
if (-not (Test-Path -LiteralPath (Join-Path $data 'settings.json'))) { throw 'Legacy protection metadata was removed' }
foreach ($model in $models) {
    $file = Get-Item -LiteralPath (Join-Path $data ('models/' + $model.name))
    if ((Get-FileHash -LiteralPath $file.FullName).Hash -ne $model.hash -or $file.LastWriteTimeUtc.Ticks -ne $model.time) { throw 'Sanitized legacy destination was changed' }
}
Save-UserState
# Inno's registered payload must also survive a protected installation destination.
$installedManifest = Join-Path $install 'resources/models.json'
$manifestBytes = [IO.File]::ReadAllBytes($installedManifest)
$privateSentinel = '{"private":"synthetic protected transcript"}'
foreach ($protectedFolder in @((Join-Path $install 'resources'), ('\\?\' + (Join-Path $install 'resources')))) {
    @{schema_version=1;preserved_paths=@($protectedFolder)} | ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $data 'settings.json') -Encoding utf8NoBOM
    [IO.File]::WriteAllText($installedManifest, $privateSentinel)
    Uninstall-App 'yes' 1
    if (-not (Test-Path -LiteralPath (Join-Path $install 'dusty/dusty.exe')) -or
        -not (Test-Path -LiteralPath (Join-Path $data 'settings.json')) -or
        [IO.File]::ReadAllText($installedManifest) -ne $privateSentinel) { throw 'Protected installed payload was removed or changed' }
}
[IO.File]::WriteAllBytes($installedManifest, $manifestBytes)
Save-UserState
& (Join-Path $repo '.venv/Scripts/python.exe') (Join-Path $PSScriptRoot 'check_installed_payload.py') $install --output (Join-Path $work 'installed-files.json')
if ($LASTEXITCODE -ne 0) { throw 'Installed file inventory failed' }
& (Join-Path $PSScriptRoot 'test_uninstall_entries.ps1') -InstallPath $install -Output (Join-Path $work 'uninstall-entries.json')
if ($LASTEXITCODE -ne 0) { throw 'Installed shortcut and uninstall registration audit failed' }
& (Join-Path $PSScriptRoot 'test_network_isolation.ps1') -Bundle $install -InstalledModels
if ($LASTEXITCODE -ne 0) { throw 'Installed WFP self-test failed' }
& (Join-Path $repo '.venv/Scripts/python.exe') (Join-Path $PSScriptRoot 'check_pe_imports.py') (Join-Path $install 'dusty') --native (Join-Path $install 'bin') --output (Join-Path $work 'installed-pe.json')
if ($LASTEXITCODE -ne 0) { throw 'Installed PE import gate failed' }
& (Join-Path $PSScriptRoot 'test_uninstall_ui.ps1') -InstallPath $install -Output (Join-Path $work 'uninstall-ui.json')
if ($LASTEXITCODE -ne 0) { throw 'Interactive uninstall confirmation test failed' }
Assert-WerExclusions $false
Assert-Output
if (Test-Path -LiteralPath (Join-Path $install 'dusty/dusty.exe')) { throw 'Uninstall left app executable' }
foreach ($model in $models) { if (-not (Test-Path -LiteralPath (Join-Path $data ('models/' + $model.name)))) { throw 'Keep-models uninstall removed a model' } }
if (Test-Path -LiteralPath (Join-Path $data 'settings.json')) { throw 'Uninstall left settings' }
Install-App
Save-UserState
Uninstall-App 'yes'
Assert-Output
if (Test-Path -LiteralPath $data) { throw 'Remove-models uninstall left owned user data' }
if (Test-Path -LiteralPath (Join-Path $install 'dusty/dusty.exe')) { throw 'Remove-models uninstall left app' }
# A two-version upgrade starts with the old setup. Also audit a fresh download
# through the CURRENT setup, so its own EXE/temp runtime is the observed image.
$audit = Start-InstallerAudit $work
try {
    $p = Start-Process -FilePath (Join-Path $repo 'dist/Dusty/dusty/dusty.exe') -ArgumentList @('--probe-vulkan','--out',('"'+$probeResult+'"')) -PassThru -WindowStyle Hidden
    if (-not $p.WaitForExit(15000)) { $p.Kill($true); throw 'Final probe exceeded deadline' }
    if ($p.ExitCode -notin @(0,1)) { throw 'Final probe returned unsupported result' }
    Install-App
    Complete-InstallerAudit $audit $Installer $work
} finally { Stop-InstallerAudit $audit }
Uninstall-App 'yes'
Assert-Output
if ((Test-Path -LiteralPath $data) -or (Test-Path -LiteralPath (Join-Path $install 'dusty/dusty.exe'))) { throw 'Final fresh-install cleanup left owned files' }
# Exercise the same stop routine as Cancel/X after real partial bytes arrive.
# The flag is honored only for explicit silent acceptance on a disposable CI runner.
$completeAudit = Get-Content -LiteralPath (Join-Path $work 'download-wfp.json') -Raw
$audit = Start-InstallerAudit $work
try {
    Invoke-Checked $Installer @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/CURRENTUSER','/ACCEPTTERMS=yes','/ALLOWDOWNLOAD=yes','/MODELS=tiny','/TESTCANCEL=yes',('/DIR='+$install)) 130
    if (@(Get-ChildItem -LiteralPath (Join-Path $data 'models') -Filter '*.part').Count) { throw 'Normal stop left an active partial' }
    # Completion racing a stop may keep a final model, but only a verified one.
    if (Test-Path -LiteralPath (Join-Path $data 'models/ggml-tiny.bin')) {
        Invoke-Checked (Join-Path $install 'dusty-fetch/dusty-fetch.exe') @('verify','--id','tiny','--dest',(Join-Path $data 'models'),'--manifest',(Join-Path $install 'resources/models.json'))
    }
    Complete-InstallerAudit $audit $Installer $work
    Copy-Item -LiteralPath (Join-Path $work 'download-wfp.json') -Destination (Join-Path $work 'download-wfp-cancel.json')
    # Retain the full successful-download receipt as the primary release audit.
    Set-Content -LiteralPath (Join-Path $work 'download-wfp.json') -Value $completeAudit -Encoding utf8NoBOM
} finally { Stop-InstallerAudit $audit }
Assert-Output
Install-App
Save-UserState
Uninstall-App 'yes'
Assert-Output
if ((Test-Path -LiteralPath $data) -or (Test-Path -LiteralPath (Join-Path $install 'dusty/dusty.exe'))) { throw 'Cancelled-install retry cleanup left owned files' }
# Skip for now must install the app without fetching or claiming a passed test.
Invoke-Checked $Installer @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/CURRENTUSER','/ACCEPTTERMS=yes','/ALLOWDOWNLOAD=yes','/SKIPMODELS=yes',('/DIR='+$install))
if (-not (Test-Path -LiteralPath (Join-Path $install 'dusty/dusty.exe'))) { throw 'Skip for now did not install the app' }
if (Test-Path -LiteralPath (Join-Path $data 'models')) { throw 'Skip for now downloaded models' }
if (Test-Path -LiteralPath (Join-Path $data 'settings.json')) { throw 'Skip for now recorded a tested default' }
Uninstall-App 'yes'
Assert-Output
Assert-WerExclusions $false
$werFixture = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($werSubkey, $true)
try { $werFixture.DeleteValue($werSentinel, $true) } finally { $werFixture.Dispose() }
@{same_version_reinstall_models_preserved=$(if (-not $twoVersions) { 'passed' } else { 'not_applicable' });wer_exclusions_current_user='passed';real_wer_abort_stores='passed';unrelated_wer_entry_preserved='passed';forced_selftest_deadline_stage3='passed';forced_selftest_deadline_stage4='passed';missing_helper_uninstall_failure='passed';previous_tag=$env:PREVIOUS_TAG;skip_for_now_without_download_or_test='passed';silent_per_user_install='passed';installer_download_tiny_and_vad='passed';current_installer_fresh_download_wfp='passed';installed_wfp='passed';two_distinct_versions=$twoVersions;upgrade_models_preserved_with_downloader_blocked='passed';uninstall_keep_models='passed';uninstall_remove_models='passed';normal_cancel_removes_partial='passed';preserved_legacy_destination='passed';protected_install_destination='passed';user_outputs_unchanged=$true} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $work 'summary.json') -Encoding utf8NoBOM
