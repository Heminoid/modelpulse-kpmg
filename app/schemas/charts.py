"""Chart payload schemas."""

from typing import Any, Optional

from pydantic import BaseModel


class ChartSeries(BaseModel):
    name: str            # series label, e.g. "Current", "Baseline"
    data: list[dict]     # [{"x": "600-700", "y": 0.08}, ...]
    color: Optional[str] = None # hex color hint for frontend


class ChartPayload(BaseModel):
    """Canonical chart payload definition per Amendment A winner (Section 17 base)."""
    chart_id: str
    chart_type: str      # "bar", "line", "scatter", "histogram", "pie", "heatmap"
    title: str
    subtitle: Optional[str] = None
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    series: list[ChartSeries]
    annotations: Optional[list[dict]] = None    # threshold lines, reference points
    image_url: Optional[str] = None
