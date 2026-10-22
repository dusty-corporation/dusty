param(
    [string]$Root,
    [int]$Threads = 4
)

$ErrorActionPreference = 'Stop'
if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path }
if ($Threads -lt 1) { throw 'Threads must be positive' }
$audio = Join-Path $Root 'tests/fixtures/audio/formats/jfk.wav'
$model = Join-Path $Root 'build/models/ggml-tiny.bin'
if (-not (Test-Path -LiteralPath $audio)) { throw 'Public JFK fixture is missing' }
if (-not (Test-Path -LiteralPath $model)) { throw 'Pinned tiny model is missing' }

foreach ($backend in @('cpu', 'vulkan')) {
    $engine = Join-Path $Root "build/bin/$backend/whisper-cli.exe"
    if (-not (Test-Path -LiteralPath $engine)) { throw 'Pinned engine is missing' }
    for ($run = 1; $run -le 5; $run++) {
        $psi = [Diagnostics.ProcessStartInfo]::new()
        $psi.FileName = $engine
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        foreach ($arg in @('-m', $model, '-f', $audio, '-l', 'en', '-t', [string]$Threads, '-pp')) {
            [void]$psi.ArgumentList.Add($arg)
        }
        if ($backend -eq 'cpu') { [void]$psi.ArgumentList.Add('-ng') }
        $process = [Diagnostics.Process]::new()
        $process.StartInfo = $psi
        $clock = [Diagnostics.Stopwatch]::StartNew()
        if (-not $process.Start()) { throw 'Engine did not start' }
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $firstProgress = $null
        $numbers = @{}
        while ($null -ne ($line = $process.StandardError.ReadLine())) {
            if ($null -eq $firstProgress -and $line -match 'whisper_print_progress_callback: progress =') {
                $firstProgress = $clock.Elapsed.TotalSeconds
            }
            if ($line -match 'whisper_print_timings:\s*(load|mel|sample|encode|decode|batchd|prompt|total) time =\s*([0-9.]+) ms') {
                $numbers[$Matches[1]] = [double]::Parse($Matches[2], [Globalization.CultureInfo]::InvariantCulture)
            }
        }
        $process.WaitForExit()
        $clock.Stop()
        $null = $stdoutTask.Result
        if ($process.ExitCode -ne 0) { throw "Engine failed with exit code $($process.ExitCode)" }
        $first = if ($null -eq $firstProgress) { 'NA' } else { $firstProgress.ToString('F3', [Globalization.CultureInfo]::InvariantCulture) }
        $load = if ($numbers.ContainsKey('load')) { $numbers['load'] } else { 0 }
        $encode = if ($numbers.ContainsKey('encode')) { $numbers['encode'] } else { 0 }
        $decode = if ($numbers.ContainsKey('decode')) { $numbers['decode'] } else { 0 }
        $total = if ($numbers.ContainsKey('total')) { $numbers['total'] } else { 0 }
        '{0} run={1} first_progress_sec={2} load_ms={3:F1} encode_ms={4:F1} decode_ms={5:F1} engine_total_ms={6:F1} wall_sec={7:F3}' -f `
            $backend, $run, $first, $load, $encode, $decode, $total, $clock.Elapsed.TotalSeconds
        $process.Dispose()
    }
}
