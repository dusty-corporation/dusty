param([string]$Destination = 'build/startup-probe-m2')

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$target = [IO.Path]::GetFullPath((Join-Path $repo $Destination))
if (-not $target.StartsWith($repo + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Package destination must be inside the repository'
}
if ((Test-Path -LiteralPath $target) -or (Test-Path -LiteralPath "$target.zip")) {
    throw 'Package destination already exists'
}
foreach ($folder in @('tools/bench', 'tests/fixtures/audio/formats')) {
    New-Item -ItemType Directory -Force (Join-Path $target $folder) | Out-Null
}
foreach ($name in @('startup-probe.ps1', 'setup-startup-probe.ps1')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $name) -Destination (Join-Path $target 'tools/bench')
}
Copy-Item -LiteralPath (Join-Path $repo 'tests/fixtures/audio/formats/jfk.wav') -Destination (Join-Path $target 'tests/fixtures/audio/formats')
Copy-Item -LiteralPath (Join-Path $repo 'tests/fixtures/AUDIO_SOURCES.md') -Destination (Join-Path $target 'AUDIO_SOURCES.md')
Copy-Item -LiteralPath (Join-Path $repo 'docs/dev/startup-probe.md') -Destination (Join-Path $target 'README.md')
Copy-Item -LiteralPath (Join-Path $repo 'LICENSE') -Destination $target
Compress-Archive -LiteralPath $target -DestinationPath "$target.zip" -CompressionLevel Optimal
Get-Item -LiteralPath "$target.zip" | Select-Object Name, Length
Get-FileHash -LiteralPath "$target.zip" -Algorithm SHA256 | Select-Object Hash
