from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class MetricSnapshot:
    observed_at: datetime
    subject: str
    metrics: dict[str, float]
    context: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "observed_at": self.observed_at.isoformat(),
            "subject": self.subject,
            "metrics": dict(self.metrics),
            "context": dict(self.context),
        }


@dataclass(frozen=True)
class RangeRule:
    metric: str
    minimum: float
    maximum: float


@dataclass(frozen=True)
class ProductRule:
    result_metric: str
    factor_a_metric: str
    factor_b_metric: str
    absolute_tolerance: float = 1.0
    relative_tolerance: float = 0.02


@dataclass(frozen=True)
class ValidationResult:
    passed: bool
    errors: tuple[str, ...]
    checks: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PipelineOutcome:
    run_id: str
    status: str
    inserted: bool = False
    observation_id: int | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
