"""Metric definition and result schemas."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


@dataclass
class MetricDefinition:
    """Metadata and execution details for a single metric."""

    metric_key: str
    display_name: str
    category: str  # "data_quality", "drift", "performance", "calibration", "strategy", "delinquency"
    description: str
    required_roles: list[str]
    optional_roles: list[str]
    template_compatibility: list[str]
    output_type: str  # "scalar", "table", "chart_data", "mixed"
    chart_recommendation: str  # "bar", "line", "scatter", "histogram", "heatmap", "none"
    threshold_support: bool
    # Signature: (df: pd.DataFrame, mapped_cols: dict[str, list[str]], baseline_df: pd.DataFrame | None, **kwargs) -> MetricResult
    calculation_fn: Callable


class MetricResult(BaseModel):
    """Result of a computed metric."""

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    metric_key: str = ""
    display_name: str = ""
    category: str = ""
    status: str  # "ok", "warning", "critical", "skipped", "error"
    skipped_reason: Optional[str] = None
    scalar_value: Optional[float] = None
    scalar_label: Optional[str] = None
    table_data: Optional[list[dict[str, Any]]] = None
    chart_data: Optional[dict[str, Any]] = None  # Expected to match ChartPayload.model_dump()
    metadata: Optional[dict[str, Any]] = None
    threshold_breached: bool = False
    threshold_value: Optional[float] = None
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
