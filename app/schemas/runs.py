from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RunMetadata(BaseModel):
    model_config = ConfigDict(ser_json_timedelta="iso8601")

    run_id: str
    monitor_id: str
    dataset_id: str
    baseline_dataset_id: Optional[str] = None
    status: str     # "pending", "running", "completed", "failed"
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    metrics_computed: list[str] = []
    metrics_skipped: list[str] = []
    metrics_failed: list[str] = []
    row_count: int = 0
    baseline_row_count: Optional[int] = None
    created_at: datetime
