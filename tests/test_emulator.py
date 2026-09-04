from unittest.mock import patch

from android_automation_toolkit.commands import CommandError
from android_automation_toolkit.emulator import AndroidEmulator


class Evidence:
    def __init__(self) -> None:
        self.events = []

    def log(self, event: str, **fields) -> None:
        self.events.append((event, fields))


@patch("android_automation_toolkit.emulator.time.sleep")
def test_screen_wake_retries_transient_adb_timeout(sleep) -> None:
    emulator = object.__new__(AndroidEmulator)
    emulator.evidence = Evidence()
    calls = []

    def fake_adb(*args, **kwargs):
        calls.append(args)
        if args[1:3] == ("svc", "power") and calls.count(args) == 1:
            raise CommandError("transient timeout")
        return ""

    emulator._adb = fake_adb
    emulator.ensure_awake()
    assert calls.count(("shell", "svc", "power", "stayon", "true")) == 2
    assert sleep.call_count == 1
