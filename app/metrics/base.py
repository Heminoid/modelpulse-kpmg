"""Metric engine shared utilities and base types."""

from typing import Any

from app.schemas.metrics import MetricResult


def build_skipped_result(
    metric_key: str, display_name: str, category: str, reason: str
) -> MetricResult:
    """Helper to return a skipped MetricResult."""
    return MetricResult(
        metric_key=metric_key,
        display_name=display_name,
        category=category,
        status="skipped",
        skipped_reason=reason,
    )
