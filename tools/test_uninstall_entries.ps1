param([Parameter(Mandatory)][string]$InstallPath, [Parameter(Mandatory)][string]$Output)

$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Installed entry audit is disposable CI only' }
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
$shell = New-Object -ComObject WScript.Shell
$checked = @()
try {
    foreach ($root in @([Environment]::GetFolderPath('Programs'),[Environment]::GetFolderPath('DesktopDirectory'))) {
        foreach ($file in @(Get-ChildItem -LiteralPath $root -Recurse -Filter '*.lnk' -File)) {
            $link = $shell.CreateShortcut($file.FullName)
            try {
                $target = [string]$link.TargetPath
                if (-not $target -or -not $target.StartsWith($InstallPath + '\',[StringComparison]::OrdinalIgnoreCase)) { continue }
                $relative = [IO.Path]::GetRelativePath($InstallPath,$target)
                if ([IO.Path]::GetFileName($target) -match '(?i)^unins[0-9]*\.exe$' -and $link.Arguments -ne '/SILENT /DUSTYCONFIRM=yes') { throw 'Shortcut launches a bare uninstaller' }
                $checked += @{target=$relative;arguments=[string]$link.Arguments}
            } finally { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($link) }
        }
    }
} finally { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shell) }
if (@($checked | Where-Object { $_.target -eq 'dusty\dusty.exe' }).Count -ne 2) { throw 'Expected Start Menu and default Desktop app shortcuts' }
@{registered_commands=$registered;shortcuts=$checked;bare_uninstall_entries=0} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $Output -Encoding utf8NoBOM
