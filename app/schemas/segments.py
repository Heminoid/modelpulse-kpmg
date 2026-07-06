from typing import Optional

from pydantic import BaseModel, ConfigDict


class SegmentResult(BaseModel):
    model_config = ConfigDict(ser_json_timedelta="iso8601")

    segment_column: str
    segment_value: str
    count: int
    share_pct: float            # share of total portfolio
    bad_rate: Optional[float] = None
    approval_rate: Optional[float] = None
    avg_prediction_score: Optional[float] = None
    avg_probability_of_default: Optional[float] = None
    avg_loan_amount: Optional[float] = None
    severe_dpd_rate: Optional[float] = None    # 90+ DPD rate
    
    # Baseline comparison (if baseline exists):
    baseline_count: Optional[int] = None
    baseline_share_pct: Optional[float] = None
    share_drift: Optional[float] = None        # current_share - baseline_share
    bad_rate_drift: Optional[float] = None     # current_bad_rate - baseline_bad_rate
    drift_status: Optional[str] = None         # "stable", "watch", "alert"
