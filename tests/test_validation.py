from datetime import datetime, timezone

from android_automation_toolkit.models import MetricSnapshot, ProductRule, RangeRule
from android_automation_toolkit.validation import validate_snapshot


def snapshot(cost: float = 50.0, energy: float = 10.0) -> MetricSnapshot:
    return MetricSnapshot(
        observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        subject="demo",
        metrics={"cost": cost, "energy": energy, "rate": 5.0},
    )


def test_valid_snapshot_reconciles() -> None:
    result = validate_snapshot(
        snapshot(),
        range_rules=(RangeRule("energy", 0, 500), RangeRule("rate", 0, 50)),
        product_rules=(ProductRule("cost", "energy", "rate"),),
    )
    assert result.passed
    assert not result.errors


def test_outlier_and_product_mismatch_are_rejected() -> None:
    result = validate_snapshot(
        snapshot(cost=20, energy=700),
        range_rules=(RangeRule("energy", 0, 500),),
        product_rules=(ProductRule("cost", "energy", "rate"),),
    )
    assert not result.passed
    assert len(result.errors) == 2
