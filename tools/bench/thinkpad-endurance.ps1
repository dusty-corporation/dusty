param(
    [Parameter(Mandatory)][string]$SourceMp3,
    [Parameter(Mandatory)][string]$Work,
    [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA 'Programs/Dusty'),
    [switch]$PrepareOnly
)

$ErrorActionPreference = 'Stop'
$Work = [IO.Path]::GetFullPath($Work)
$InstallRoot = [IO.Path]::GetFullPath($InstallRoot)
$expectedMp3 = '17d68d8940e92907f13e6e2bedc5f997fa1b41fa9fca9e0aefd89760f97175b6'
$expectedWave = '8455996fe6970d43828600d976712ab4b37c40b22863d4fa0031f4bc47921de3'
if ((Get-FileHash -LiteralPath $SourceMp3 -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedMp3) { throw 'Public source hash mismatch' }
New-Item -ItemType Directory -Path $Work -Force | Out-Null
$audio = Join-Path $Work 'long.wav'
if (-not (Test-Path -LiteralPath $audio)) {
    $decoded = Join-Path $Work 'source.wav'
    if (Test-Path -LiteralPath $decoded) { throw 'Existing decode found; choose a fresh work folder' }
    & (Join-Path $InstallRoot 'bin/ffmpeg/ffmpeg.exe') -nostdin -hide_banner -loglevel error -n -protocol_whitelist file,pipe -i $SourceMp3 -vn -ac 1 -ar 16000 -c:a pcm_s16le -f wav $decoded
    if ($LASTEXITCODE -ne 0) { throw 'Public source decode failed' }
    $inputStream = [IO.File]::OpenRead($decoded)
    $reader = [IO.BinaryReader]::new($inputStream)
    $target = $null
    try {
        if ([Text.Encoding]::ASCII.GetString($reader.ReadBytes(4)) -ne 'RIFF') { throw 'Not RIFF' }
        [void]$reader.ReadUInt32()
        if ([Text.Encoding]::ASCII.GetString($reader.ReadBytes(4)) -ne 'WAVE') { throw 'Not WAVE' }
        $offset = [long]0; $length = [long]0; $formatOk = $false
        while ($inputStream.Position + 8 -le $inputStream.Length) {
            $name = [Text.Encoding]::ASCII.GetString($reader.ReadBytes(4))
            $size = $reader.ReadUInt32(); $next = $inputStream.Position + $size + ($size % 2)
            if ($name -eq 'fmt ') {
                $formatOk = ($reader.ReadUInt16() -eq 1) -and ($reader.ReadUInt16() -eq 1) -and ($reader.ReadUInt32() -eq 16000)
                [void]$reader.ReadUInt32(); [void]$reader.ReadUInt16()
                $formatOk = $formatOk -and ($reader.ReadUInt16() -eq 16)
            }
            if ($name -eq 'data') { $offset = $inputStream.Position; $length = $size; break }
            $inputStream.Position = $next
        }
        if (-not $formatOk -or $length -ne 21120500) { throw 'Unexpected source PCM parameters/length' }
        $target = [IO.BinaryWriter]::new([IO.File]::Open($audio,[IO.FileMode]::CreateNew))
        $total = [uint32]($length * 12)
        $target.Write([Text.Encoding]::ASCII.GetBytes('RIFF')); $target.Write([uint32](36+$total))
        $target.Write([Text.Encoding]::ASCII.GetBytes('WAVEfmt ')); $target.Write([uint32]16)
        $target.Write([uint16]1); $target.Write([uint16]1); $target.Write([uint32]16000)
        $target.Write([uint32]32000); $target.Write([uint16]2); $target.Write([uint16]16)
        $target.Write([Text.Encoding]::ASCII.GetBytes('data')); $target.Write($total)
        $buffer = [byte[]]::new(65536)
        for ($repeat = 0; $repeat -lt 12; $repeat++) {
            $inputStream.Position = $offset; $remaining = $length
            while ($remaining -gt 0) {
                $count = $inputStream.Read($buffer,0,[int][Math]::Min($buffer.Length,$remaining))
                if ($count -le 0) { throw 'Truncated source PCM' }
                $target.Write($buffer,0,$count); $remaining -= $count
            }
        }
    } finally { if ($target) { $target.Dispose() }; $reader.Dispose() }
}
if ((Get-FileHash -LiteralPath $audio -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedWave) { throw 'Long WAV hash mismatch; keep evidence and use a fresh work folder' }
Write-Host 'Verified public audio: 7920.1875 seconds, SHA-256 matches desktop input'
if ($PrepareOnly) { exit 0 }

$exe = Join-Path $InstallRoot 'dusty/dusty.exe'
$data = Join-Path $env:LOCALAPPDATA 'Dusty'
$stateFile = Join-Path $data 'state/queue.json'
$workDir = Join-Path $data 'work'
if (Get-Process -Name dusty -ErrorAction SilentlyContinue) { throw 'Close Dusty before this test' }
if (Test-Path -LiteralPath $stateFile) { throw 'Use Tools > Clear history, then close Dusty before starting. No existing state is overwritten.' }
if (@(Get-ChildItem -LiteralPath $workDir -Force -ErrorAction SilentlyContinue).Count) { throw 'App work area is not empty; review in Dusty, do not delete unknown files' }
foreach ($case in @(@{id='large-v3-turbo-q8_0';backend='vulkan'},@{id='small';backend='cpu'})) {
    $resultDir = Join-Path $Work $case.backend
    if (Test-Path -LiteralPath $resultDir) { throw 'Refusing to overwrite an existing endurance result' }
    New-Item -ItemType Directory -Path $resultDir | Out-Null
    if (Test-Path -LiteralPath $stateFile) {
        $old = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
        if (@($old.jobs).Count -ne 1 -or $old.jobs[0].source -ne $audio -or $old.jobs[0].status -ne 'done') { throw 'Unrelated or unfinished app state appeared; refusing to overwrite it' }
    }
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $exe; $psi.UseShellExecute = $false; $psi.CreateNoWindow = $true
    foreach ($arg in @('--headless-batch',$audio,'--out',(Join-Path $resultDir 'transcripts'),'--model',$case.id,'--backend',$case.backend)) { [void]$psi.ArgumentList.Add($arg) }
    $process = [Diagnostics.Process]::new(); $process.StartInfo = $psi
    $clock = [Diagnostics.Stopwatch]::StartNew(); [void]$process.Start()
    $peakRam = [long]0; $peakWork = [long]0
    do {
        $tree = [Collections.Generic.HashSet[int]]::new(); [void]$tree.Add($process.Id)
        $all = @(Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId)
        do {
            $changed = $false
            foreach ($p in $all) { if ($tree.Contains([int]$p.ParentProcessId) -and $tree.Add([int]$p.ProcessId)) { $changed = $true } }
        } while ($changed)
        $ram = [long]0
        foreach ($processId in $tree) { $p = Get-Process -Id $processId -ErrorAction SilentlyContinue; if ($p) { $ram += $p.WorkingSet64 } }
        $peakRam = [Math]::Max($peakRam,$ram)
        $disk = [long]((Get-ChildItem -LiteralPath $workDir -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum)
        $peakWork = [Math]::Max($peakWork,$disk)
    } while (-not $process.WaitForExit(1000))
    $clock.Stop(); $process.Refresh()
    $state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
    $left = @(Get-ChildItem -LiteralPath $workDir -Force -ErrorAction SilentlyContinue).Count
    $result = @{model=$case.id;requested_backend=$case.backend;backend_used=$state.jobs[0].backend_used;threads=$state.options.threads;audio_sec=7920.1875;wall_sec=$clock.Elapsed.TotalSeconds;rtf=$clock.Elapsed.TotalSeconds/7920.1875;sampled_peak_tree_ram_bytes=$peakRam;sampled_peak_work_bytes=$peakWork;work_entries_after=$left;exit_code=$process.ExitCode;status=$state.jobs[0].status;installed_exe_sha256=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()}
    $result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $resultDir 'summary.json') -Encoding utf8NoBOM
    $result | ConvertTo-Json -Compress
    if ($process.ExitCode -ne 0 -or $left -ne 0 -or $result.status -ne 'done' -or $result.backend_used -ne $case.backend) { throw 'Endurance acceptance failed; retain result and send only redacted summary' }
    $process.Dispose()
}
Write-Host 'Both installed-app cases passed. Keep transcripts/audio local; send the two summary objects only.'
