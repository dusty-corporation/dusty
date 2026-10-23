param([string]$Python = '.venv/Scripts/python.exe')

$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'This system-audit test runs only on the disposable GitHub runner' }
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Runner administrator access is required' }
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'wfp_events.ps1')
$pythonPath = (Resolve-Path -LiteralPath $Python).Path
$basePython = (& $pythonPath -c 'import sys; print(sys._base_executable)').Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve the Python base interpreter' }
$programs = @($pythonPath, $basePython)
foreach ($relative in @('cpu/whisper-cli.exe', 'vulkan/whisper-cli.exe', 'ffmpeg/ffmpeg.exe', 'ffmpeg/ffprobe.exe')) {
    $programs += (Resolve-Path -LiteralPath (Join-Path $repo "build/bin/$relative")).Path
}
$programs = @($programs | Select-Object -Unique)
$runId = [guid]::NewGuid().ToString('N')
$work = Join-Path $repo "build/offline-$runId"
New-Item -ItemType Directory -Path $work | Out-Null
$snapshot = Join-Path $work 'audit-policy.csv'
$rules = [Collections.Generic.List[string]]::new()
$oldLocal = $env:LOCALAPPDATA
$oldQpa = $env:QT_QPA_PLATFORM
$savedAudit = $false

function Invoke-TestPython([string[]]$Arguments) {
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $pythonPath
    $psi.WorkingDirectory = $repo
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    foreach ($argument in $Arguments) { [void]$psi.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $psi
    [void]$process.Start()
    $outTask = $process.StandardOutput.ReadToEndAsync()
    $errTask = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit(180000)) {
        $process.Kill($true)
        throw 'Offline process timed out'
    }
    $stdout = $outTask.Result
    $null = $errTask.Result
    $code = $process.ExitCode
    $process.Dispose()
    if ($code -ne 0) { throw "Offline process failed exit_code=$code" }
    return $stdout.Trim()
}

function Read-ConnectionEvents([datetime]$Since) {
    try {
        return @(Get-WinEvent -FilterHashtable @{LogName='Security'; Id=5156,5157; StartTime=$Since} -ErrorAction Stop)
    } catch {
        if ($_.FullyQualifiedErrorId -like 'NoMatchingEventsFound*') { return @() }
        throw 'Security event log could not be queried'
    }
}

try {
    & auditpol /backup "/file:$snapshot" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Audit policy backup failed' }
    $savedAudit = $true
    & auditpol /set '/subcategory:{0CCE9226-69AE-11D9-BED3-505054503030}' /success:enable /failure:enable | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'WFP auditing could not be enabled' }
    $index = 0
    foreach ($program in $programs) {
        $name = "Dusty-CI-$runId-$index"
        New-NetFirewallRule -Name $name -DisplayName $name -Direction Outbound -Action Block -Profile Any -Program $program | Out-Null
        $rules.Add($name)
        $index++
    }
    $began = Get-Date
    $controlMarker = (Get-WinEvent -LogName Security -MaxEvents 1).RecordId
    $controlPid = [long](Invoke-TestPython -Arguments @('tests/offline/network_control.py'))
    $calibrated = $false
    for ($attempt = 0; $attempt -lt 10; $attempt++) {
        $events = Read-ConnectionEvents $began
        $matched = @(Get-DustyConnectionEvents -Events $events -Programs $programs -AfterRecordId $controlMarker)
        if (@($matched | Where-Object { $_.ProcessId -eq $controlPid -and $_.EventId -eq 5157 }).Count) {
            $calibrated = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $calibrated) { throw 'WFP control did not produce a blocked-connection audit event' }
    $marker = (Get-WinEvent -LogName Security -MaxEvents 1).RecordId
    $env:LOCALAPPDATA = Join-Path $work 'user'
    $selftest = Invoke-TestPython -Arguments @('-m', 'dusty', '--self-test', '--backend', 'auto', '--model', 'tiny')
    if ($selftest -ne 'OK') { throw 'Offline self-test did not report success' }
    $batch = Invoke-TestPython -Arguments @('-m', 'dusty', '--headless-batch', 'tests/fixtures/audio/formats/jfk.wav', '--out', (Join-Path $work 'outputs'), '--backend', 'auto', '--model', 'tiny')
    $expectedBatch = "added=1 unsupported=0 duplicates=0`ndone OK"
    if (($batch -replace "`r`n", "`n") -cne $expectedBatch) { throw 'Offline batch did not report success' }
    $env:QT_QPA_PLATFORM = 'offscreen'
    $gui = Invoke-TestPython -Arguments @('tests/offline/gui_batch.py', (Join-Path $work 'gui-outputs'))
    if ($gui -cne 'gui batch passed') { throw 'Offline GUI batch did not report success' }
    Start-Sleep -Seconds 3
    $events = Read-ConnectionEvents $began
    $violations = @(Get-DustyConnectionEvents -Events $events -Programs $programs -AfterRecordId $marker -ExcludeProcessId $controlPid)
    $summary = @{calibration_blocked_event=$true; selftest='passed'; batch='passed'; gui='passed'; connection_events=$violations.Count}
    $summary | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $work 'summary.json') -Encoding utf8
    if ($violations.Count) { throw "S0: processing_connection_events=$($violations.Count)" }
    'WFP calibration passed; selftest passed; batch passed; gui passed; connection_events=0'
} finally {
    foreach ($name in $rules) { Remove-NetFirewallRule -Name $name }
    if ($savedAudit) {
        & auditpol /restore "/file:$snapshot" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Audit policy restoration failed' }
    }
    $env:LOCALAPPDATA = $oldLocal
    $env:QT_QPA_PLATFORM = $oldQpa
}
