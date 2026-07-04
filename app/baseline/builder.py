from datetime import datetime, timezone
import numpy as np
import pandas as pd

from app.schemas.baseline import BaselineStats
from app.schemas.mapping import ColumnMapping
from app.metrics.engine import run_metrics


def build_baseline_stats(dataset_id: str, df: pd.DataFrame, mapping: ColumnMapping) -> BaselineStats:
    """Builds and returns BaselineStats from a pandas DataFrame and its mapping."""
    
    numeric_stats = {}
    categorical_stats = {}
    
    # Process numeric columns (prediction_score, prediction_probability, feature_fields, dpd_field, amount_field)
    numeric_roles = ["prediction_score", "prediction_probability", "dpd_field", "amount_field"]
    numeric_cols = set(mapping.feature_fields)
    for role in numeric_roles:
        cols = mapping.mappings.get(role)
        if cols:
            numeric_cols.add(cols)
    # the mapping dict actually maps column_name -> role, so we need to reverse it or iterate over mappings
    for col, role in mapping.mappings.items():
        if role in numeric_roles:
            numeric_cols.add(col)
            
    for col in numeric_cols:
        if col not in df.columns:
            continue
        
        series = df[col].dropna()
        if len(series) == 0:
            continue
            
        try:
            # Basic stats
            p10, p20, p30, p40, p50, p60, p70, p80, p90 = np.percentile(series, [10, 20, 30, 40, 50, 60, 70, 80, 90])
            
            # Histogram (20 bins)
            counts, bin_edges = np.histogram(series, bins=20)
            
            numeric_stats[col] = {
                "mean": float(series.mean()),
                "std": float(series.std()),
                "min": float(series.min()),
                "max": float(series.max()),
                "percentiles": [float(p10), float(p20), float(p30), float(p40), float(p50), 
                                float(p60), float(p70), float(p80), float(p90)],
                "histogram": {
                    "bin_edges": [float(b) for b in bin_edges],
                    "counts": [int(c) for c in counts]
                }
            }
        except Exception:
            pass # Skip if not numeric
            
    # Process categorical columns (segment_fields, target, decision, score_band, risk_band)
    cat_roles = ["target", "decision", "score_band", "risk_band", "segment_field"]
    cat_cols = set(mapping.segment_fields)
    for col, role in mapping.mappings.items():
        if role in cat_roles:
            cat_cols.add(col)
            
    for col in cat_cols:
        if col not in df.columns:
            continue
            
        series = df[col].dropna()
        if len(series) == 0:
            continue
            
        vc = series.value_counts(normalize=True).to_dict()
        categorical_stats[col] = {
            "value_counts": {str(k): float(v) for k, v in vc.items()},
            "total": len(series)
        }
        
    # Decile edges for score and PD
    score_decile_edges = []
    pd_decile_edges = []
    
    score_col = None
    for col, role in mapping.mappings.items():
        if role == "prediction_score":
            score_col = col
            break
            
    if score_col and score_col in df.columns:
        s = df[score_col].dropna()
        if len(s) > 0:
            score_decile_edges = [float(x) for x in np.percentile(s, np.linspace(0, 100, 11))]
            
    pd_col = None
    for col, role in mapping.mappings.items():
        if role == "prediction_probability":
            pd_col = col
            break
            
    if pd_col and pd_col in df.columns:
        s = df[pd_col].dropna()
        if len(s) > 0:
            pd_decile_edges = [float(x) for x in np.percentile(s, np.linspace(0, 100, 11))]
            
    # Compute baseline metrics
    results = run_metrics(df, mapping, []) # empty keys = all defaults... wait, we need to specify keys or let it run all
    # Engine defaults to all registered if keys is empty? 
    # Let's run all metrics that don't need a baseline
    all_keys = [
        "data_quality_row_count", "data_quality_duplicate_count", "data_quality_null_rates",
        "data_quality_invalid_probability", "data_quality_invalid_target", "data_quality_readiness_summary",
        "dq_score_pd_coherence", "dq_band_consistency",
        "perf_auc", "perf_gini", "perf_ks", "perf_decile_table", 
        "calib_brier_score", "calib_summary",
        "strategy_approval_rate", "strategy_bad_rate",
        "delinq_buckets"
    ]
    metrics = run_metrics(df, mapping, all_keys)
    baseline_metrics = {m.metric_key: m.scalar_value for m in metrics if m.scalar_value is not None}
    
    return BaselineStats(
        dataset_id=dataset_id,
        computed_at=datetime.now(timezone.utc),
        row_count=len(df),
        numeric_stats=numeric_stats,
        categorical_stats=categorical_stats,
        score_decile_edges=score_decile_edges,
        pd_decile_edges=pd_decile_edges,
        baseline_metrics=baseline_metrics
    )
