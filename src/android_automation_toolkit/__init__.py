"""Reliability-first primitives for unattended Android automation on Windows."""

from .models import MetricSnapshot, PipelineOutcome, ProductRule, RangeRule, ValidationResult
from .pipeline import CollectionPipeline
from .storage import ObservationStore

__all__ = [
    "CollectionPipeline",
    "MetricSnapshot",
    "ObservationStore",
    "PipelineOutcome",
    "ProductRule",
    "RangeRule",
    "ValidationResult",
]
