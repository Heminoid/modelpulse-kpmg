from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class BaselineStats(BaseModel):
    model_config = ConfigDict(ser_json_timedelta="iso8601")

    dataset_id: str
    computed_at: datetime
    row_count: int
    
    # Per-column statistics
    numeric_stats: dict = {}       # {col: {"mean", "std", "min", "max", "percentiles": [p10,..,p90], "histogram": {"bin_edges": [], "counts": []}}}
    categorical_stats: dict = {}   # {col: {"value_counts": {cat: pct}, "total": n}}
    
    score_decile_edges: list[float] = []   # 11 edges for 10 decile bins
    pd_decile_edges: list[float] = []
    
    # Computed metric values (for comparison)
    baseline_metrics: dict = {}    # {metric_key: scalar_value}
