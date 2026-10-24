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
$install = Join-Path $work 'app'
# Inno uses the Windows known folder, not the LOCALAPPDATA environment override.
$local = [Environment]::GetFolderPath('LocalApplicationData')
if ($env:LOCALAPPDATA -ne $local) { throw 'Inno and app user-data roots must match' }
$data = Join-Path $local 'Dusty'
if (Test-Path -LiteralPath $data) { throw 'Refusing to change pre-existing runner app data' }
$outputs = Join-Path $work 'user-outputs'
New-Item -ItemType Directory -Path $outputs -Force | Out-Null
$sentinel = Join-Path $outputs 'keep.txt'
'public test output sentinel' | Set-Content -LiteralPath $sentinel -Encoding utf8NoBOM
$sentinelHash = (Get-FileHash -LiteralPath $sentinel).Hash

function Invoke-Checked([string]$Executable, [string[]]$Arguments, [int]$ExpectedExit = 0) {
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $Executable
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    foreach ($arg in $Arguments) { [void]$psi.ArgumentList.Add($arg) }
    $p = [Diagnostics.Process]::new()
    $p.StartInfo = $psi
    [void]$p.Start()
    if (-not $p.WaitForExit(600000)) { $p.Kill($true); throw 'Installer acceptance process timed out' }
    if ($p.ExitCode -ne $ExpectedExit) { throw "Installer acceptance exit_code=$($p.ExitCode) expected=$ExpectedExit" }
}
function Install-App {
    Write-Host 'acceptance: install or upgrade'
    Invoke-Checked $Installer @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/CURRENTUSER','/ACCEPTTERMS=yes','/ALLOWDOWNLOAD=yes','/MODELS=tiny',('/DIR='+$install))
    if (-not (Test-Path -LiteralPath (Join-Path $install 'dusty/dusty.exe'))) { throw 'Installed app missing' }
    Invoke-Checked (Join-Path $install 'dusty-fetch/dusty-fetch.exe') @('verify','--id','tiny','--dest',(Join-Path $data 'models'),'--manifest',(Join-Path $install 'resources/models.json'))
}
function Uninstall-App([string]$Remove) {
    # Inno may choose unins001 etc. Use its own per-user registration rather
    # than assuming the generated filename across upgrade/reinstall cycles.
    $key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{7B3110E8-7983-41AC-A0ED-F6EB13DBB72A}_is1'
    $command = (Get-ItemProperty -LiteralPath $key).UninstallString
    if ($command -notmatch '^"([^"]+)"$') { throw 'Unexpected registered uninstall command' }
    $uninstaller = [IO.Path]::GetFullPath($Matches[1])
    if ([IO.Path]::GetDirectoryName($uninstaller) -ne $install -or -not (Test-Path -LiteralPath $uninstaller)) { throw 'Registered uninstaller is outside the test install or missing' }
    Write-Host ('acceptance: uninstall remove_models=' + $Remove + ' executable=' + [IO.Path]::GetFileName($uninstaller))
    Invoke-Checked $uninstaller @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/REMOVEMODELS='+$Remove))
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
& (Join-Path $repo '.venv/Scripts/python.exe') (Join-Path $PSScriptRoot 'check_installed_payload.py') $install --output (Join-Path $work 'installed-files.json')
if ($LASTEXITCODE -ne 0) { throw 'Installed file inventory failed' }
& (Join-Path $PSScriptRoot 'test_network_isolation.ps1') -Bundle $install -InstalledModels
if ($LASTEXITCODE -ne 0) { throw 'Installed WFP self-test failed' }
& (Join-Path $repo '.venv/Scripts/python.exe') (Join-Path $PSScriptRoot 'check_pe_imports.py') (Join-Path $install 'dusty') --native (Join-Path $install 'bin') --output (Join-Path $work 'installed-pe.json')
if ($LASTEXITCODE -ne 0) { throw 'Installed PE import gate failed' }
Uninstall-App 'no'
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
@{silent_per_user_install='passed';installer_download_tiny_and_vad='passed';current_installer_fresh_download_wfp='passed';installed_wfp='passed';two_distinct_versions=$twoVersions;upgrade_models_preserved_with_downloader_blocked='passed';uninstall_keep_models='passed';uninstall_remove_models='passed';normal_cancel_removes_partial='passed';preserved_legacy_destination='passed';user_outputs_unchanged=$true} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $work 'summary.json') -Encoding utf8NoBOM
