param(
    [Parameter(Mandatory = $true)][string]$AudioPath,
    [Parameter(Mandatory = $true)][ValidateSet('cpu', 'vulkan')][string]$Backend,
    [Parameter(Mandatory = $true)][string]$Machine,
    [int[]]$Threads = @(4),
    [switch]$PublicReference
)

$ErrorActionPreference = 'Stop'
$kit = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (Test-Path (Join-Path $kit 'models.json')) {
    $root = $kit
} else {
    $root = (Get-Location).Path
}
$manifest = Get-Content (Join-Path $root 'models.json') -Raw | ConvertFrom-Json
$engine = Join-Path $root "bin/$Backend/whisper-cli.exe"
$probe = Join-Path $root 'bin/ffmpeg/ffprobe.exe'
$warmup = Join-Path $root 'audio/warmup.wav'
if (-not (Test-Path $engine)) { throw 'Engine binary is missing' }
if (-not (Test-Path $probe)) { throw 'FFprobe binary is missing' }
if (-not (Test-Path $warmup)) { throw 'Warm-up fixture is missing' }
if (-not (Test-Path $AudioPath)) { throw 'Input audio is missing' }

$probeJson = & $probe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels -show_entries format=duration -of json $AudioPath 2>$null
if ($LASTEXITCODE -ne 0) { throw 'Cannot probe input audio' }
$audioInfo = $probeJson | ConvertFrom-Json
if (-not $audioInfo.streams -or -not $audioInfo.format.duration) {
    throw 'Cannot probe input audio'
}
$stream = $audioInfo.streams[0]
if ($stream.codec_name -ne 'pcm_s16le' -or [int]$stream.sample_rate -ne 16000 -or [int]$stream.channels -ne 1) {
    throw 'Input must be 16 kHz mono PCM s16le WAV. Convert it privately before benchmarking.'
}
$duration = [double]::Parse($audioInfo.format.duration, [Globalization.CultureInfo]::InvariantCulture)
if ($duration -le 0) { throw 'Input duration must be positive' }

function Invoke-Engine {
    param([string]$ModelPath, [string]$InputPath, [int]$ThreadCount, [string]$OutputStem)
    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName = $engine
    $args = @('-m', ('"' + $ModelPath + '"'), '-f', ('"' + $InputPath + '"'), '-l', 'en', '-t', $ThreadCount, '-pp')
    if ($Backend -eq 'cpu') { $args += '-ng' }
    if ($OutputStem) { $args += @('-ojf', '-of', ('"' + $OutputStem + '"')) }
    $psi.Arguments = $args -join ' '
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $psi
    $clock = [Diagnostics.Stopwatch]::StartNew()
    if (-not $process.Start()) { throw 'Engine process did not start' }
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $peak = [long]0
    while (-not $process.WaitForExit(100)) {
        $process.Refresh()
        try { $peak = [Math]::Max($peak, $process.WorkingSet64) } catch { }
    }
    $clock.Stop()
    $process.Refresh()
    try { $peak = [Math]::Max($peak, $process.PeakWorkingSet64) } catch { }
    $stderr = $stderrTask.Result
    $null = $stdoutTask.Result
    if ($process.ExitCode -ne 0) { throw "Engine exited with $($process.ExitCode)" }
    $actual = if ($stderr -match 'whisper_backend_init_gpu: using Vulkan\d+ backend') {
        'vulkan'
    } elseif ($stderr -match 'whisper_backend_init_gpu: (no GPU found|device \d+: CPU)') {
        'cpu'
    } else {
        throw 'Could not identify the backend from engine output'
    }
    $variant = if ($stderr -match 'load_backend: loaded CPU backend from [^\r\n]*ggml-cpu-([a-z0-9]+)\.dll') {
        $Matches[1]
    } else { 'unknown' }
    return @{ seconds = $clock.Elapsed.TotalSeconds; peak = $peak; actual = $actual; variant = $variant }
}

$results = Join-Path $root 'results'
New-Item -ItemType Directory -Force $results | Out-Null
$stamp = Get-Date -Format yyyy-MM-dd
$safeMachine = $Machine -replace '[^A-Za-z0-9_]', '_'
$csv = Join-Path $results "$safeMachine-$stamp-$Backend.csv"
$rows = @()
foreach ($model in $manifest.models) {
    $modelPath = Join-Path $root "models/$($model.file_name)"
    if (-not (Test-Path $modelPath)) { throw "Missing benchmark model $($model.id)" }
    $modelHash = (Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($modelHash -ne $model.sha256) { throw "Model hash mismatch for $($model.id)" }
    foreach ($threadCount in $Threads) {
        if ($threadCount -lt 1) { throw 'Thread count must be positive' }
        $null = Invoke-Engine -ModelPath $modelPath -InputPath $warmup -ThreadCount $threadCount -OutputStem ''
        $outputStem = ''
        if ($PublicReference) {
            $outputStem = Join-Path $results "public-$safeMachine-$($model.id)-$Backend-t$threadCount"
        }
        $run = Invoke-Engine -ModelPath $modelPath -InputPath $AudioPath -ThreadCount $threadCount -OutputStem $outputStem
        $rows += [pscustomobject]@{
            machine = $safeMachine
            sample = $(if ($PublicReference) { 'public' } else { 'private' })
            model = $model.id
            quantization = $model.quantization
            backend_requested = $Backend
            backend_actual = $run.actual
            cpu_variant = $run.variant
            threads = $threadCount
            audio_duration_s = [Math]::Round($duration, 3)
            wall_time_s = [Math]::Round($run.seconds, 3)
            rtf = [Math]::Round($run.seconds / $duration, 4)
            peak_memory_mb = [Math]::Round($run.peak / 1MB, 1)
        }
    }
}
$rows | Export-Csv -Path $csv -NoTypeInformation -Encoding UTF8
$summary = Join-Path $results "$safeMachine-$stamp-$Backend.md"
$lines = @('# Benchmark summary', '', '| Model | Quant | Requested | Actual | CPU variant | Threads | Duration s | Wall s | RTF | Peak MB |', '| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |')
foreach ($row in $rows) {
    $lines += "| $($row.model) | $($row.quantization) | $($row.backend_requested) | $($row.backend_actual) | $($row.cpu_variant) | $($row.threads) | $($row.audio_duration_s) | $($row.wall_time_s) | $($row.rtf) | $($row.peak_memory_mb) |"
}
$lines | Set-Content -Path $summary -Encoding UTF8
Write-Output 'Benchmark CSV and Markdown summary written to results folder.'
