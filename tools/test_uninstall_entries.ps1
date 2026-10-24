param([Parameter(Mandatory)][string]$InstallPath, [Parameter(Mandatory)][string]$Output)

$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Installed entry audit is disposable CI only' }
$InstallPath = [IO.Path]::GetFullPath($InstallPath)
$key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{7B3110E8-7983-41AC-A0ED-F6EB13DBB72A}_is1'
$values = Get-ItemProperty -LiteralPath $key
$expected = $values.UninstallString
if ($expected -notmatch '^"([^"]+)" /SILENT /DUSTYCONFIRM=yes$') { throw 'Uninstall registration lacks official confirmation arguments' }
$exe = [IO.Path]::GetFullPath($Matches[1])
if ([IO.Path]::GetDirectoryName($exe) -ne [IO.Path]::GetFullPath($InstallPath)) { throw 'Registered uninstaller outside acceptance install' }
if ($values.QuietUninstallString -ne $expected) { throw 'Quiet uninstall registration bypasses the official confirmation route' }
$registered = @()
foreach ($value in $values.PSObject.Properties) {
    if ($value.Value -is [string] -and $value.Value -match '(?i)unins[0-9]*\.exe') {
        if ($value.Value -ne $expected) { throw 'Other registered command invokes an unsupported uninstaller route' }
        $registered += $value.Name
    }
}
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$raw = & (Join-Path $repo '.venv/Scripts/python.exe') -m tools.audit_shortcuts $InstallPath ([Environment]::GetFolderPath('Programs')) ([Environment]::GetFolderPath('DesktopDirectory'))
if ($LASTEXITCODE -ne 0) { throw 'Unicode shortcut target audit failed' }
$checked = @($raw | ConvertFrom-Json)
@{registered_commands=$registered;shortcuts=$checked;bare_uninstall_entries=0} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $Output -Encoding utf8NoBOM
if (@($checked | Where-Object { $_.target -eq (Join-Path 'dusty' 'dusty.exe') }).Count -ne 2) { throw 'Expected Start Menu and default Desktop app shortcuts' }
