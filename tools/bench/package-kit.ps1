param(
    [Parameter(Mandatory = $true)][string]$CpuDir,
    [Parameter(Mandatory = $true)][string]$VulkanDir,
    [Parameter(Mandatory = $true)][string]$FfmpegDir,
    [Parameter(Mandatory = $true)][string]$Manifest,
    [string]$Destination = 'build/bench-kit-m1'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$destinationPath = [IO.Path]::GetFullPath((Join-Path $repo $Destination))
if (Test-Path $destinationPath) { throw 'Destination already exists' }
foreach ($source in @($CpuDir, $VulkanDir, $FfmpegDir, $Manifest)) {
    if (-not (Test-Path $source)) { throw 'A packaging input is missing' }
}
foreach ($folder in @('bin/cpu', 'bin/vulkan', 'bin/ffmpeg', 'models', 'audio', 'tools/bench')) {
    New-Item -ItemType Directory -Force (Join-Path $destinationPath $folder) | Out-Null
}
foreach ($source in @(@($CpuDir, 'cpu'), @($VulkanDir, 'vulkan'))) {
    $target = Join-Path $destinationPath "bin/$($source[1])"
    Get-ChildItem $source[0] -File | Where-Object { $_.Extension -in @('.exe', '.dll') } |
        Copy-Item -Destination $target
    if (-not (Test-Path (Join-Path $target 'whisper-cli.exe'))) { throw 'Engine binary missing' }
    if (-not (Test-Path (Join-Path $target 'ggml-cpu-haswell.dll'))) { throw 'CPU variant missing' }
}
Get-ChildItem $FfmpegDir -File -Filter '*.exe' | Copy-Item -Destination (Join-Path $destinationPath 'bin/ffmpeg')
Copy-Item $Manifest (Join-Path $destinationPath 'models.json')
Copy-Item (Join-Path $repo 'tools/bench/run-bench.ps1') (Join-Path $destinationPath 'tools/bench')
Copy-Item (Join-Path $repo 'tools/bench/README.txt') (Join-Path $destinationPath 'README.txt')
Copy-Item (Join-Path $repo 'tests/fixtures/audio/formats/jfk.wav') (Join-Path $destinationPath 'audio/warmup.wav')
Copy-Item (Join-Path $repo 'tests/fixtures/audio/bench/swineherd-reference.txt') (Join-Path $destinationPath 'audio/swineherd-reference.txt')
Copy-Item (Join-Path $repo 'tests/fixtures/audio/bench/swineherd-scored-spans.json') (Join-Path $destinationPath 'audio/swineherd-scored-spans.json')
$ffmpeg = Join-Path $destinationPath 'bin/ffmpeg/ffmpeg.exe'
& $ffmpeg -nostdin -hide_banner -loglevel error -protocol_whitelist file,pipe -i (Join-Path $repo 'tests/fixtures/audio/bench/swineherd.mp3') -vn -map 0:a:0 -ac 1 -ar 16000 -c:a pcm_s16le -f wav (Join-Path $destinationPath 'audio/swineherd.wav') -y
if ($LASTEXITCODE -ne 0) { throw 'Public reference audio conversion failed' }
$archive = "$destinationPath.zip"
Compress-Archive -Path $destinationPath -DestinationPath $archive -CompressionLevel Optimal
Get-Item $archive | Select-Object FullName, Length
Get-FileHash $archive -Algorithm SHA256 | Select-Object Hash
