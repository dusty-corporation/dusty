# CI-only audit window around the real installer download and model-free probe.
. (Join-Path $PSScriptRoot 'wfp_events.ps1')

function Read-InstallerEvents([datetime]$Since) {
    try { return @(Get-WinEvent -FilterHashtable @{LogName='Security';Id=5156,5157;StartTime=$Since} -ErrorAction Stop) }
    catch { if ($_.FullyQualifiedErrorId -like 'NoMatchingEventsFound*') { return @() }; throw }
}

function Start-InstallerAudit([string]$Work) {
    if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Installer audit runs only on disposable CI' }
    $snapshot = Join-Path $Work ('download-audit-policy-' + [guid]::NewGuid().ToString('N') + '.csv')
    & auditpol /backup "/file:$snapshot" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Installer audit backup failed' }
    $state = @{snapshot=$snapshot;rules=@();began=(Get-Date)}
    try {
        & auditpol /set '/subcategory:{0CCE9226-69AE-11D9-BED3-505054503030}' /success:enable /failure:enable | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Installer WFP enable failed' }
        $python = (Resolve-Path '.venv/Scripts/python.exe').Path
        $base = (& $python -c 'import sys; print(sys._base_executable)').Trim()
        $programs = @($python,$base | Select-Object -Unique)
        foreach ($program in $programs) {
            $rule = 'Dusty-Setup-Control-' + [guid]::NewGuid().ToString('N')
            New-NetFirewallRule -Name $rule -DisplayName $rule -Direction Outbound -Action Block -Profile Any -Program $program | Out-Null
            $state.rules += $rule
        }
        $marker = (Get-WinEvent -LogName Security -MaxEvents 1).RecordId
        $pidValue = [long](& $python tests/offline/network_control.py)
        if ($LASTEXITCODE -ne 0) { throw 'Installer WFP control failed' }
        $calibrated = $false
        for ($attempt=0; $attempt -lt 10; $attempt++) {
            $matched = @(Get-DustyConnectionEvents -Events (Read-InstallerEvents $state.began) -Programs $programs -AfterRecordId $marker)
            if (@($matched | Where-Object { $_.ProcessId -eq $pidValue -and $_.EventId -eq 5157 }).Count) { $calibrated=$true; break }
            Start-Sleep -Seconds 1
        }
        if (-not $calibrated) { throw 'Installer WFP calibration produced no blocked event' }
        foreach ($rule in $state.rules) { Remove-NetFirewallRule -Name $rule }
        $state.rules = @()
        $state.marker = (Get-WinEvent -LogName Security -MaxEvents 1).RecordId
        return $state
    } catch { Stop-InstallerAudit $state; throw }
}

function Complete-InstallerAudit($State, [string]$Installer, [string]$Work) {
    Start-Sleep -Seconds 3
    $counts = @{installer=0;gui=0;native=0;fetch_allowed=0;fetch_blocked=0}
    $setupStem = [IO.Path]::GetFileNameWithoutExtension($Installer)
    foreach ($event in (Read-InstallerEvents $State.began)) {
        if ($event.RecordId -le $State.marker) { continue }
        [xml]$xml = $event.ToXml()
        $fields = @{}
        foreach ($field in $xml.Event.EventData.Data) { $fields[$field.Name]=$field.InnerText }
        $name = [IO.Path]::GetFileName([string]$fields.Application)
        if ($name -in @(($setupStem+'.exe'),($setupStem+'.tmp'))) { $counts.installer++ }
        elseif ($name -eq 'dusty.exe') { $counts.gui++ }
        elseif ($name -in @('whisper-cli.exe','ffmpeg.exe','ffprobe.exe')) { $counts.native++ }
        elseif ($name -eq 'dusty-fetch.exe') {
            if ($event.Id -eq 5156) { $counts.fetch_allowed++ } else { $counts.fetch_blocked++ }
        }
    }
    $counts.calibration_blocked_event = $true
    $counts.model_free_probe = 'passed'
    $counts | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Work 'download-wfp.json') -Encoding utf8NoBOM
    if ($counts.installer -or $counts.gui -or $counts.native) { throw 'S0: connection event during installer or probe processing' }
    if (-not $counts.fetch_allowed -or $counts.fetch_blocked) { throw 'Installer downloader audit missing allowed event or contains blocked event' }
    Write-Host ($counts | ConvertTo-Json -Compress)
}

function Stop-InstallerAudit($State) {
    foreach ($rule in $State.rules) { Remove-NetFirewallRule -Name $rule }
    & auditpol /restore "/file:$($State.snapshot)" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Installer audit restore failed' }
}
