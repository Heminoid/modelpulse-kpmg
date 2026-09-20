"""Calibration Metrics."""

import numpy as np
import pandas as pd

from app.metrics.registry import MetricDefinition, register_metric
from app.schemas.metrics import MetricResult


def _calc_brier_score(df: pd.DataFrame, mapped_roles: dict[str, list[str]], **kwargs) -> MetricResult:
    target_col = mapped_roles["target"][0]
    pd_col = mapped_roles["prediction_probability"][0]
    
    clean_df = df[[target_col, pd_col]].dropna()
    if len(clean_df) == 0:
        return MetricResult(status="skipped", skipped_reason="No overlapping data")
        
    brier = np.mean((clean_df[pd_col] - clean_df[target_col]) ** 2)
    brier_null = clean_df[target_col].mean() * (1 - clean_df[target_col].mean())
    if brier_null == 0:
        brier_skill_score = 0.0
    else:
        brier_skill_score = 1 - (brier / brier_null)
        
    return MetricResult(
        metric_key="calib_brier_score",
        display_name="Brier Skill Score",
        category="calibration",
        status="ok",
        scalar_value=float(brier_skill_score),
        metadata={"brier_score": float(brier), "brier_null": float(brier_null)}
    )

register_metric(
    MetricDefinition(
        metric_key="calib_brier_score",
        display_name="Brier Skill Score",
        category="calibration",
        description="Brier Skill Score (higher is better)",
        required_roles=["target", "prediction_probability"],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="scalar",
        chart_recommendation="none",
        threshold_support=True,
        calculation_fn=_calc_brier_score,
    )
)


def _calc_calib_summary(df: pd.DataFrame, mapped_roles: dict[str, list[str]], **kwargs) -> MetricResult:
    target_col = mapped_roles["target"][0]
    pd_col = mapped_roles["prediction_probability"][0]
    
    clean_df = df[[target_col, pd_col]].dropna()
    if len(clean_df) == 0:
        return MetricResult(status="skipped", skipped_reason="No overlapping data")
        
    realized_dr = clean_df[target_col].mean()
    avg_predicted_pd = clean_df[pd_col].mean()
    
    if avg_predicted_pd == 0:
        return MetricResult(status="error", skipped_reason="Average predicted PD is 0")
        
    ratio = float(realized_dr / avg_predicted_pd)
    
    status = "ok"
    if ratio < 0.6 or ratio > 1.5:
        status = "critical"
    elif ratio < 0.8 or ratio > 1.25:
        status = "warning"
        
    return MetricResult(
        metric_key="calib_summary",
        display_name="Calibration Ratio",
        category="calibration",
        status=status,
        scalar_value=ratio,
        metadata={"realized_dr": float(realized_dr), "avg_predicted_pd": float(avg_predicted_pd)}
    )

register_metric(
    MetricDefinition(
        metric_key="calib_summary",
        display_name="Calibration Ratio",
        category="calibration",
        description="Overall calibration ratio (Realized DR / Avg Predicted PD)",
        required_roles=["target", "prediction_probability"],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="scalar",
        chart_recommendation="none",
        threshold_support=True,
        calculation_fn=_calc_calib_summary,
    )
)
