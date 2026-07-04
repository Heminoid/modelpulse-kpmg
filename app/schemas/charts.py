"""Chart payload schemas."""

from typing import Any, Optional

from pydantic import BaseModel


class ChartPayload(BaseModel):
    """Canonical chart payload definition per Amendment A winner."""

    title: str
    chart_type: str  # e.g. "bar", "line", "scatter", "histogram", "heatmap"
    data: dict[str, Any]
    x_label: Optional[str] = None
    y_label: Optional[str] = None
    series_labels: Optional[list[str]] = None
    image_url: Optional[str] = None
