param([string]$Python = '.venv/Scripts/python.exe', [string]$Bundle = '')

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
$pythonPrograms = @($pythonPath, $basePython | Select-Object -Unique)
if ($Bundle) {
    $bundlePath = (Resolve-Path -LiteralPath $Bundle).Path
    $gui = (Resolve-Path -LiteralPath (Join-Path $bundlePath 'dusty/dusty.exe')).Path
    $fetch = (Resolve-Path -LiteralPath (Join-Path $bundlePath 'dusty-fetch/dusty-fetch.exe')).Path
    $guiPrograms = @($gui)
    $fetchPrograms = @($fetch)
    $guiArguments = @('--check-model-download', '--model', 'tiny')
} else {
    $gui = $pythonPath
    $guiPrograms = $pythonPrograms
    $fetchPrograms = $pythonPrograms
    $guiArguments = @('-m', 'dusty', '--check-model-download', '--model', 'tiny')
}
$runId = [guid]::NewGuid().ToString('N')
$work = Join-Path $repo "build/model-download-$runId"
New-Item -ItemType Directory -Path $work | Out-Null
$snapshot = Join-Path $work 'audit-policy.csv'
$rules = [Collections.Generic.List[string]]::new()
$oldLocal = $env:LOCALAPPDATA
$oldQpa = $env:QT_QPA_PLATFORM
$savedAudit = $false

function Invoke-AuditProcess([string]$Executable, [string[]]$Arguments) {
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $Executable
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
    if (-not $process.WaitForExit(210000)) {
        $process.Kill($true)
        throw 'Model Manager process timed out'
    }
    $stdout = $outTask.Result
    $null = $errTask.Result
    $code = $process.ExitCode
    $process.Dispose()
    if ($code -ne 0) { throw "Model Manager process failed exit_code=$code" }
    return $stdout.Trim()
}

function Read-DownloadEvents([datetime]$Since) {
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
    foreach ($program in $pythonPrograms) {
        $name = "Dusty-Download-Control-$runId-$($rules.Count)"
        New-NetFirewallRule -Name $name -DisplayName $name -Direction Outbound -Action Block -Profile Any -Program $program | Out-Null
        $rules.Add($name)
    }
    $began = Get-Date
    $controlMarker = (Get-WinEvent -LogName Security -MaxEvents 1).RecordId
    $controlPid = [long](Invoke-AuditProcess -Executable $pythonPath -Arguments @('tests/offline/network_control.py'))
    $calibrated = $false
    for ($attempt = 0; $attempt -lt 10; $attempt++) {
        $events = Read-DownloadEvents $began
        $matched = @(Get-DustyConnectionEvents -Events $events -Programs $pythonPrograms -AfterRecordId $controlMarker)
        if (@($matched | Where-Object { $_.ProcessId -eq $controlPid -and $_.EventId -eq 5157 }).Count) {
            $calibrated = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $calibrated) { throw 'WFP control did not produce a blocked-connection audit event' }
    foreach ($name in $rules) { Remove-NetFirewallRule -Name $name }
    $rules.Clear()
    # Source GUI/fetch share a Python image, so this phase audits actual PIDs.
    # The separate existing offline test blocks Python during processing.
    if ($Bundle) {
        $name = "Dusty-Download-GUI-$runId"
        New-NetFirewallRule -Name $name -DisplayName $name -Direction Outbound -Action Block -Profile Any -Program $gui | Out-Null
        $rules.Add($name)
    }
    $marker = (Get-WinEvent -LogName Security -MaxEvents 1).RecordId
    $env:LOCALAPPDATA = Join-Path $work 'user'
    $env:QT_QPA_PLATFORM = 'offscreen'
    $null = Invoke-AuditProcess -Executable $gui -Arguments ($guiArguments + @('--out', $work))
    $result = Get-Content -LiteralPath (Join-Path $work 'download-result.json') -Raw | ConvertFrom-Json
    if (-not $result.verified -or -not $result.consent_confirmed -or -not $result.guard_installed) { throw 'Model Manager completion/guard evidence missing' }
    $fetchPids = @($result.fetch_pids | ForEach-Object { [long]$_ } | Select-Object -Unique)
    if (-not $fetchPids.Count -or $result.gui_pid -in $fetchPids -or [long]$result.gui_pid -le 0) { throw 'GUI and downloader PID attribution is invalid' }
    Start-Sleep -Seconds 3
    $events = Read-DownloadEvents $began
    $guiMatched = @(Get-DustyConnectionEvents -Events $events -Programs $guiPrograms -AfterRecordId $marker)
    $guiEvents = @($guiMatched | Where-Object { $Bundle -or $_.ProcessId -eq [long]$result.gui_pid })
    $fetchMatched = @(Get-DustyConnectionEvents -Events $events -Programs $fetchPrograms -AfterRecordId $marker)
    $allowed = @($fetchMatched | Where-Object { $_.ProcessId -in $fetchPids -and $_.EventId -eq 5156 })
    $blocked = @($fetchMatched | Where-Object { $_.ProcessId -in $fetchPids -and $_.EventId -eq 5157 })
    $summary = @{packaged=[bool]$Bundle; calibration_blocked_event=$true; model_manager='passed'; verified=$true;
                 gui_connection_events=$guiEvents.Count; fetch_allowed_events=$allowed.Count; fetch_blocked_events=$blocked.Count}
    $summary | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $work 'summary.json') -Encoding utf8
    if ($guiEvents.Count) { throw "S0: gui_connection_events=$($guiEvents.Count)" }
    if (-not $allowed.Count -or $blocked.Count) { throw "Downloader audit failed: allowed=$($allowed.Count) blocked=$($blocked.Count)" }
    "Model Manager WFP passed; gui_connection_events=0; fetch_allowed_events=$($allowed.Count); fetch_blocked_events=0"
} finally {
    foreach ($name in $rules) { Remove-NetFirewallRule -Name $name }
    if ($savedAudit) {
        & auditpol /restore "/file:$snapshot" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Audit policy restoration failed' }
    }
    $env:LOCALAPPDATA = $oldLocal
    $env:QT_QPA_PLATFORM = $oldQpa
}
