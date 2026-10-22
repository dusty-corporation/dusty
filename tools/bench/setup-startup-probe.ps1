param([string]$Root)

$ErrorActionPreference = 'Stop'
if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path }
$rootPath = [IO.Path]::GetFullPath($Root)
$downloads = Join-Path $rootPath 'build/downloads'
$models = Join-Path $rootPath 'build/models'
New-Item -ItemType Directory -Force $downloads, $models | Out-Null
foreach ($asset in @(
    @('whisper-cpu.zip', 'cpu', 'bb98378bfe200f503fdeff5aed8aa9e7c043a3e32f6d274b3ae4fb8ebdcb120c'),
    @('whisper-vulkan.zip', 'vulkan', '1c6892dea290e4c16b3a1e109ac5950e018fa89ce2a27c679f638009f4921f76')
)) {
    $archive = Join-Path $downloads $asset[0]
    if (-not (Test-Path -LiteralPath $archive)) {
        gh release download engine-v1 --repo dusty-corporation/dusty --pattern $asset[0] --dir $downloads
        if ($LASTEXITCODE -ne 0) { throw 'Engine download failed' }
    }
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne $asset[2]) {
        throw 'Engine archive hash does not match the pin'
    }
    $destination = Join-Path $rootPath "build/bin/$($asset[1])"
    if (-not (Test-Path -LiteralPath $destination)) {
        Expand-Archive -LiteralPath $archive -DestinationPath $destination
    }
    $zip = [IO.Compression.ZipFile]::OpenRead($archive)
    try {
        foreach ($entry in $zip.Entries) {
            if (-not $entry.Name) { continue }
            $file = Join-Path $destination $entry.FullName
            if (-not (Test-Path -LiteralPath $file)) { throw 'An extracted engine file is missing' }
            $stream = $entry.Open()
            try { $expected = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($stream)) }
            finally { $stream.Dispose() }
            if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $expected) {
                throw 'An extracted engine file differs from the pinned archive'
            }
        }
    } finally { $zip.Dispose() }
}
$model = Join-Path $models 'ggml-tiny.bin'
if (-not (Test-Path -LiteralPath $model)) {
    gh release download models-v1 --repo dusty-corporation/dusty --pattern ggml-tiny.bin --dir $models
    if ($LASTEXITCODE -ne 0) { throw 'Model download failed' }
}
if ((Get-FileHash -LiteralPath $model -Algorithm SHA256).Hash -ne 'a38bcb31dcd68cf7d9a630e2148ccf0656f95ac87c5bcbc4064a689f383b2059') {
    throw 'Tiny model hash does not match the pin'
}
'Setup complete. No Python or repository clone is needed.'
