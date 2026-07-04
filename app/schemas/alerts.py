from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


DEFAULT_ALERT_THRESHOLDS = {
    # PSI thresholds
    "psi_model_score":                {"warning": 0.10, "critical": 0.25},
    "psi_probability_of_default":     {"warning": 0.10, "critical": 0.25},
    "csi_credit_score":               {"warning": 0.10, "critical": 0.25},
    "csi_debt_to_income":             {"warning": 0.10, "critical": 0.25},
    "csi_revolving_utilization":      {"warning": 0.10, "critical": 0.25},
    "csi_annual_income":              {"warning": 0.10, "critical": 0.25},

    # Performance thresholds (decline from baseline)
    "perf_auc":                       {"warning_decline": 0.03, "critical_decline": 0.05},
    "perf_gini":                      {"warning_decline": 0.05, "critical_decline": 0.08},
    "perf_ks":                        {"warning_decline": 0.03, "critical_decline": 0.05},

    # Calibration thresholds
    "calib_brier_score":              {"warning_increase": 0.02, "critical_increase": 0.05},
    "calib_ratio_overall":            {"warning_low": 0.80, "warning_high": 1.25, "critical_low": 0.60, "critical_high": 1.50},
    "calib_gap_per_bin":              {"warning": 0.03, "critical": 0.05},

    # Strategy thresholds (change from baseline)
    "strategy_approval_rate":         {"warning_change": 0.05, "critical_change": 0.10},
    "strategy_bad_rate_approved":     {"warning_increase": 0.02, "critical_increase": 0.05},
    "strategy_decline_rate":          {"warning_change": 0.05, "critical_change": 0.10},

    # Delinquency thresholds
    "delinq_severe_rate":             {"warning": 0.10, "critical": 0.20},
    "delinq_30plus_rate":             {"warning": 0.15, "critical": 0.25},

    # Data quality thresholds
    "data_quality_null_rate":         {"warning": 0.05, "critical": 0.20},
}


class Alert(BaseModel):
    model_config = ConfigDict(ser_json_timedelta="iso8601")

    alert_id: str
    run_id: str
    metric_key: str
    metric_display_name: str
    category: str   # "drift", "performance", "calibration", "strategy", "delinquency", "data_quality"
    severity: str   # "info", "warning", "critical"
    observed_value: float
    threshold_value: float
    message: str    
    triggered_at: datetime
