param(
    [ValidateSet('cpu', 'vulkan')][string]$Backend = 'cpu',
    [string]$Source = 'build/upstream-whisper',
    [string]$Output = 'build/native'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$pins = Get-Content (Join-Path $PSScriptRoot 'versions.toml') -Raw
$commit = [regex]::Match($pins, '(?s)\[whisper_cpp\].*?commit = "([0-9a-f]{40})"').Groups[1].Value
if (-not $commit) { throw 'Missing whisper.cpp commit pin' }
$sourcePath = [IO.Path]::GetFullPath((Join-Path $repo $Source))
$outputPath = [IO.Path]::GetFullPath((Join-Path $repo $Output))
if (-not (Test-Path (Join-Path $sourcePath 'CMakeLists.txt'))) { throw 'whisper.cpp source is missing' }
$actual = (& git -C $sourcePath rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $actual -ne $commit) { throw 'whisper.cpp commit does not match pin' }

$buildPath = Join-Path $outputPath $Backend
$args = @('-S', $sourcePath, '-B', $buildPath, '-A', 'x64',
    '-DCMAKE_POLICY_DEFAULT_CMP0091=NEW',
    '-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded',
    '-DBUILD_SHARED_LIBS=OFF',
    '-DWHISPER_BUILD_TESTS=OFF',
    '-DWHISPER_BUILD_EXAMPLES=ON',
    '-DWHISPER_SDL2=OFF',
    '-DGGML_CUDA=OFF',
    '-DGGML_BACKEND_DL=OFF',
    '-DGGML_CPU_ALL_VARIANTS=OFF')
if ($Backend -eq 'vulkan') {
    if (-not $env:VULKAN_SDK) { throw 'VULKAN_SDK is required for Vulkan build' }
    $args += '-DGGML_VULKAN=ON'
} else {
    $args += '-DGGML_VULKAN=OFF'
}
& cmake @args
if ($LASTEXITCODE -ne 0) { throw 'CMake configure failed' }
& cmake --build $buildPath --config Release --target whisper-cli whisper-bench --parallel 4
if ($LASTEXITCODE -ne 0) { throw 'CMake build failed' }

$package = Join-Path $outputPath "package/$Backend"
New-Item -ItemType Directory -Force $package | Out-Null
foreach ($name in @('whisper-cli.exe', 'whisper-bench.exe')) {
    $candidate = Join-Path $buildPath "bin/Release/$name"
    if (-not (Test-Path $candidate)) { throw "Missing $name" }
    Copy-Item $candidate $package
}
Write-Output $package
