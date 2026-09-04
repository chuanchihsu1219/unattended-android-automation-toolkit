from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .commands import CommandError, CommandRunner, start_background_process
from .evidence import EvidenceWriter


class EmulatorError(RuntimeError):
    pass


@dataclass(frozen=True)
class AndroidRuntimeConfig:
    sdk_root: Path
    avd_name: str
    runtime_root: Path
    serial: str = "emulator-5556"
    port: int = 5556
    timezone: str = "Asia/Taipei"
    boot_timeout_seconds: int = 240
    shutdown_timeout_seconds: int = 30


class AndroidEmulator:
    def __init__(
        self,
        config: AndroidRuntimeConfig,
        runner: CommandRunner,
        evidence: EvidenceWriter,
    ) -> None:
        self.config = config
        self.runner = runner
        self.evidence = evidence
        self.adb = config.sdk_root / "platform-tools" / "adb.exe"
        dedicated = config.sdk_root / "emulator" / "emulator-headless.exe"
        fallback = config.sdk_root / "emulator" / "emulator.exe"
        self.emulator = dedicated if dedicated.exists() else fallback
        self.process: Any = None
        self._stream: Any = None
        self.pid_file = config.runtime_root / "owned-emulator.json"

    def _adb(self, *args: str, timeout: int = 30, check: bool = True) -> str:
        result = self.runner.run(
            [self.adb, "-s", self.config.serial, *args], timeout=timeout, check=check
        )
        return result.stdout.strip()

    def _cleanup_owned_orphan(self) -> None:
        if not self.pid_file.exists():
            return
        try:
            record = json.loads(self.pid_file.read_text(encoding="utf-8"))
            pid = int(record["pid"])
            identity_matches = (
                record["avd_name"] == self.config.avd_name
                and record["serial"] == self.config.serial
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            self.pid_file.unlink(missing_ok=True)
            return
        if not identity_matches:
            self.evidence.log("orphan_ignored", reason="identity_mismatch")
            return
        try:
            self._adb("emu", "kill", timeout=10, check=False)
        finally:
            self.runner.run(
                ["taskkill.exe", "/PID", str(pid), "/T", "/F"],
                timeout=10,
                check=False,
            )
            self.pid_file.unlink(missing_ok=True)

    def start(self) -> None:
        if not self.adb.exists() or not self.emulator.exists():
            raise EmulatorError("Android SDK platform-tools and Emulator are required")
        self._cleanup_owned_orphan()
        arguments: list[str | os.PathLike[str]] = [
            self.emulator,
            "-avd",
            self.config.avd_name,
            "-port",
            str(self.config.port),
            "-no-audio",
            "-no-boot-anim",
            "-no-snapshot",
            "-timezone",
            self.config.timezone,
        ]
        if self.emulator.name.lower() != "emulator-headless.exe":
            arguments.append("-no-window")
        environment = os.environ.copy()
        environment.update(
            {
                "ANDROID_HOME": str(self.config.sdk_root),
                "ANDROID_SDK_ROOT": str(self.config.sdk_root),
                "QEMU_AUDIO_DRV": "none",
            }
        )
        self.process, self._stream = start_background_process(
            arguments,
            stdout_path=self.evidence.directory / "emulator.log",
            env=environment,
        )
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.pid_file.write_text(
            json.dumps(
                {
                    "pid": self.process.pid,
                    "avd_name": self.config.avd_name,
                    "serial": self.config.serial,
                }
            ),
            encoding="utf-8",
        )
        self._wait_for_boot()

    def _wait_for_boot(self) -> None:
        deadline = time.monotonic() + self.config.boot_timeout_seconds
        last_state = "not detected"
        while time.monotonic() < deadline:
            if self.process is not None and self.process.poll() is not None:
                raise EmulatorError(f"Emulator exited with code {self.process.returncode}")
            try:
                state = self._adb("get-state", timeout=5, check=False)
                boot = self._adb("shell", "getprop", "sys.boot_completed", timeout=5, check=False)
                packages = self._adb(
                    "shell", "cmd", "package", "list", "packages", timeout=10, check=False
                )
                connectivity = ""
                if state == "device" and boot == "1" and "package:" in packages:
                    connectivity = self._adb(
                        "shell", "dumpsys", "connectivity", timeout=10, check=False
                    )
                network_ready = "VALIDATED" in connectivity and "INTERNET" in connectivity
                last_state = (
                    f"state={state}, boot={boot}, packages={bool(packages)}, "
                    f"network={network_ready}"
                )
                if state == "device" and boot == "1" and "package:" in packages and network_ready:
                    self.ensure_awake()
                    self.evidence.log("emulator_boot_completed")
                    return
            except (CommandError, OSError) as error:
                last_state = str(error)
            time.sleep(2)
        raise EmulatorError(f"Emulator boot timeout: {last_state}")

    def ensure_awake(self) -> None:
        commands = (
            ("stay_on", ("shell", "svc", "power", "stayon", "true")),
            ("wake", ("shell", "input", "keyevent", "224")),
            ("dismiss_keyguard", ("shell", "wm", "dismiss-keyguard")),
        )
        for name, args in commands:
            last_error: Exception | None = None
            for attempt in range(1, 4):
                try:
                    self._adb(*args, timeout=15, check=False)
                    break
                except (CommandError, OSError) as error:
                    last_error = error
                    self.evidence.log(
                        "screen_wake_retry", command=name, attempt=attempt, error=str(error)
                    )
                    if attempt < 3:
                        time.sleep(1)
            else:
                raise EmulatorError(
                    f"Screen wake command {name} failed after 3 attempts: {last_error}"
                )

    def package_installed(self, package_name: str) -> bool:
        return self._adb(
            "shell", "pm", "path", package_name, timeout=15, check=False
        ).startswith("package:")

    def shell(self, *args: str, timeout: int = 30, check: bool = True) -> str:
        return self._adb("shell", *args, timeout=timeout, check=check)

    def shutdown(self) -> None:
        try:
            self._adb("emu", "kill", timeout=10, check=False)
        except Exception as error:
            self.evidence.log("emulator_shutdown_adb_failed", error=str(error))
        if self.process is not None:
            try:
                self.process.wait(timeout=self.config.shutdown_timeout_seconds)
            except Exception:
                self.runner.run(
                    ["taskkill.exe", "/PID", str(self.process.pid), "/T", "/F"],
                    timeout=10,
                    check=False,
                )
        if self._stream is not None:
            self._stream.close()
        self.pid_file.unlink(missing_ok=True)
