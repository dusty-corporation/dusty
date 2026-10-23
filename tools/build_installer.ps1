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
$version = (Get-Item -LiteralPath $iscc).VersionInfo
$numericVersion = '{0}.{1}.{2}' -f $version.FileMajorPart, $version.FileMinorPart, $version.FileBuildPart
Write-Host "Inno compiler file version: $($version.FileVersion); numeric: $numericVersion"
if ($numericVersion -ne '6.7.3') {
    throw 'Unexpected Inno compiler numeric version'
}
& (Join-Path $repo '.venv/Scripts/python.exe') (Join-Path $repo 'installer/generate_iss.py') --bundle $Bundle
if ($LASTEXITCODE -ne 0) { throw 'Installer input generation failed' }
& $iscc /Qp (Join-Path $work 'dusty.iss')
if ($LASTEXITCODE -ne 0) { throw 'Draft installer compilation failed' }
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
