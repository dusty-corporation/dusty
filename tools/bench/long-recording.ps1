param([string]$Bundle = 'dist/Dusty')

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$work = Join-Path $repo 'build/m6-long-recording'
if (Test-Path -LiteralPath (Join-Path $work 'cpu')) { throw 'Refusing to overwrite an existing long-recording run' }
New-Item -ItemType Directory -Path $work -Force | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $work 'input.json'))) {
$bundlePath = (Resolve-Path -LiteralPath $Bundle).Path
Copy-Item -LiteralPath $bundlePath -Destination (Join-Path $work 'bundle') -Recurse
$bundlePath = Join-Path $work 'bundle'
$audio = Join-Path $work 'long.wav'
$decoded = Join-Path $work 'source.wav'
& (Join-Path $bundlePath 'bin/ffmpeg/ffmpeg.exe') -nostdin -hide_banner -loglevel error -protocol_whitelist file,pipe -i (Join-Path $repo 'tests/fixtures/audio/bench/swineherd.mp3') -vn -ac 1 -ar 16000 -c:a pcm_s16le -f wav $decoded
if ($LASTEXITCODE -ne 0) { throw 'Public-domain source decode failed' }
& (Join-Path $repo '.venv/Scripts/python.exe') -c @'
import sys, wave, json
from pathlib import Path
root=Path(sys.argv[1])
with wave.open(str(root/'source.wav'),'rb') as source:
    frames=source.readframes(source.getnframes())
    with wave.open(str(root/'long.wav'),'wb') as target:
        target.setparams(source.getparams())
        for _ in range(12): target.writeframesraw(frames)
    duration=source.getnframes()/source.getframerate()*12
assert duration >= 7200
(root/'input.json').write_text(json.dumps({'duration_sec':duration,'repetitions':12,'source':'LibriVox Swineherd public-domain fixture'},indent=2))
'@ $work
if ($LASTEXITCODE -ne 0) { throw 'Long recording generation failed' }
}
$bundlePath = Join-Path $work 'bundle'
$audio = Join-Path $work 'long.wav'
$duration = (Get-Content -LiteralPath (Join-Path $work 'input.json') -Raw | ConvertFrom-Json).duration_sec
$hardware = @{
    cpu = @((Get-CimInstance Win32_Processor).Name)
    memory_bytes = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
    gpu = @((Get-CimInstance Win32_VideoController).Name)
}
$oldLocal = $env:LOCALAPPDATA
try {
    foreach ($case in @(@{model='small';backend='cpu'}, @{model='large-v3-turbo-q8_0';backend='vulkan'})) {
        $caseRoot = Join-Path $work $case.backend
        $env:LOCALAPPDATA = Join-Path $caseRoot 'profile'
        $models = Join-Path $env:LOCALAPPDATA 'Dusty/models'
        New-Item -ItemType Directory -Path $models -Force | Out-Null
        $manifest = Get-Content -LiteralPath (Join-Path $bundlePath 'resources/models.json') -Raw | ConvertFrom-Json
        $entries = @($manifest.models | Where-Object id -eq $case.model) + @($manifest.vad)
        foreach ($entry in $entries) {
            $source = Join-Path $repo ('build/models/' + $entry.file_name)
            if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw 'Model integrity failed' }
            Copy-Item -LiteralPath $source -Destination (Join-Path $models $entry.file_name)
        }
        $psi = [Diagnostics.ProcessStartInfo]::new()
        $psi.FileName = Join-Path $bundlePath 'dusty/dusty.exe'
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        foreach ($arg in @('--headless-batch', $audio, '--out', (Join-Path $caseRoot 'outputs'), '--model', $case.model, '--backend', $case.backend)) { [void]$psi.ArgumentList.Add($arg) }
        $process = [Diagnostics.Process]::new()
        $process.StartInfo = $psi
        $clock = [Diagnostics.Stopwatch]::StartNew()
        [void]$process.Start()
        $peak = [long]0
        $peakDisk = [long]0
        $observed = [Collections.Generic.HashSet[int]]::new()
        [void]$observed.Add($process.Id)
        do {
            $all = @(Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId)
            do {
                $changed = $false
                foreach ($p in $all) {
                    if ($observed.Contains([int]$p.ParentProcessId) -and $observed.Add([int]$p.ProcessId)) { $changed = $true }
                }
            } while ($changed)
            $sum = [long]0
            foreach ($processId in $observed) {
                $p = Get-Process -Id $processId -ErrorAction SilentlyContinue
                if ($p) { $sum += $p.WorkingSet64 }
            }
            $peak = [Math]::Max($peak, $sum)
            $files = @(Get-ChildItem -LiteralPath (Join-Path $env:LOCALAPPDATA 'Dusty/work') -Recurse -File -ErrorAction SilentlyContinue)
            $disk = [long](($files | Measure-Object -Property Length -Sum).Sum)
            $peakDisk = [Math]::Max($peakDisk, $disk)
        } while (-not $process.WaitForExit(1000))
        $clock.Stop()
        $state = Get-Content -LiteralPath (Join-Path $env:LOCALAPPDATA 'Dusty/state/queue.json') -Raw | ConvertFrom-Json
        $remaining = @(Get-ChildItem -LiteralPath (Join-Path $env:LOCALAPPDATA 'Dusty/work') -Recurse -File -ErrorAction SilentlyContinue).Count
        $result = @{model=$case.model; requested_backend=$case.backend; wall_sec=$clock.Elapsed.TotalSeconds; audio_sec=$duration; rtf=$clock.Elapsed.TotalSeconds/$duration; peak_tree_working_set_bytes=$peak; peak_work_bytes=$peakDisk; remaining_work_files=$remaining; exit_code=$process.ExitCode; jobs=$state.jobs | Select-Object status,backend_used,failure; hardware=$hardware; sample_method='CIM process descendants plus Get-Process working set; approximately 1 s plus CIM overhead; sampled peaks'}
        $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $caseRoot 'summary.json') -Encoding utf8NoBOM
        $result | Select-Object model,requested_backend,wall_sec,rtf,peak_tree_working_set_bytes,peak_work_bytes,remaining_work_files,exit_code | ConvertTo-Json -Compress
        if ($process.ExitCode -ne 0 -or $remaining -ne 0) { throw 'Long recording acceptance failed' }
    }
} finally { $env:LOCALAPPDATA = $oldLocal }
