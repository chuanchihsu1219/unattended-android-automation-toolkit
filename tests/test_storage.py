from datetime import datetime, timezone

from android_automation_toolkit.models import MetricSnapshot
from android_automation_toolkit.storage import ObservationStore


def make_snapshot(cost: float = 50.0) -> MetricSnapshot:
    return MetricSnapshot(
        observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        subject="demo",
        metrics={"cost": cost, "energy": cost / 5, "rate": 5.0},
    )


def begin(store: ObservationStore, run_id: str, tmp_path) -> None:
    store.begin_run(run_id, tmp_path / run_id)


def test_first_validated_success_wins(tmp_path) -> None:
    store = ObservationStore(tmp_path / "data.sqlite3")
    begin(store, "run-1", tmp_path)
    first_id, inserted = store.insert_first_validated(make_snapshot(), "run-1")
    begin(store, "run-2", tmp_path)
    repeated_id, repeated_inserted = store.insert_first_validated(make_snapshot(55), "run-2")
    assert inserted
    assert not repeated_inserted
    assert repeated_id == first_id
    assert len(store.current_observations()) == 1


def test_manual_repair_supersedes_without_deleting_history(tmp_path) -> None:
    store = ObservationStore(tmp_path / "data.sqlite3")
    begin(store, "run-1", tmp_path)
    first_id, _ = store.insert_first_validated(make_snapshot(), "run-1")
    begin(store, "run-2", tmp_path)
    repaired_id = store.supersede_validated(make_snapshot(55), "run-2", reason="invoice")
    assert repaired_id != first_id
    assert store.current_observations()[0]["metrics"]["cost"] == 55
    with store.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 2
