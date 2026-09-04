from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from .security import SecretRedactor


class EvidenceWriter:
    def __init__(self, directory: Path, redactor: SecretRedactor) -> None:
        self.directory = directory
        self.redactor = redactor
        self.directory.mkdir(parents=True, exist_ok=True)
        self._log_path = directory / "run.log"
        self._lock = threading.Lock()

    def log(self, event: str, **fields: Any) -> None:
        record = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "event": event,
            **fields,
        }
        line = json.dumps(self.redactor.object(record), ensure_ascii=False, default=str)
        with self._lock:
            with self._log_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def write_json(self, name: str, data: Any) -> None:
        payload = json.dumps(
            self.redactor.object(data), ensure_ascii=False, indent=2, default=str
        ).encode("utf-8")
        self._atomic_write(name, payload)

    def write_text(self, name: str, text: str, *, xml: bool = False) -> None:
        safe = self.redactor.xml(text) if xml else self.redactor.text(text)
        self._atomic_write(name, safe.encode("utf-8"))

    def _atomic_write(self, name: str, data: bytes) -> None:
        target = self.directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        pending = target.with_suffix(target.suffix + ".tmp")
        pending.write_bytes(data)
        pending.replace(target)


def create_evidence_directory(root: Path, run_id: str) -> Path:
    now = datetime.now().astimezone()
    # Keep the folder compact for Windows installations under deep OneDrive paths.
    # The full run_id remains in SQLite, logs, and result.json.
    timestamp = now.strftime("%H%M%S%f")[:-3]
    directory = root / now.date().isoformat() / f"{timestamp}_{run_id[:8]}"
    directory.mkdir(parents=True, exist_ok=False)
    return directory
