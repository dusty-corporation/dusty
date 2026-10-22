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
$patchName = [regex]::Match($pins, '(?s)\[whisper_cpp\].*?patch = "([^"]+)"').Groups[1].Value
$patchHash = [regex]::Match($pins, '(?s)\[whisper_cpp\].*?patch_sha256 = "([0-9a-f]{64})"').Groups[1].Value
if (-not $patchName -or -not $patchHash) { throw 'Missing approved native patch pin' }
$patchPath = Join-Path $repo $patchName
if ((Get-FileHash -LiteralPath $patchPath -Algorithm SHA256).Hash -ne $patchHash) { throw 'Native patch hash mismatch' }
& git -C $sourcePath apply --check $patchPath 2>$null
if ($LASTEXITCODE -eq 0) {
    & git -C $sourcePath apply $patchPath
    if ($LASTEXITCODE -ne 0) { throw 'Native patch application failed' }
} else {
    & git -C $sourcePath apply --reverse --check $patchPath 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Source does not match the approved native patch' }
}
Write-Output "Applied native patch SHA-256=$patchHash"

$buildPath = Join-Path $outputPath $Backend
$args = @('-S', $sourcePath, '-B', $buildPath, '-A', 'x64',
    '-DCMAKE_POLICY_DEFAULT_CMP0091=NEW',
    '-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded',
    '-DBUILD_SHARED_LIBS=ON',
    '-DWHISPER_BUILD_TESTS=OFF',
    '-DWHISPER_BUILD_EXAMPLES=ON',
    '-DWHISPER_SDL2=OFF',
    '-DGGML_CUDA=OFF',
    '-DGGML_OPENMP=OFF',
    '-DGGML_NATIVE=OFF',
    '-DGGML_BACKEND_DL=ON',
    '-DGGML_CPU_ALL_VARIANTS=ON')
if ($Backend -eq 'vulkan') {
    if (-not $env:VULKAN_SDK) { throw 'VULKAN_SDK is required for Vulkan build' }
    $args += '-DGGML_VULKAN=ON'
} else {
    $args += '-DGGML_VULKAN=OFF'
}
& cmake @args
if ($LASTEXITCODE -ne 0) { throw 'CMake configure failed' }
$cache = Get-Content (Join-Path $buildPath 'CMakeCache.txt')
$cache | Where-Object { $_ -match '^GGML_[^:]+:' } | Write-Output
foreach ($required in @('GGML_NATIVE:BOOL=OFF', 'GGML_BACKEND_DL:BOOL=ON', 'GGML_CPU_ALL_VARIANTS:BOOL=ON')) {
    if ($cache -notcontains $required) { throw "Unsafe CMake cache: $required missing" }
}
if ($cache -contains 'GGML_NATIVE:BOOL=ON') { throw 'GGML_NATIVE must be OFF' }
& cmake --build $buildPath --config Release --target whisper-cli whisper-bench --parallel 4
if ($LASTEXITCODE -ne 0) { throw 'CMake build failed' }

$package = Join-Path $outputPath "package/$Backend"
New-Item -ItemType Directory -Force $package | Out-Null
foreach ($name in @('whisper-cli.exe', 'whisper-bench.exe')) {
    $candidate = Join-Path $buildPath "bin/Release/$name"
    if (-not (Test-Path $candidate)) { throw "Missing $name" }
    Copy-Item $candidate $package
}
$runtime = Join-Path $buildPath 'bin/Release'
Get-ChildItem $runtime -Filter '*.dll' | Copy-Item -Destination $package
if (-not (Get-ChildItem $package -Filter 'ggml-cpu-*.dll')) { throw 'Runtime CPU variants missing' }
foreach ($variant in @('x64', 'sse42', 'sandybridge', 'haswell', 'skylakex', 'cannonlake', 'cascadelake', 'icelake', 'alderlake')) {
    $name = "ggml-cpu-$variant.dll"
    if (-not (Test-Path (Join-Path $package $name))) { throw "Missing CPU variant $name" }
}
Write-Output $package
