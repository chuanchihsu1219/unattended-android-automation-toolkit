from datetime import datetime, timezone

from android_automation_toolkit.models import MetricSnapshot, ProductRule, RangeRule
from android_automation_toolkit.pipeline import CollectionPipeline
from android_automation_toolkit.storage import ObservationStore


class FakeDevice:
    def __init__(self, evidence) -> None:
        self.evidence = evidence
        self.shutdown_called = False

    def start(self) -> None:
        pass

    def shutdown(self) -> None:
        self.shutdown_called = True


class Adapter:
    name = "fixture"

    def __init__(self, cost: float) -> None:
        self.cost = cost

    def collect(self, device) -> MetricSnapshot:
        return MetricSnapshot(
            observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            subject="demo",
            metrics={"cost": self.cost, "energy": 10.0, "rate": 5.0},
        )


def create_pipeline(tmp_path, adapter: Adapter, devices: list[FakeDevice]):
    store = ObservationStore(tmp_path / "data.sqlite3")

    def factory(evidence):
        device = FakeDevice(evidence)
        devices.append(device)
        return device

    return store, CollectionPipeline(
        store=store,
        evidence_root=tmp_path / "evidence",
        device_factory=factory,
        adapter=adapter,
        range_rules=(RangeRule("cost", 0, 25_000),),
        product_rules=(ProductRule("cost", "energy", "rate"),),
    )


def test_validated_result_is_persisted_and_device_is_cleaned_up(tmp_path) -> None:
    devices: list[FakeDevice] = []
    store, pipeline = create_pipeline(tmp_path, Adapter(50), devices)
    outcome = pipeline.run()
    assert outcome.status == "SUCCESS"
    assert outcome.inserted
    assert len(store.current_observations()) == 1
    assert devices[0].shutdown_called


def test_invalid_result_never_reaches_canonical_storage(tmp_path) -> None:
    devices: list[FakeDevice] = []
    store, pipeline = create_pipeline(tmp_path, Adapter(12), devices)
    outcome = pipeline.run()
    assert outcome.status == "REJECTED"
    assert store.current_observations() == []
    assert devices[0].shutdown_called


class FailingAdapter:
    name = "failing"

    def collect(self, device):
        raise RuntimeError("simulated UI failure")


def test_failure_is_evidenced_and_cleanup_still_runs(tmp_path) -> None:
    devices: list[FakeDevice] = []
    store, pipeline = create_pipeline(tmp_path, FailingAdapter(), devices)
    outcome = pipeline.run()
    assert outcome.status == "FAILED"
    assert store.current_observations() == []
    assert devices[0].shutdown_called
    results = list((tmp_path / "evidence").rglob("result.json"))
    assert len(results) == 1
