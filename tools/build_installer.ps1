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
$installedLicense = (Get-Content -LiteralPath (Join-Path $compilerDir 'license.txt') -Raw).Replace("`r`n", "`n").Trim()
$sourceLicense = (Get-Content -LiteralPath (Join-Path $repo 'packaging/licenses/inno/license.txt') -Raw).Replace("`r`n", "`n").Trim()
if ($installedLicense -cne $sourceLicense) { throw 'Compiler binary license differs from pinned source terms' }
$iscc = Join-Path $compilerDir 'ISCC.exe'
$sourceProof = Get-Content -LiteralPath (Join-Path $repo 'packaging/licenses/inno/runtime-source.json') -Raw | ConvertFrom-Json
$sourceRoot = Join-Path $work 'upstream-source'
foreach ($entry in @($sourceProof.reviewed_files) + @($sourceProof.jedi_sources)) {
    $target = Join-Path $sourceRoot $entry.path
    New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
    Invoke-WebRequest -Uri ('https://raw.githubusercontent.com/jrsoftware/issrc/' + $sourceProof.commit + '/' + $entry.path) -OutFile $target
    if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw 'Pinned Inno source hash mismatch' }
}
& (Join-Path $repo '.venv/Scripts/python.exe') -c 'from pathlib import Path; from tools.installer_notices import source_archive; import sys; Path(sys.argv[2]).write_bytes(source_archive(Path(sys.argv[1])))' $sourceRoot (Join-Path $work 'installer-jedi-source.zip')
if ($LASTEXITCODE -ne 0) { throw 'Installer source retention failed' }
$runtimeFiles = @($sourceProof.runtime_files | ForEach-Object {
    $path = Join-Path $compilerDir $_
    @{name=$_;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant();bytes=(Get-Item -LiteralPath $path).Length}
})
@{files=$runtimeFiles;source_commit=$sourceProof.commit;source_review_sha256=(Get-FileHash -LiteralPath (Join-Path $repo 'packaging/licenses/inno/runtime-source.json')).Hash.ToLowerInvariant();compiler_bootstrap_sha256=$pins.compiler_sha256} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $work 'runtime-inputs.json') -Encoding utf8NoBOM
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
if (-not ($compilerOutput -match 'Updating icons \(Setup\.e32\)') -or ($compilerOutput -match 'SetupCustomStyle\.e32')) {
    throw 'Installer runtime selection changed; review ADR 0023 unit inventory'
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
