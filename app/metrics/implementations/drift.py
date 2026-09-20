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

def _calc_feature_csi(df: pd.DataFrame, mapped_roles: dict[str, list[str]], 
                      baseline_df: pd.DataFrame | None = None,
                      baseline_stats: dict | None = None, **kwargs) -> MetricResult:
    """Calculate Characteristic Stability Index (CSI) for each numeric feature.
    
    Uses the pre-computed baseline histograms from BaselineStats.numeric_stats
    to measure feature-level distributional drift.
    """
    results = []
    
    if baseline_stats is None or not baseline_stats.get('numeric_stats'):
        return MetricResult(
            metric_key='csi_feature_drift',
            display_name='Feature CSI',
            category='drift',
            status='skipped',
            skipped_reason='No baseline stats available for CSI'
        )
    
    # Exclude non-feature columns (score, PD, target, record_id)
    non_feature_cols = set(mapped_roles.get('prediction_score', [])) | \
                       set(mapped_roles.get('prediction_probability', [])) | \
                       set(mapped_roles.get('target', [])) | \
                       set(mapped_roles.get('record_id', []))
    
    feature_results = []
    numeric_stats = baseline_stats['numeric_stats']
    
    for col_name, col_stats in numeric_stats.items():
        if col_name in non_feature_cols:
            continue
        
        if col_name not in df.columns:
            continue
            
        histogram = col_stats.get('histogram')
        if not histogram or not histogram.get('bin_edges') or not histogram.get('counts'):
            continue
        
        bin_edges = np.array(histogram['bin_edges'])
        baseline_counts = np.array(histogram['counts'])
        
        # Compute current histogram using same bin edges
        current_vals = df[col_name].dropna().values
        if len(current_vals) == 0:
            continue
        
        current_counts = np.histogram(current_vals, bins=bin_edges)[0]
        
        # Compute CSI (same formula as PSI)
        eps = 1e-4
        total_baseline = sum(baseline_counts)
        total_current = len(current_vals)
        
        if total_baseline == 0 or total_current == 0:
            continue
        
        baseline_pct = (baseline_counts / total_baseline) + eps
        current_pct = (current_counts / total_current) + eps
        
        csi = float(np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct)))
        
        status = 'ok'
        if csi > 0.25:
            status = 'critical'
        elif csi > 0.10:
            status = 'warning'
        
        feature_results.append({
            'feature': col_name,
            'csi_value': round(csi, 6),
            'status': status,
            'baseline_histogram': {
                'bin_edges': [round(e, 4) for e in bin_edges.tolist()],
                'counts': baseline_counts.tolist()
            },
            'current_histogram': {
                'bin_edges': [round(e, 4) for e in bin_edges.tolist()],
                'counts': current_counts.tolist()
            }
        })
    
    if not feature_results:
        return MetricResult(
            metric_key='csi_feature_drift',
            display_name='Feature CSI',
            category='drift',
            status='skipped',
            skipped_reason='No overlapping numeric feature columns between baseline and current dataset'
        )

    # Sort by CSI descending
    feature_results.sort(key=lambda x: x['csi_value'], reverse=True)

    # Create summary metric result
    max_csi = max((f['csi_value'] for f in feature_results), default=0.0)
    drifted_count = sum(1 for f in feature_results if f['status'] in ('warning', 'critical'))
    
    summary_status = 'ok'
    if any(f['status'] == 'critical' for f in feature_results):
        summary_status = 'critical'
    elif any(f['status'] == 'warning' for f in feature_results):
        summary_status = 'warning'
    
    summary_result = MetricResult(
        metric_key='csi_feature_drift',
        display_name='Feature CSI Drift',
        category='drift',
        status=summary_status,
        scalar_value=max_csi,
        scalar_label=f'{drifted_count} features drifted',
        table_data=feature_results
    )

    # Return summary metric plus individual feature CSI metrics
    out_results = [summary_result]
    for f in feature_results:
        col = f['feature']
        clean_name = col.replace('_', ' ').title()
        out_results.append(
            MetricResult(
                metric_key=f"csi_{col}",
                display_name=f"CSI ({clean_name})",
                category="drift",
                status=f['status'],
                scalar_value=f['csi_value'],
                metadata={
                    "baseline_histogram": f['baseline_histogram'],
                    "current_histogram": f['current_histogram']
                }
            )
        )
    return out_results

register_metric(
    MetricDefinition(
        metric_key='csi_feature_drift',
        display_name='Feature CSI Drift',
        category='drift',
        description='Characteristic Stability Index for each numeric feature',
        required_roles=[],
        optional_roles=[],
        template_compatibility=['all'],
        output_type='mixed',
        chart_recommendation='bar',
        threshold_support=False,
        calculation_fn=_calc_feature_csi,
    )
)
