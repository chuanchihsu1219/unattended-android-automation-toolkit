from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .models import MetricSnapshot


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    error TEXT,
    evidence_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS observations (
    observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    observed_at TEXT NOT NULL,
    subject TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    context_json TEXT NOT NULL,
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    validated INTEGER NOT NULL CHECK (validated IN (0, 1)),
    is_current INTEGER NOT NULL CHECK (is_current IN (0, 1)),
    supersedes_id INTEGER REFERENCES observations(observation_id),
    repair_reason TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_current_validated_observation
ON observations(observed_at, subject)
WHERE validated = 1 AND is_current = 1;
"""


class ObservationStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def begin_run(self, run_id: str, evidence_path: Path) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO runs(run_id, started_at, status, evidence_path) VALUES (?, ?, ?, ?)",
                (run_id, datetime.now().astimezone().isoformat(), "RUNNING", str(evidence_path)),
            )

    def finish_run(self, run_id: str, status: str, error: str | None = None) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE runs SET finished_at = ?, status = ?, error = ? WHERE run_id = ?",
                (datetime.now().astimezone().isoformat(), status, error, run_id),
            )

    def insert_first_validated(
        self, snapshot: MetricSnapshot, run_id: str
    ) -> tuple[int, bool]:
        observed_at = snapshot.observed_at.isoformat()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT observation_id FROM observations
                WHERE observed_at = ? AND subject = ? AND validated = 1 AND is_current = 1
                """,
                (observed_at, snapshot.subject),
            ).fetchone()
            if existing:
                return int(existing["observation_id"]), False
            cursor = connection.execute(
                """
                INSERT INTO observations(
                    observed_at, subject, metrics_json, context_json, run_id,
                    validated, is_current
                ) VALUES (?, ?, ?, ?, ?, 1, 1)
                """,
                (
                    observed_at,
                    snapshot.subject,
                    json.dumps(snapshot.metrics, sort_keys=True),
                    json.dumps(snapshot.context, sort_keys=True, default=str),
                    run_id,
                ),
            )
            return int(cursor.lastrowid), True

    def supersede_validated(
        self, snapshot: MetricSnapshot, run_id: str, *, reason: str
    ) -> int:
        if not reason.strip():
            raise ValueError("repair reason is required")
        observed_at = snapshot.observed_at.isoformat()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT observation_id FROM observations
                WHERE observed_at = ? AND subject = ? AND validated = 1 AND is_current = 1
                """,
                (observed_at, snapshot.subject),
            ).fetchone()
            supersedes_id = int(existing["observation_id"]) if existing else None
            if supersedes_id is not None:
                connection.execute(
                    "UPDATE observations SET is_current = 0 WHERE observation_id = ?",
                    (supersedes_id,),
                )
            cursor = connection.execute(
                """
                INSERT INTO observations(
                    observed_at, subject, metrics_json, context_json, run_id,
                    validated, is_current, supersedes_id, repair_reason
                ) VALUES (?, ?, ?, ?, ?, 1, 1, ?, ?)
                """,
                (
                    observed_at,
                    snapshot.subject,
                    json.dumps(snapshot.metrics, sort_keys=True),
                    json.dumps(snapshot.context, sort_keys=True, default=str),
                    run_id,
                    supersedes_id,
                    reason.strip(),
                ),
            )
            return int(cursor.lastrowid)

    def current_observations(self) -> list[dict[str, object]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT observation_id, observed_at, subject, metrics_json, run_id
                FROM observations
                WHERE validated = 1 AND is_current = 1
                ORDER BY observed_at, subject
                """
            ).fetchall()
        return [
            {
                "observation_id": int(row["observation_id"]),
                "observed_at": str(row["observed_at"]),
                "subject": str(row["subject"]),
                "metrics": json.loads(row["metrics_json"]),
                "run_id": str(row["run_id"]),
            }
            for row in rows
        ]

    def run_count(self) -> int:
        with self.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0])
