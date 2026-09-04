[CmdletBinding()]
param(
    [string]$TaskName = 'Unattended Android Collector',
    [int[]]$ExpectedHours = (1..23)
)

$ErrorActionPreference = 'Stop'
$task = Get-ScheduledTask -TaskName $TaskName
$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
[xml]$xml = Export-ScheduledTask -TaskName $TaskName
$namespace = [Xml.XmlNamespaceManager]::new($xml.NameTable)
$namespace.AddNamespace('t', 'http://schemas.microsoft.com/windows/2004/02/mit/task')
$calendar = @($xml.SelectNodes('//t:Triggers/t:CalendarTrigger', $namespace))
$logon = @($xml.SelectNodes('//t:Triggers/t:LogonTrigger', $namespace))
$hours = @($calendar | ForEach-Object { [datetimeoffset]$_.StartBoundary } | ForEach-Object Hour | Sort-Object)
$settings = $xml.Task.Settings
$restart = $settings.RestartOnFailure
[ordered]@{
    state = [string]$task.State
    last_task_result = $taskInfo.LastTaskResult
    next_run_time = $taskInfo.NextRunTime
    calendar_trigger_count = $calendar.Count
    calendar_hours = $hours
    expected_hours_match = (($hours -join ',') -eq (($ExpectedHours | Sort-Object) -join ','))
    midnight_trigger_absent = 0 -notin $hours
    logon_trigger_count = $logon.Count
    hidden = [string]$settings.Hidden
    multiple_instances = [string]$settings.MultipleInstancesPolicy
    wake_to_run = [string]$settings.WakeToRun
    start_when_available = [string]$settings.StartWhenAvailable
    allow_start_on_battery = ([string]$settings.DisallowStartIfOnBatteries -eq 'false')
    continue_on_battery = ([string]$settings.StopIfGoingOnBatteries -eq 'false')
    restart_count = if ($restart) { [int]$restart.Count } else { 0 }
    restart_interval = if ($restart) { [string]$restart.Interval } else { '' }
} | ConvertTo-Json -Depth 5
