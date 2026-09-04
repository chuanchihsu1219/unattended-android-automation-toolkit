[CmdletBinding()]
param(
    [string]$Serial = 'emulator-5556',
    [string]$Package = '',
    [string]$OutputRoot = 'runtime/dev-tools/state',
    [switch]$IncludeScreenshot,
    [switch]$AcknowledgeScreenshotMayContainSecrets,
    [switch]$AllowWhileCollectorRunning
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$collectorPidPath = Join-Path $projectRoot 'runtime\owned-emulator.json'
if ((Test-Path -LiteralPath $collectorPidPath) -and -not $AllowWhileCollectorRunning) {
    throw 'The collector appears to own the Emulator. Wait for it to finish, or explicitly pass -AllowWhileCollectorRunning for live incident diagnosis.'
}
$adb = Join-Path $env:LOCALAPPDATA 'Android\Sdk\platform-tools\adb.exe'
if (-not (Test-Path -LiteralPath $adb)) { throw "ADB not found: $adb" }
if ($IncludeScreenshot -and -not $AcknowledgeScreenshotMayContainSecrets) {
    throw 'Screenshot capture requires -AcknowledgeScreenshotMayContainSecrets.'
}

$outputBase = if ([IO.Path]::IsPathRooted($OutputRoot)) {
    [IO.Path]::GetFullPath($OutputRoot)
} else {
    [IO.Path]::GetFullPath((Join-Path $projectRoot $OutputRoot))
}
$projectPrefix = $projectRoot.TrimEnd('\') + '\'
if (-not $outputBase.StartsWith($projectPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'OutputRoot must stay inside the project directory.'
}
$outputDirectory = Join-Path $outputBase (Get-Date -Format 'yyyyMMdd_HHmmss')
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

$secretValues = @()
$envPath = Join-Path $projectRoot '.env'
if (Test-Path -LiteralPath $envPath) {
    foreach ($line in Get-Content -LiteralPath $envPath -Encoding UTF8) {
        if ($line -match '^\s*[^#][A-Za-z0-9_]*?(ACCOUNT|AUTHORIZATION|EMAIL|PASSWORD|PASSWD|PWD|SECRET|TOKEN|USERNAME)[A-Za-z0-9_]*?\s*=\s*(.*)\s*$') {
            $value = $Matches[2].Trim().Trim('"').Trim("'")
            if ($value) { $secretValues += $value }
        }
    }
}

function Protect-Text {
    param([AllowEmptyString()][string]$Text)
    $safe = $Text
    foreach ($secret in ($secretValues | Sort-Object Length -Descending -Unique)) {
        $safe = $safe.Replace($secret, '[REDACTED]')
    }
    return $safe
}

function Invoke-AdbText {
    param([string[]]$Arguments)
    return Protect-Text (& $adb -s $Serial @Arguments 2>&1 | Out-String)
}

function Write-SafeText {
    param([string]$Name, [AllowEmptyString()][string]$Content)
    [IO.File]::WriteAllText(
        (Join-Path $outputDirectory $Name),
        (Protect-Text $Content),
        [Text.UTF8Encoding]::new($false)
    )
}

$state = Invoke-AdbText @('get-state')
if ($state.Trim() -ne 'device') { throw "Device is not ready: $($state.Trim())" }
Write-SafeText 'adb_state.txt' $state
Write-SafeText 'boot_props.txt' (Invoke-AdbText @('shell', 'getprop'))
Write-SafeText 'connectivity.txt' (Invoke-AdbText @('shell', 'dumpsys', 'connectivity'))
Write-SafeText 'activity.txt' (Invoke-AdbText @('shell', 'dumpsys', 'activity', 'activities'))
Write-SafeText 'window.txt' (Invoke-AdbText @('shell', 'dumpsys', 'window', 'windows'))
Write-SafeText 'logcat_tail.txt' (Invoke-AdbText @('logcat', '-d', '-t', '500'))
if ($Package) {
    Write-SafeText 'package.txt' (Invoke-AdbText @('shell', 'dumpsys', 'package', $Package))
}

$remoteXml = '/sdcard/toolkit_window_dump.xml'
$remoteScreenshot = '/sdcard/toolkit_screen.png'
try {
    Write-SafeText 'hierarchy_dump_status.txt' (Invoke-AdbText @('shell', 'uiautomator', 'dump', $remoteXml))
    Write-SafeText 'hierarchy_sanitized.xml' (Invoke-AdbText @('exec-out', 'cat', $remoteXml))
    if ($IncludeScreenshot) {
        & $adb -s $Serial shell screencap -p $remoteScreenshot | Out-Null
        & $adb -s $Serial pull $remoteScreenshot (Join-Path $outputDirectory 'screen_sensitive.png') | Out-Null
    }
} finally {
    & $adb -s $Serial shell rm -f $remoteXml $remoteScreenshot 2>$null | Out-Null
}

Write-SafeText 'metadata.json' ([ordered]@{
    captured_at = (Get-Date).ToString('o')
    serial = $Serial
    package = $Package
    screenshot_included = [bool]$IncludeScreenshot
} | ConvertTo-Json -Depth 3)
Write-Host "Sanitized emulator state written to: $outputDirectory"
