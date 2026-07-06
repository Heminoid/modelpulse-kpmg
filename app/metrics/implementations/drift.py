"""Drift Metrics (PSI/CSI)."""

import numpy as np
import pandas as pd

from app.metrics.registry import MetricDefinition, register_metric
from app.schemas.metrics import MetricResult


def _compute_psi(
    baseline_vals: np.ndarray, current_vals: np.ndarray, n_bins: int = 10, eps: float = 1e-4
) -> tuple[float, list[dict], str]:
    """Population Stability Index."""
    quantiles = np.linspace(0, 100, n_bins + 1)
    bin_edges = np.percentile(baseline_vals, quantiles)
    bin_edges = np.unique(bin_edges)
    
    # B5: PSI degenerate-bins guard
    if len(bin_edges) < 3:
        return 0.0, [], "insufficient value variation for binning"
        
    bin_edges[0] = -np.inf
    bin_edges[-1] = np.inf

    baseline_counts = np.histogram(baseline_vals, bins=bin_edges)[0]
    current_counts = np.histogram(current_vals, bins=bin_edges)[0]

    baseline_pct = (baseline_counts / len(baseline_vals)) + eps
    current_pct = (current_counts / len(current_vals)) + eps

    psi = np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct))
    
    bin_results = [
        {
            "bin": i + 1,
            "range": f"{bin_edges[i]:.2f}–{bin_edges[i+1]:.2f}",
            "baseline_pct": float(baseline_pct[i] * 100),
            "current_pct": float(current_pct[i] * 100),
            "psi_contribution": float((current_pct[i] - baseline_pct[i]) * np.log(current_pct[i] / baseline_pct[i]))
        }
        for i in range(len(baseline_counts))
    ]
    
    return float(psi), bin_results, ""


def _calc_score_psi(df: pd.DataFrame, mapped_roles: dict[str, list[str]], baseline_df: pd.DataFrame | None = None, **kwargs) -> MetricResult:
    if baseline_df is None:
        return MetricResult(status="skipped", skipped_reason="No baseline provided")
        
    score_col = mapped_roles["prediction_score"][0]
    
    b_vals = baseline_df[score_col].dropna().values
    c_vals = df[score_col].dropna().values
    
    if len(b_vals) == 0 or len(c_vals) == 0:
        return MetricResult(status="skipped", skipped_reason="Empty score array")
        
    n_bins = 5 if len(b_vals) < 200 else 10
    psi, bins, reason = _compute_psi(b_vals, c_vals, n_bins=n_bins)
    
    if reason:
        return MetricResult(status="skipped", skipped_reason=reason)
        
    status = "ok"
    if psi > 0.25:
        status = "critical"
    elif psi > 0.10:
        status = "warning"
        
    return MetricResult(
        status=status,
        scalar_value=psi,
        table_data=bins,
    )

register_metric(
    MetricDefinition(
        metric_key="psi_prediction_score",
        display_name="Score PSI",
        category="drift",
        description="Population Stability Index for model score",
        required_roles=["prediction_score"],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="mixed",
        chart_recommendation="bar",
        threshold_support=True,
        calculation_fn=_calc_score_psi,
    )
)
