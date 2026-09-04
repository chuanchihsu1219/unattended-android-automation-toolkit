[CmdletBinding()]
param(
    [string]$AvdName = 'Automation_API36',
    [int]$Port = 5556,
    [string]$Package = '',
    [int]$BootTimeoutSeconds = 240,
    [switch]$CaptureState
)

$ErrorActionPreference = 'Stop'
$sdk = Join-Path $env:LOCALAPPDATA 'Android\Sdk'
$adb = Join-Path $sdk 'platform-tools\adb.exe'
$dedicatedHeadless = Join-Path $sdk 'emulator\emulator-headless.exe'
$normalEmulator = Join-Path $sdk 'emulator\emulator.exe'
$emulator = if (Test-Path -LiteralPath $dedicatedHeadless) { $dedicatedHeadless } else { $normalEmulator }
if (-not (Test-Path -LiteralPath $adb)) { throw "ADB not found: $adb" }
if (-not (Test-Path -LiteralPath $emulator)) { throw "Emulator not found: $emulator" }

$serial = "emulator-$Port"
$existing = (& $adb -s $serial get-state 2>$null | Out-String).Trim()
if ($existing -eq 'device') {
    throw "$serial is already running; refusing to take ownership of an existing device."
}

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$logRoot = Join-Path $projectRoot 'runtime\dev-tools\headless-boot'
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$stdout = Join-Path $logRoot "$stamp.stdout.log"
$stderr = Join-Path $logRoot "$stamp.stderr.log"
$arguments = @(
    '-avd', $AvdName,
    '-port', $Port,
    '-no-audio',
    '-no-boot-anim',
    '-no-snapshot',
    '-timezone', 'Asia/Taipei'
)
if ([IO.Path]::GetFileName($emulator) -ne 'emulator-headless.exe') { $arguments += '-no-window' }

$process = Start-Process -FilePath $emulator -ArgumentList $arguments -PassThru `
    -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr
$booted = $false
$networkValidated = $false
try {
    $deadline = (Get-Date).AddSeconds($BootTimeoutSeconds)
    do {
        Start-Sleep -Seconds 2
        $deviceState = (& $adb -s $serial get-state 2>$null | Out-String).Trim()
        $bootCompleted = (& $adb -s $serial shell getprop sys.boot_completed 2>$null | Out-String).Trim()
        & $adb -s $serial shell cmd package list packages 1>$null 2>$null
        $packageManagerReady = $LASTEXITCODE -eq 0
        if ($deviceState -eq 'device' -and $bootCompleted -eq '1' -and $packageManagerReady) {
            $connectivity = (& $adb -s $serial shell dumpsys connectivity 2>$null | Out-String)
            $networkValidated = $connectivity -match 'VALIDATED' -and $connectivity -match 'INTERNET'
        }
        $booted = $deviceState -eq 'device' -and $bootCompleted -eq '1' -and $packageManagerReady -and $networkValidated
    } while (-not $booted -and (Get-Date) -lt $deadline -and -not $process.HasExited)

    if (-not $booted) { throw "Headless boot gates did not pass within $BootTimeoutSeconds seconds." }
    & $adb -s $serial shell svc power stayon true | Out-Null
    & $adb -s $serial shell input keyevent 224 | Out-Null
    & $adb -s $serial shell wm dismiss-keyguard | Out-Null
    $packageInstalled = $null
    if ($Package) {
        $packageList = (& $adb -s $serial shell pm list packages $Package 2>$null | Out-String)
        $packageInstalled = $packageList -match [regex]::Escape("package:$Package")
    }
    if ($CaptureState) {
        & (Join-Path $PSScriptRoot 'capture-emulator-state.ps1') -Serial $serial -Package $Package
    }
    [ordered]@{
        status = 'PASS'
        avd = $AvdName
        serial = $serial
        pid = $process.Id
        adb_state = 'device'
        boot_completed = 1
        package_manager_ready = $true
        network_validated = $networkValidated
        package = $Package
        package_installed = $packageInstalled
    } | ConvertTo-Json -Depth 3
} finally {
    if (-not $process.HasExited) {
        & $adb -s $serial emu kill 2>$null | Out-Null
        try { Wait-Process -Id $process.Id -Timeout 15 -ErrorAction Stop } catch {
            if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
        }
    }
}
