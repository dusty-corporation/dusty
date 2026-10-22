param(
    [string]$Root,
    [string]$BinDir,
    [int]$Threads = 4,
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = 'Stop'
if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path }
if (-not $BinDir) { $BinDir = Join-Path $Root 'build/bin' }
$BinDir = (Resolve-Path -LiteralPath $BinDir).Path
if ($Threads -lt 1) { throw 'Threads must be positive' }
if ($TimeoutSeconds -lt 1) { throw 'TimeoutSeconds must be positive' }
$audio = Join-Path $Root 'tests/fixtures/audio/formats/jfk.wav'
$model = Join-Path $Root 'build/models/ggml-tiny.bin'
if (-not (Test-Path -LiteralPath $audio)) { throw 'Public JFK fixture is missing' }
if (-not (Test-Path -LiteralPath $model)) { throw 'Pinned tiny model is missing' }
if ((Get-FileHash -LiteralPath $model -Algorithm SHA256).Hash -ne 'a38bcb31dcd68cf7d9a630e2148ccf0656f95ac87c5bcbc4064a689f383b2059') {
    throw 'Tiny model hash does not match the published pin'
}
if ((Get-FileHash -LiteralPath $audio -Algorithm SHA256).Hash -ne '59dfb9a4acb36fe2a2affc14bacbee2920ff435cb13cc314a08c13f66ba7860e') {
    throw 'Public fixture hash does not match the pin'
}
'startup_probe engine=v1.9.5 model=tiny threads={0} runs_per_backend=5 vad=off' -f $Threads

foreach ($backend in @('cpu', 'vulkan')) {
    $engine = Join-Path $BinDir "$backend/whisper-cli.exe"
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
        $actualVulkan = $false
        $variant = 'unknown'
        $readTask = $process.StandardError.ReadLineAsync()
        while ($true) {
            if (-not $readTask.Wait(100)) {
                if ($clock.Elapsed.TotalSeconds -gt $TimeoutSeconds) {
                    $process.Kill($true)
                    $process.WaitForExit()
                    $process.Dispose()
                    throw 'Engine exceeded the per-run timeout'
                }
                continue
            }
            $line = $readTask.Result
            if ($null -eq $line) { break }
            if ($line -match 'whisper_backend_init_gpu: using Vulkan\d+ backend') { $actualVulkan = $true }
            if ($line -match 'load_backend: loaded CPU backend from .*ggml-cpu-([a-z0-9]+)\.dll') { $variant = $Matches[1] }
            if ($null -eq $firstProgress -and $line -match 'whisper_print_progress_callback: progress =') {
                $firstProgress = $clock.Elapsed.TotalSeconds
            }
            if ($line -match 'whisper_print_timings:\s*(load|mel|sample|encode|decode|batchd|prompt|total) time =\s*([0-9.]+) ms') {
                $numbers[$Matches[1]] = [double]::Parse($Matches[2], [Globalization.CultureInfo]::InvariantCulture)
            }
            $readTask = $process.StandardError.ReadLineAsync()
        }
        $process.WaitForExit()
        $clock.Stop()
        $null = $stdoutTask.Result
        if ($process.ExitCode -ne 0) { throw "Engine failed with exit code $($process.ExitCode)" }
        if ($backend -eq 'vulkan' -and -not $actualVulkan) { throw 'The Vulkan run did not select Vulkan' }
        foreach ($required in @('load', 'encode', 'decode', 'total')) {
            if (-not $numbers.ContainsKey($required)) { throw 'A required engine timing is missing' }
        }
        $first = if ($null -eq $firstProgress) { 'NA' } else { $firstProgress.ToString('F3', [Globalization.CultureInfo]::InvariantCulture) }
        $load = if ($numbers.ContainsKey('load')) { $numbers['load'] } else { 0 }
        $encode = if ($numbers.ContainsKey('encode')) { $numbers['encode'] } else { 0 }
        $decode = if ($numbers.ContainsKey('decode')) { $numbers['decode'] } else { 0 }
        $total = if ($numbers.ContainsKey('total')) { $numbers['total'] } else { 0 }
        $row = '{0} run={1} first_progress_sec={2} load_ms={3:F1} encode_ms={4:F1} decode_ms={5:F1} engine_total_ms={6:F1} wall_sec={7:F3} cpu_variant={8}'
        [string]::Format([Globalization.CultureInfo]::InvariantCulture, $row, @(
            $backend, $run, $first, $load, $encode, $decode, $total, $clock.Elapsed.TotalSeconds, $variant
        ))
        $process.Dispose()
    }
}
