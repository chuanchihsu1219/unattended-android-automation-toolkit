[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$TaskName = 'Unattended Android Collector',
    [string]$ModuleName = 'your_collector',
    [int[]]$Hours = (1..23)
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$pythonw = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw)) { throw "pythonw.exe not found: $pythonw" }
$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$action = New-ScheduledTaskAction `
    -Execute $pythonw `
    -Argument "-m $ModuleName scheduled-run" `
    -WorkingDirectory $projectRoot
$triggers = @((New-ScheduledTaskTrigger -AtLogOn -User $currentUser))
foreach ($hour in $Hours) {
    if ($hour -lt 1 -or $hour -gt 23) { throw "Schedule hour must be in 1..23: $hour" }
    $triggers += New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.AddHours($hour))
}
$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 45) `
    -StartWhenAvailable `
    -WakeToRun `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal `
    -UserId $currentUser `
    -LogonType Interactive `
    -RunLevel Limited
if ($PSCmdlet.ShouldProcess($TaskName, 'Register unattended Android collector task')) {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $triggers `
        -Settings $settings `
        -Principal $principal `
        -Description 'Headless Android collector example with hourly and logon recovery triggers.' `
        -Force | Out-Null
    Write-Host "Registered scheduled task: $TaskName"
}
