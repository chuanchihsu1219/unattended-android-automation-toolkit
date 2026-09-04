# Development playbook

## Build sequence

1. Write the data contract and canonical identity before opening the app.
2. Install official Android SDK tools and create a dedicated AVD.
3. Perform the authorized app-install and authentication checkpoint visibly.
4. Capture activity, package version, sanitized XML, and screenshots safe for the target state.
5. Model named UI states and transitions instead of a long click script.
6. Implement validation and persistence against fixtures before live collection.
7. Add headless lifecycle management, timeouts, ownership, and evidence.
8. Register the schedule only after a manual end-to-end run passes.
9. Inject selector, network, workbook-lock, and sleep failures.

## Selector priority

Use the first stable option available:

1. Resource ID or accessibility identifier.
2. Hierarchy-relative selector anchored to a stable label.
3. Deterministic text plus a verified screen state.
4. Fixed-region local OCR with numeric and state validation.

Do not retain a UI object across a screen transition. Query it again after the hierarchy changes.

## State machine pattern

```text
launch
  ├─ onboarding ──> select language ──> continue
  ├─ verification ──> submit authorized identifier
  ├─ login ──> submit local credentials
  ├─ loading ──> wait
  ├─ system dialog ──> handle only an explicitly recognized action
  ├─ network error ──> bounded retry or fail
  └─ data screen ──> extract ──> validate
```

Each state needs a positive recognition rule, bounded timeout, allowed transitions, and safe evidence policy.

## Failure modes observed in practice

| Symptom | Likely cause | Stable response | Acceptance check |
|---|---|---|---|
| ADB reports `offline` | The process exists but adbd is not ready | Poll; do not equate process existence with boot | `get-state=device` |
| Package command fails after boot property is `1` | Android framework services are still starting | Require package manager responsiveness | Package list contains entries |
| App reports no network | Android booted before the default network was validated | Add a connectivity gate | `VALIDATED` and `INTERNET` are present |
| Headless screenshot is black | Screen timeout or keyguard | Stay-on, wake keyevent, dismiss keyguard | App nodes are visible in hierarchy |
| One ADB shell command times out after cold boot | uiautomator or framework startup temporarily congested shell | Use bounded retry for idempotent wake commands | Retry recovers within the run limit |
| System UI ANR appears | Cold AVD service pressure | Handle only the exact recognized wait action | Dialog action is evidenced |
| Login button cannot be clicked | Soft keyboard changed layout and old bounds are stale | Close keyboard and query selector again | Data state appears within timeout |
| `StaleObjectException` | Reused UI object after hierarchy rebuild | Query after every state transition | Repeated run remains stable |
| Login disappears after shutdown | Confused Quick Boot snapshots with userdata persistence | Fix userdata path and support safe re-authentication | Cold-boot end-to-end passes |
| A retry duplicates data | Write path lacks a canonical identity | Partial unique index and first-success semantics | Repeated run returns existing ID |
| Workbook update fails | Excel holds a Windows file lock | Pending file, verification, atomic replace, deferred publish | Database succeeds; prior workbook stays valid |
| Lid close creates a gap | Trigger was missed or run was interrupted by sleep | Wake, start-when-available, logon, bounded restart | Resume audit and next eligible run succeed |
| Evidence write fails near 260 characters | Deep project path plus full UUID and temporary suffix reaches the legacy Windows path limit | Use a compact evidence folder and keep the full run ID inside metadata and SQLite | Atomic evidence files succeed under a deep OneDrive path |

## Evidence policy

Every real attempt should have its own directory:

```text
metadata.json
run.log
extraction.json
validation.json
result.json
activity.txt
package.txt
connectivity.txt
logcat.txt
traceback.txt          # failure only
hierarchy_*.xml        # only after redaction
screen_*.png           # never for authentication states
```

Redaction must be applied to values, keyed objects, XML attributes, exceptions, and subprocess arguments before they reach disk.

## Scheduling checklist

- One hidden `pythonw.exe` entry point.
- `MultipleInstances=IgnoreNew` plus a process-level mutex.
- Execution time limit longer than the application's bounded worst case.
- `WakeToRun` and `StartWhenAvailable`.
- Explicit battery behavior.
- Logon trigger for reboot recovery without storing a Windows password.
- Retry-on-failure with bounded count and interval.
- Program-level local-time window check to reject dangerous delayed runs.

## New-adapter checklist

- Confirm authorization and target terms.
- Install only from an official source.
- Record package and version.
- Define each screen state and allowed transition.
- Identify selectors from resource IDs before text or OCR.
- Define identity and numeric validation rules.
- Test cold boot, expired session, network loss, selector change, and app error dialogs.
- Verify no Windows input events and no unrelated process termination.
- Scan the full Git history before publication.
