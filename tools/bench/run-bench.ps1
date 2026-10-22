param(
    [Parameter(Mandatory = $true)][string]$AudioPath,
    [ValidateSet('cpu', 'vulkan')][string]$Backend,
    [Parameter(Mandatory = $true)][string]$Machine,
    [string]$Threads = '4',
    [switch]$PublicReference,
    [switch]$Quick,
    [ValidateSet('tiny-f16', 'small-f16', 'large-v3-turbo-q5_0', 'large-v3-q5_0')]
    [string]$SweepModel
)

$ErrorActionPreference = 'Stop'
if ($SweepModel -and -not $Quick) { throw 'SweepModel requires Quick mode' }
$threadValues = @()
foreach ($piece in $Threads.Split(',')) {
    $value = $piece.Trim()
    if ($value -notmatch '^[1-9][0-9]*$') { throw 'Threads must be positive comma-separated integers' }
    $threadValues += [int]$value
}
if (($threadValues | Select-Object -Unique).Count -ne $threadValues.Count) {
    throw 'Threads must not repeat a value'
}
if ($Quick -and $threadValues.Count -gt 1 -and -not $SweepModel) {
    throw 'Use SweepModel to limit a Quick thread sweep to one model'
}
if ($Quick) {
    if ($PSBoundParameters.ContainsKey('Backend')) { throw 'Quick mode runs both backends; omit Backend' }
    $backends = @('cpu', 'vulkan')
} else {
    if (-not $PSBoundParameters.ContainsKey('Backend')) { throw 'Backend is required for a full run' }
    $backends = @($Backend)
}
$kit = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (Test-Path (Join-Path $kit 'models.json')) {
    $root = $kit
} else {
    $root = (Get-Location).Path
}
$manifest = Get-Content (Join-Path $root 'models.json') -Raw | ConvertFrom-Json
$probe = Join-Path $root 'bin/ffmpeg/ffprobe.exe'
$warmup = Join-Path $root 'audio/warmup.wav'
foreach ($selectedBackend in $backends) {
    if (-not (Test-Path (Join-Path $root "bin/$selectedBackend/whisper-cli.exe"))) {
        throw 'Engine binary is missing'
    }
}
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
$sample = if ($PublicReference) { 'public' } else { 'private' }
$runMode = if ($SweepModel) { 'quick_sweep' } elseif ($Quick) { 'quick' } else { 'full' }
$modeSuffix = if ($SweepModel) {
    "-quick-sweep-$SweepModel-t$($threadValues -join '_')"
} elseif ($Quick) { '-quick' } else { '' }
$jsonMode = if ($SweepModel) { 'quick-sweep-' } elseif ($Quick) { 'quick-' } else { '' }
$models = if ($Quick) {
    $ids = if ($SweepModel) { @($SweepModel) } else {
        @('tiny-f16', 'small-f16', 'large-v3-turbo-q5_0', 'large-v3-q5_0')
    }
    foreach ($id in $ids) {
        $match = @($manifest.models | Where-Object { $_.id -eq $id })
        if ($match.Count -ne 1) { throw "Quick model is missing from manifest: $id" }
        $match[0]
    }
} else { @($manifest.models) }
foreach ($model in $models) {
    $modelPath = Join-Path $root "models/$($model.file_name)"
    if (-not (Test-Path $modelPath)) { throw "Missing benchmark model $($model.id)" }
    $modelHash = (Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($modelHash -ne $model.sha256) { throw "Model hash mismatch for $($model.id)" }
}

# Check every planned output before running any model. Existing summaries and
# public JSON are never overwritten, including when a second backend is run.
foreach ($selectedBackend in $backends) {
    $stem = "$safeMachine-$stamp-$sample-$selectedBackend$modeSuffix"
    foreach ($extension in @('.csv', '.md')) {
        if (Test-Path (Join-Path $results "$stem$extension")) { throw 'Benchmark summary already exists' }
    }
    if ($PublicReference) {
        foreach ($model in $models) {
            foreach ($threadCount in $threadValues) {
                $jsonName = "public-$safeMachine-$jsonMode$($model.id)-$selectedBackend-t$threadCount.json"
                if (Test-Path (Join-Path $results $jsonName)) { throw 'Public benchmark JSON already exists' }
            }
        }
    }
}

foreach ($selectedBackend in $backends) {
    $Backend = $selectedBackend
    $engine = Join-Path $root "bin/$Backend/whisper-cli.exe"
    $stem = "$safeMachine-$stamp-$sample-$Backend$modeSuffix"
    $csv = Join-Path $results "$stem.csv"
    $summary = Join-Path $results "$stem.md"
    $rows = @()
    foreach ($model in $models) {
        $modelPath = Join-Path $root "models/$($model.file_name)"
        foreach ($threadCount in $threadValues) {
            $null = Invoke-Engine -ModelPath $modelPath -InputPath $warmup -ThreadCount $threadCount -OutputStem ''
            $outputStem = ''
            if ($PublicReference) {
                $outputStem = Join-Path $results "public-$safeMachine-$jsonMode$($model.id)-$Backend-t$threadCount"
            }
            $run = Invoke-Engine -ModelPath $modelPath -InputPath $AudioPath -ThreadCount $threadCount -OutputStem $outputStem
            if ($PublicReference) {
                $jsonPath = "$outputStem.json"
                $publicJson = Get-Content -LiteralPath $jsonPath -Raw | ConvertFrom-Json
                $publicJson.params.model = '<redacted>'
                $safeJson = $publicJson | ConvertTo-Json -Depth 100
                [IO.File]::WriteAllText($jsonPath, $safeJson, [Text.UTF8Encoding]::new($false))
            }
            $rows += [pscustomobject]@{
                machine = $safeMachine
                sample = $sample
                run_mode = $runMode
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
    $lines = @('# Benchmark summary', '', '| Model | Quant | Requested | Actual | CPU variant | Threads | Duration s | Wall s | RTF | Peak MB |', '| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |')
    foreach ($row in $rows) {
        $lines += "| $($row.model) | $($row.quantization) | $($row.backend_requested) | $($row.backend_actual) | $($row.cpu_variant) | $($row.threads) | $($row.audio_duration_s) | $($row.wall_time_s) | $($row.rtf) | $($row.peak_memory_mb) |"
    }
    $lines | Set-Content -Path $summary -Encoding UTF8
}
Write-Output 'Benchmark CSV and Markdown summaries written to results folder.'
