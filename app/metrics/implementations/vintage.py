"""Vintage and Cohort Analysis."""

import pandas as pd
from pydantic import BaseModel, ConfigDict
from typing import Optional, Any

class RollRateBucket(BaseModel):
    bucket: str
    count: int
    pct: float
    cumulative_pct: Optional[float] = None

class RollRateMatrix(BaseModel):
    type: str
    note: str
    buckets: list[RollRateBucket]
    severe_delinquency_rate: float

class VintageResult(BaseModel):
    cohort_curves: Optional[list[Any]] = None
    reason: Optional[str] = None
    roll_rate_matrix: Optional[RollRateMatrix] = None

def _is_time_parseable(series: pd.Series) -> bool:
    """Returns False if all values are the same, or if <80% parse successfully."""
    if series.nunique() <= 1:
        return False
    try:
        parsed = pd.to_datetime(series, errors="coerce")
        return parsed.notna().mean() >= 0.8
    except:
        return False

def compute_roll_rate_matrix(df: pd.DataFrame, dpd_col: str) -> dict:
    def dpd_bucket(d: float) -> str:
        if pd.isna(d): return "Current (0 DPD)"
        if d == 0: return "Current (0 DPD)"
        elif d <= 29: return "1-29 DPD"
        elif d <= 59: return "30-59 DPD"
        elif d <= 89: return "60-89 DPD"
        else: return "90+ DPD"

    bucket_order = ["Current (0 DPD)", "1-29 DPD", "30-59 DPD", "60-89 DPD", "90+ DPD"]
    df_temp = df.copy()
    df_temp["_dpd_bucket"] = df_temp[dpd_col].apply(dpd_bucket)
    counts = df_temp["_dpd_bucket"].value_counts()
    
    n_total = len(df_temp)
    buckets = []
    cum_pct = 0.0
    for b in bucket_order:
        count = int(counts.get(b, 0))
        pct = round(count / n_total * 100, 2) if n_total > 0 else 0.0
        cum_pct += pct
        buckets.append(RollRateBucket(
            bucket=b,
            count=count,
            pct=pct,
            cumulative_pct=round(cum_pct, 2)
        ))
        
    sev_rate = round((df_temp[dpd_col] >= 90).mean(), 4) if pd.api.types.is_numeric_dtype(df_temp[dpd_col]) else 0.0
    
    return RollRateMatrix(
        type="cross_sectional_dpd_distribution",
        note="True roll rate matrix requires two time-snapshot datasets. This shows current DPD bucket distribution.",
        buckets=buckets,
        severe_delinquency_rate=sev_rate
    )

def run_vintage_analysis(df: pd.DataFrame, mapping) -> VintageResult:
    mapped_roles = {}
    for col, role in mapping.mappings.items():
        mapped_roles.setdefault(role, []).append(col)
        
    time_col = mapped_roles.get("event_time", [None])[0]
    dpd_col = mapped_roles.get("dpd_field", [None])[0] or mapped_roles.get("past_due_days", [None])[0]
    
    res = VintageResult()
    
    if dpd_col and dpd_col in df.columns:
        res.roll_rate_matrix = compute_roll_rate_matrix(df, dpd_col)
        
    if not time_col or time_col not in df.columns:
        res.reason = "event_time column not mapped or missing."
    elif not _is_time_parseable(df[time_col]):
        res.reason = "event_time column not parseable or contains single unique value — cohort analysis requires distinct origination dates"
    else:
        # Placeholder for real cohort curves if time is parseable
        res.cohort_curves = []
        
    return res
