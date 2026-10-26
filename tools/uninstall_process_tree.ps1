# Inno's launcher exits before its second phase finishes usPostUninstall.
# Track handles for the process tree we started, never infer completion from
# disappearance of files or registry values and never use a fixed delay.
function New-UninstallTracker([Diagnostics.Process]$Root) {
    return @{Root=$Root; Children=@{}}
}

function Update-UninstallTracker($Tracker) {
    $parents = @($Tracker.Root.Id) + @($Tracker.Children.Keys)
    foreach ($parentId in $parents) {
        foreach ($child in @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$parentId")) {
            $childId = [int]$child.ProcessId
            if ($Tracker.Children.ContainsKey($childId)) { continue }
            $owned = Get-Process -Id $childId -ErrorAction SilentlyContinue
            if ($null -eq $owned) { continue }
            try { [void]$owned.Handle } catch { $owned.Dispose(); continue }
            $Tracker.Children[$childId] = @{Process=$owned; Worker=($child.Name -eq '_unins.tmp')}
        }
    }
    $Tracker.Root.Refresh()
    $active = -not $Tracker.Root.HasExited
    foreach ($entry in $Tracker.Children.Values) {
        $entry.Process.Refresh()
        if (-not $entry.Process.HasExited) { $active = $true }
    }
    return $active
}

function Assert-UninstallTrackerExit($Tracker, [int]$ExpectedExit) {
    if (Update-UninstallTracker $Tracker) { throw 'Uninstall worker is still running' }
    if ($Tracker.Root.ExitCode -ne $ExpectedExit) { throw 'Uninstall launcher exit code mismatch' }
    foreach ($entry in $Tracker.Children.Values) {
        if ($entry.Worker -and $entry.Process.ExitCode -ne $ExpectedExit) { throw 'Actual uninstall worker exit code mismatch' }
    }
}

function Close-UninstallTracker($Tracker) {
    $Tracker.Root.Refresh()
    if (-not $Tracker.Root.HasExited) { $Tracker.Root.Kill($true); [void]$Tracker.Root.WaitForExit(5000) }
    foreach ($entry in $Tracker.Children.Values) {
        $entry.Process.Refresh()
        if (-not $entry.Process.HasExited) { $entry.Process.Kill($true); [void]$entry.Process.WaitForExit(5000) }
        $entry.Process.Dispose()
    }
}
