from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from .evidence import EvidenceWriter
from .security import SecretRedactor


CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class CommandError(RuntimeError):
    pass


class CommandRunner:
    def __init__(
        self,
        redactor: SecretRedactor,
        evidence: EvidenceWriter | None = None,
        default_timeout: int = 30,
    ) -> None:
        self.redactor = redactor
        self.evidence = evidence
        self.default_timeout = default_timeout

    def run(
        self,
        args: Sequence[str | os.PathLike[str]],
        *,
        timeout: int | None = None,
        check: bool = True,
        env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [str(arg) for arg in args]
        safe_command = [self.redactor.text(arg) for arg in command]
        if self.evidence:
            self.evidence.log("command_start", command=safe_command)
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout or self.default_timeout,
                check=False,
                env=dict(env) if env else None,
                creationflags=CREATE_NO_WINDOW,
            )
        except subprocess.TimeoutExpired as error:
            if self.evidence:
                self.evidence.log("command_timeout", command=safe_command)
            raise CommandError(f"Command timed out: {' '.join(safe_command)}") from error

        completed.stdout = self.redactor.text(completed.stdout)
        completed.stderr = self.redactor.text(completed.stderr)
        if self.evidence:
            self.evidence.log(
                "command_finish",
                command=safe_command,
                return_code=completed.returncode,
                stdout_tail=completed.stdout[-2000:],
                stderr_tail=completed.stderr[-2000:],
            )
        if check and completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "no output"
            raise CommandError(
                f"Command failed ({completed.returncode}): {' '.join(safe_command)}: {detail[-1000:]}"
            )
        return completed


def start_background_process(
    args: Sequence[str | os.PathLike[str]],
    *,
    stdout_path: Path,
    env: Mapping[str, str] | None = None,
) -> tuple[subprocess.Popen[bytes], object]:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stream = stdout_path.open("ab", buffering=0)
    process = subprocess.Popen(
        [str(arg) for arg in args],
        stdin=subprocess.DEVNULL,
        stdout=stream,
        stderr=subprocess.STDOUT,
        env=dict(env) if env else None,
        creationflags=CREATE_NO_WINDOW,
    )
    return process, stream
