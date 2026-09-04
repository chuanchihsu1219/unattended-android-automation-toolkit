from __future__ import annotations

import math
from collections.abc import Iterable

from .models import MetricSnapshot, ProductRule, RangeRule, ValidationResult


def validate_snapshot(
    snapshot: MetricSnapshot,
    *,
    range_rules: Iterable[RangeRule] = (),
    product_rules: Iterable[ProductRule] = (),
) -> ValidationResult:
    errors: list[str] = []
    checks: dict[str, object] = {"subject_present": bool(snapshot.subject.strip())}
    if not checks["subject_present"]:
        errors.append("subject is required")

    for rule in range_rules:
        value = snapshot.metrics.get(rule.metric)
        numeric = isinstance(value, (int, float)) and math.isfinite(float(value))
        in_range = bool(numeric and rule.minimum <= float(value) <= rule.maximum)
        checks[f"{rule.metric}_numeric"] = numeric
        checks[f"{rule.metric}_in_range"] = in_range
        if not numeric:
            errors.append(f"{rule.metric} is missing or non-numeric")
        elif not in_range:
            errors.append(
                f"{rule.metric}={value} is outside [{rule.minimum}, {rule.maximum}]"
            )

    for rule in product_rules:
        result = snapshot.metrics.get(rule.result_metric)
        factor_a = snapshot.metrics.get(rule.factor_a_metric)
        factor_b = snapshot.metrics.get(rule.factor_b_metric)
        values = (result, factor_a, factor_b)
        numeric = all(
            isinstance(value, (int, float)) and math.isfinite(float(value))
            for value in values
        )
        check_name = (
            f"{rule.result_metric}_matches_"
            f"{rule.factor_a_metric}_times_{rule.factor_b_metric}"
        )
        if not numeric:
            checks[check_name] = False
            errors.append(f"product rule {check_name} has missing or non-numeric input")
            continue
        expected = float(factor_a) * float(factor_b)
        difference = abs(float(result) - expected)
        tolerance = max(rule.absolute_tolerance, abs(expected) * rule.relative_tolerance)
        reconciles = difference <= tolerance
        checks[check_name] = reconciles
        checks[f"{check_name}_expected"] = expected
        checks[f"{check_name}_difference"] = difference
        checks[f"{check_name}_tolerance"] = tolerance
        if not reconciles:
            errors.append(
                f"{rule.result_metric} differs from expected product by {difference:.4f}"
            )

    return ValidationResult(passed=not errors, errors=tuple(errors), checks=checks)
