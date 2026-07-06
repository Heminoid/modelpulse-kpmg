from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict
from app.schemas.mapping import ColumnMapping


class MonitorConfig(BaseModel):
    model_config = ConfigDict(ser_json_timedelta="iso8601")

    monitor_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    template_type: str = "credit_scorecard_monitoring"
    dataset_id: str
    baseline_dataset_id: Optional[str] = None
    column_mapping: ColumnMapping
    selected_metrics: list[str] = []       # empty = use template defaults
    selected_segments: list[str] = []      # segment columns to break down
    score_direction: str = "higher_is_better"
    binning_strategy: str = "quantile"     # "quantile" or "equal_width"
    n_bins: int = 10
    thresholds: dict[str, float] = {}      # override default thresholds per metric
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
