# Development tools

These PowerShell tools support discovery and reliability testing on Windows.

```powershell
# Verify headless AVD boot, package manager, and validated network.
.\scripts\dev\test-headless-boot.ps1 -AvdName Automation_API36

# Capture redacted diagnostics from a running, explicitly selected serial.
.\scripts\dev\capture-emulator-state.ps1 -Package com.example.app

# Audit a registered task's sleep, battery, logon, and retry settings.
.\scripts\dev\check-task-recovery.ps1
```

Safety boundaries:

- Every ADB call is scoped to one serial.
- The capture tool redacts local `.env` values and disables screenshots by default.
- Live capture refuses to compete with a collector-owned Emulator unless explicitly overridden.
- The boot test refuses to adopt an existing serial and shuts down only its own PID.
