# Child-process diagnostics for the disposable offline audit runner.
# Never emit arbitrary child output: it may contain paths or transcript text.
function Get-SafeOfflineTail([string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) { return '[empty]' }
    $lines = @($Text -split "`r?`n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    $tail = @($lines | Select-Object -Last 6)
    $safe = foreach ($line in $tail) {
        if ($line -cmatch '^FIXTURE_STATUS=(FAILED|OK)$') {
            $Matches[0]
        } elseif ($line -cmatch '^\s*(RuntimeError|ValueError|OSError|PermissionError|FileNotFoundError|TimeoutError|NetworkBlockedError|FetchError|SystemExit):') {
            "$($Matches[1]):[redacted]"
        } else {
            '[redacted]'
        }
    }
    return ($safe -join ' | ')
}

function Invoke-TestPython([string[]]$Arguments, [string]$Executable = $pythonPath, [int[]]$AllowedExitCodes = @(0)) {
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
    if (-not $process.WaitForExit(180000)) {
        $process.Kill($true)
        throw 'Offline process timed out'
    }
    $stdout = $outTask.Result
    $stderr = $errTask.Result
    $code = $process.ExitCode
    $process.Dispose()
    if ($code -notin $AllowedExitCodes) {
        $name = [IO.Path]::GetFileName($Executable)
        if (@('python.exe', 'dusty.exe', 'dusty-fetch.exe', 'whisper-cli.exe', 'ffmpeg.exe', 'ffprobe.exe') -cnotcontains $name) {
            $name = '[other process]'
        }
        $outTail = Get-SafeOfflineTail $stdout
        $errTail = Get-SafeOfflineTail $stderr
        throw "Offline process failed process=$name exit_code=$code stdout_tail=$outTail stderr_tail=$errTail"
    }
    return $stdout.Trim()
}
