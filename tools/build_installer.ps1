param([string]$Bundle = 'dist/Dusty')

$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Compiler bootstrap runs on disposable CI only' }
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pins = Get-Content -LiteralPath (Join-Path $repo 'packaging/licenses/inno/source.json') -Raw | ConvertFrom-Json
$work = Join-Path $repo 'build/installer'
New-Item -ItemType Directory -Force -Path $work | Out-Null
$bootstrap = Join-Path $work 'innosetup-6.7.3.exe'
Invoke-WebRequest -Uri $pins.compiler_url -OutFile $bootstrap
if ((Get-FileHash -LiteralPath $bootstrap -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pins.compiler_sha256) {
    throw 'Inno compiler bootstrap hash mismatch'
}
$compilerDir = Join-Path $env:RUNNER_TEMP 'dusty-inno-6.7.3'
$process = Start-Process -FilePath $bootstrap -ArgumentList @(
    '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/CURRENTUSER',
    '/NOICONS', '/TASKS=""', ('/DIR="' + $compilerDir + '"')
) -Wait -PassThru -WindowStyle Hidden
if ($process.ExitCode -ne 0) { throw 'Pinned Inno compiler setup failed' }
$iscc = Join-Path $compilerDir 'ISCC.exe'
# The pinned ISCC launcher resource is intentionally 0.0.0.0. Its loaded
# compiler engine supplies the authoritative version in the compilation banner.
& (Join-Path $repo '.venv/Scripts/python.exe') (Join-Path $repo 'installer/generate_iss.py') --bundle $Bundle
if ($LASTEXITCODE -ne 0) { throw 'Installer input generation failed' }
$compilerOutput = @(& $iscc (Join-Path $work 'dusty.iss') 2>&1)
$compilerOutput | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) { throw 'Draft installer compilation failed' }
if ($compilerOutput -notcontains 'Compiler engine version: Inno Setup 6.7.3') {
    throw 'Unexpected Inno compiler engine version'
}
$installers = @(Get-ChildItem -LiteralPath (Join-Path $work 'output') -Filter '*.exe')
if ($installers.Count -ne 1) { throw 'Expected exactly one unsigned draft installer' }
$installer = $installers[0]
$image = [IO.File]::ReadAllBytes($installer.FullName)
$peOffset = [BitConverter]::ToInt32($image, 0x3c)
if ([BitConverter]::ToUInt16($image, $peOffset + 24) -ne 0x10b) {
    throw 'Inno Setup architecture changed; review the pinned Win32 Job Object structure'
}
if ((Get-AuthenticodeSignature -LiteralPath $installer.FullName).Status -ne 'NotSigned') {
    throw 'Unexpected signature state for the unsigned draft'
}
$hash = (Get-FileHash -LiteralPath $installer.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  $($installer.Name)" | Set-Content -LiteralPath (Join-Path $work 'output/SHA256SUMS.txt') -Encoding utf8NoBOM
@{ draft_only = $true; bytes = $installer.Length; sha256 = $hash; compiler = '6.7.3' } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $work 'output/installer.json') -Encoding utf8NoBOM
