$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'test_wfp_events.ps1')
. (Join-Path $PSScriptRoot '../../tools/installer_download_audit.ps1')
function Start-Sleep { param($Seconds) }
function Read-InstallerEvents { param($Since); return $script:sample }
$work = Join-Path $PSScriptRoot '../../build/installer-parser-test'
New-Item -ItemType Directory -Path $work -Force | Out-Null
$state = @{began=(Get-Date);marker=10}
$script:sample = @(
    (New-TestEvent 5156 11 '1' '\device\harddiskvolume2\app\dusty-fetch\dusty-fetch.exe'),
    (New-TestEvent 5157 9 '2' '\device\harddiskvolume2\old\dusty.exe')
)
Complete-InstallerAudit $state 'C:\build\Dusty-test.exe' $work
foreach ($name in @('Dusty-test.exe','Dusty-test.tmp','dusty.exe','whisper-cli.exe','ffmpeg.exe','ffprobe.exe')) {
    $script:sample = @(
        (New-TestEvent 5156 11 '1' '\device\harddiskvolume2\app\dusty-fetch\dusty-fetch.exe'),
        (New-TestEvent 5157 12 '2' ('\device\harddiskvolume2\temp\' + $name))
    )
    $rejected = $false
    try { Complete-InstallerAudit $state 'C:\build\Dusty-test.exe' $work }
    catch { if ($_.Exception.Message -notlike 'S0:*') { throw }; $rejected=$true }
    if (-not $rejected) { throw ('Installer audit missed prohibited image ' + $name) }
}
$script:sample = @()
$rejected = $false
try { Complete-InstallerAudit $state 'C:\build\Dusty-test.exe' $work }
catch { $rejected=$true }
if (-not $rejected) { throw 'Installer audit accepted missing downloader positive control' }
'Installer WFP parser negative checks passed'
