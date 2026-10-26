param(
    [string]$Executable = 'build/installer/review/Dusty-page-review.exe',
    [string]$Output = 'build/installer/screenshots',
    [int]$ExpectedDpi = 96,
    [string[]]$Pages = @('models-checking','models','models-bottom','models-low-memory','models-skip','finish-without','uninstall-helper-unavailable'),
    [Nullable[int]]$Left,
    [Nullable[int]]$Top
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$exe = (Resolve-Path -LiteralPath $Executable).Path
$destination = [IO.Path]::GetFullPath((Join-Path $repo $Output))
if (-not $exe.StartsWith($repo + '\') -or -not $destination.StartsWith($repo + '\')) { throw 'Review must stay inside the repository' }
New-Item -ItemType Directory -Force -Path $destination | Out-Null
$env:TEMP = Join-Path $destination 'temp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
foreach ($page in $Pages) {
    $bmp = Join-Path $destination ($page + '.bmp')
    $meta = Join-Path $destination ($page + '.json')
    if ((Test-Path -LiteralPath $bmp) -or (Test-Path -LiteralPath $meta)) { throw 'Use a fresh capture directory' }
    $arguments = @('/SP-',('/REVIEWPAGE=' + $page),('/REVIEWBMP="' + $bmp + '"'),('/REVIEWMETA="' + $meta + '"'))
    if ($null -ne $Left) { $arguments += ('/REVIEWLEFT=' + $Left); $arguments += ('/REVIEWTOP=' + $Top) }
    $process = Start-Process -FilePath $exe -ArgumentList $arguments -PassThru -WindowStyle Hidden
    try {
        $deadline = [DateTime]::UtcNow.AddSeconds(30)
        while (-not (Test-Path -LiteralPath $bmp) -and [DateTime]::UtcNow -lt $deadline) {
            if ($process.HasExited) { throw 'Review exited before capture' }
            Start-Sleep -Milliseconds 100
        }
        if (-not (Test-Path -LiteralPath $bmp)) { throw 'Native review capture timed out' }
        # The file is written by the same controls on the production page.
        Start-Sleep -Milliseconds 250
        $layout = Get-Content -LiteralPath $meta -Raw | ConvertFrom-Json
        if ($layout.dpi -ne $ExpectedDpi) { throw 'Native capture DPI mismatch' }
        if ($page -eq 'uninstall-helper-unavailable') {
            if ($layout.native_helper_message -ne $true -or $layout.width -le 0 -or $layout.height -le 0) { throw 'Native helper message capture missing' }
        } else {
        $expectedFont = [int][Math]::Round(10 * $ExpectedDpi / 72)
        if ([Math]::Abs($layout.font_height) -ne $expectedFont) { throw 'Native capture font DPI mismatch' }
        if (-not $layout.model_controls_fit) { throw 'Native model controls exceed their containers' }
        }
    } finally {
        if (-not $process.HasExited) { $process.Kill($true); $process.WaitForExit(5000) | Out-Null }
    }
}
& (Join-Path $repo '.venv/Scripts/python.exe') (Join-Path $PSScriptRoot 'review_bitmaps.py') $destination
if ($LASTEXITCODE -ne 0) { throw 'Review PNG conversion failed' }
