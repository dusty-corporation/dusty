param([Parameter(Mandatory)][string]$InstallPath, [Parameter(Mandatory)][string]$Output)

$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'Uninstall UI acceptance is disposable CI only' }
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'uninstall_process_tree.ps1')
$labels = & (Join-Path $repo '.venv/Scripts/python.exe') -c 'import json; from dusty.app.messages import INSTALLER; print(json.dumps({k:INSTALLER[k] for k in ("UninstallTitle","UninstallAction","RemoveModels")}))' | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Cannot load shared uninstall wording' }
$key = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{7B3110E8-7983-41AC-A0ED-F6EB13DBB72A}_is1'
$command = (Get-ItemProperty -LiteralPath $key).UninstallString
if ($command -notmatch '^"([^"]+)" /SILENT /DUSTYCONFIRM=yes$') { throw 'Unexpected uninstall registration' }
$exe = [IO.Path]::GetFullPath($Matches[1])
if ([IO.Path]::GetDirectoryName($exe) -ne [IO.Path]::GetFullPath($InstallPath)) { throw 'Uninstaller outside acceptance install' }
Add-Type @'
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public static class DustyUninstallUi {
  public delegate bool EnumProc(IntPtr h, IntPtr p);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc f, IntPtr p);
  [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr h, EnumProc f, IntPtr p);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern IntPtr SendMessageTimeoutW(IntPtr h, uint m, UIntPtr w, StringBuilder b, uint flags, uint timeout, out UIntPtr result);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetClassNameW(IntPtr h, StringBuilder b, int n);
  [DllImport("user32.dll")] public static extern IntPtr SendMessageW(IntPtr h, uint m, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  public static string Text(IntPtr h) {
    // WM_GETTEXT is marshalled across processes. GetWindowTextW is not a
    // supported way to read another process's custom control text.
    var b=new StringBuilder(2048); UIntPtr result;
    if(SendMessageTimeoutW(h,0x000D,new UIntPtr((uint)b.Capacity),b,0x22,250,out result)==IntPtr.Zero) return "";
    return b.ToString();
  }
  public static string Class(IntPtr h) { var b=new StringBuilder(128); GetClassNameW(h,b,b.Capacity); return b.ToString(); }
  public static IntPtr[] Windows(IntPtr parent) {
    var r=new List<IntPtr>(); EnumProc f=(h,p)=>{r.Add(h);return true;};
    if(parent==IntPtr.Zero) EnumWindows(f,IntPtr.Zero); else EnumChildWindows(parent,f,IntPtr.Zero);
    return r.ToArray();
  }
}
'@
$p = Start-Process -FilePath $exe -ArgumentList @('/SILENT','/DUSTYCONFIRM=yes','/NORESTART') -PassThru -WindowStyle Hidden
$tracker = New-UninstallTracker $p
$pids = [Collections.Generic.HashSet[int]]::new()
[void]$pids.Add($p.Id)
$seen = $false
$pending = 'no visible confirmation'
$deadline = [datetime]::UtcNow.AddSeconds(60)
try {
    while ((Update-UninstallTracker $tracker) -and [datetime]::UtcNow -lt $deadline) {
        foreach ($childId in $tracker.Children.Keys) { [void]$pids.Add([int]$childId) }
        foreach ($handle in [DustyUninstallUi]::Windows([IntPtr]::Zero)) {
            [uint32]$ownerId = 0
            [void][DustyUninstallUi]::GetWindowThreadProcessId($handle,[ref]$ownerId)
            if (-not $pids.Contains([int]$ownerId)) { continue }
            if (-not [DustyUninstallUi]::IsWindowVisible($handle)) { continue }
            if ([DustyUninstallUi]::Class($handle) -eq '#32770') { throw 'Redundant or unexpected native message box appeared' }
            if ([DustyUninstallUi]::Text($handle) -ne $labels.UninstallTitle -or $seen) { continue }
            $children = [DustyUninstallUi]::Windows($handle)
            $choice = @($children | Where-Object { [DustyUninstallUi]::Text($_).StartsWith(($labels.RemoveModels -split '%1')[0]) })
            $confirm = @($children | Where-Object { [DustyUninstallUi]::Text($_) -eq $labels.UninstallAction })
            # Inno creates a hidden form with the same title before the custom
            # page. A visible page can also be observed while controls are being
            # created. Wait within the same deadline; never accept absent controls.
            $pending = 'class=' + [DustyUninstallUi]::Class($handle) + ' choices=' + $choice.Count + ' confirmations=' + $confirm.Count
            if ($choice.Count -ne 1 -or $confirm.Count -ne 1) { continue }
            [void][DustyUninstallUi]::SetForegroundWindow($handle)
            if ([DustyUninstallUi]::SendMessageW($choice[0],0xF0,[IntPtr]::Zero,[IntPtr]::Zero).ToInt32() -ne 1) { throw 'Remove-model checkbox not checked by default' }
            [void][DustyUninstallUi]::SendMessageW($choice[0],0xF5,[IntPtr]::Zero,[IntPtr]::Zero)
            if ([DustyUninstallUi]::SendMessageW($choice[0],0xF0,[IntPtr]::Zero,[IntPtr]::Zero).ToInt32() -ne 0) { throw 'Could not choose keep models' }
            $seen = $true
            [void][DustyUninstallUi]::SendMessageW($confirm[0],0xF5,[IntPtr]::Zero,[IntPtr]::Zero)
        }
        [void]$p.WaitForExit(100)
        $p.Refresh()
    }
    Assert-UninstallTrackerExit $tracker 0
    if (-not $p.HasExited -or $p.ExitCode -ne 0 -or -not $seen) { throw ('Interactive uninstall did not complete with one custom confirmation; ' + $pending) }
    @{custom_confirmation=1;generic_confirmation=0;keep_models_choice='passed'} | ConvertTo-Json | Set-Content -LiteralPath $Output -Encoding utf8NoBOM
} finally {
    if (-not $p.HasExited) { $p.Kill($true); $p.WaitForExit() }
    Close-UninstallTracker $tracker
    $p.Dispose()
}
