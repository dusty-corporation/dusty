function Get-DustyConnectionEvents {
    param($Events, [string[]]$Programs, [long]$AfterRecordId, [long]$ExcludeProcessId = -1)
    foreach ($event in $Events) {
        if ($event.Id -notin @(5156, 5157) -or $event.RecordId -le $AfterRecordId) { continue }
        [xml]$xml = $event.ToXml()
        $data = @{}
        foreach ($field in $xml.Event.EventData.Data) { $data[$field.Name] = $field.InnerText }
        $processNumber = if ($data.ProcessID -match '^0x') {
            [Convert]::ToInt64($data.ProcessID.Substring(2), 16)
        } else { [long]$data.ProcessID }
        if ($processNumber -eq $ExcludeProcessId) { continue }
        $application = ([string]$data.Application).Replace('/', '\').ToLowerInvariant()
        foreach ($program in $Programs) {
            $normalized = $program.Replace('/', '\').ToLowerInvariant()
            $suffix = if ($normalized -match '^[a-z]:\\') { $normalized.Substring(2) } else { $normalized }
            if ($application.EndsWith($suffix, [StringComparison]::Ordinal)) {
                [PSCustomObject]@{ EventId = [int]$event.Id; ProcessId = $processNumber }
                break
            }
        }
    }
}
