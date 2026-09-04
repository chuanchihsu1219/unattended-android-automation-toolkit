from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from .evidence import EvidenceWriter
from .models import MetricSnapshot, ProductRule, RangeRule
from .pipeline import CollectionPipeline
from .storage import ObservationStore


class NoopDevice:
    def __init__(self, evidence: EvidenceWriter) -> None:
        self.evidence = evidence

    def start(self) -> None:
        self.evidence.log("synthetic_device_started")

    def shutdown(self) -> None:
        self.evidence.log("synthetic_device_shutdown")


class SyntheticEnergyAdapter:
    name = "synthetic-energy"

    def __init__(self, snapshot: MetricSnapshot) -> None:
        self.snapshot = snapshot

    def collect(self, device: NoopDevice) -> MetricSnapshot:
        device.evidence.log("synthetic_adapter_collected")
        return self.snapshot


def build_demo(output_root: Path) -> dict[str, object]:
    store = ObservationStore(output_root / "demo.sqlite3")
    evidence_root = output_root / "evidence"
    base = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    outcomes = []
    for offset, kwh in enumerate((8.4, 9.1, 8.9, 10.2, 11.0, 9.8, 10.6)):
        snapshot = MetricSnapshot(
            observed_at=base + timedelta(days=offset),
            subject="demo-unit",
            metrics={"cost": round(kwh * 5.0, 2), "energy": kwh, "rate": 5.0},
            context={"source": "synthetic", "sample": True},
        )
        pipeline = CollectionPipeline(
            store=store,
            evidence_root=evidence_root,
            device_factory=NoopDevice,
            adapter=SyntheticEnergyAdapter(snapshot),
            range_rules=(
                RangeRule("cost", 0, 25_000),
                RangeRule("energy", 0, 500),
                RangeRule("rate", 0.01, 50),
            ),
            product_rules=(ProductRule("cost", "energy", "rate"),),
        )
        outcomes.append(pipeline.run().as_dict())
    return {
        "status": "SUCCESS",
        "database": str(store.path),
        "run_count": store.run_count(),
        "current_observation_count": len(store.current_observations()),
        "outcomes": outcomes,
    }
