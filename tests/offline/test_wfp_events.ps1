$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '../../tools/wfp_events.ps1')
function New-TestEvent([int]$Id, [long]$Record, [string]$Process, [string]$Application) {
    $item = [PSCustomObject]@{
        Id = $Id; RecordId = $Record
        XmlContent = "<Event><EventData><Data Name='ProcessID'>$Process</Data><Data Name='Application'>$Application</Data></EventData></Event>"
    }
    $item | Add-Member -MemberType ScriptMethod -Name ToXml -Value { return $this.XmlContent }
    return $item
}
$events = @(
    (New-TestEvent 5156 11 '123' '\device\harddiskvolume2\work\venv\python.exe'),
    (New-TestEvent 5157 12 '0x7c' '\device\harddiskvolume2\work\venv\python.exe'),
    (New-TestEvent 5157 13 '125' '\device\harddiskvolume2\other\python.exe'),
    (New-TestEvent 5157 9 '126' '\device\harddiskvolume2\work\venv\python.exe'),
    (New-TestEvent 5158 14 '127' '\device\harddiskvolume2\work\venv\python.exe')
)
$matched = @(Get-DustyConnectionEvents -Events $events -Programs @('C:\work\venv\python.exe') -AfterRecordId 10)
if ($matched.Count -ne 2 -or $matched[1].ProcessId -ne 124) { throw 'WFP image or PID parser regression' }
$withoutControl = @(Get-DustyConnectionEvents -Events $events -Programs @('C:\work\venv\python.exe') -AfterRecordId 10 -ExcludeProcessId 123)
if ($withoutControl.Count -ne 1 -or $withoutControl[0].EventId -ne 5157) { throw 'WFP calibration exclusion regression' }
'WFP parser checks passed'
