"""Data Quality Metrics."""

import pandas as pd
from app.metrics.registry import MetricDefinition, register_metric
from app.schemas.metrics import MetricResult
from scipy.stats import spearmanr


def _calc_row_count(df: pd.DataFrame, **kwargs) -> MetricResult:
    return MetricResult(
        status="ok",
        scalar_value=float(len(df)),
    )

register_metric(
    MetricDefinition(
        metric_key="data_quality_row_count",
        display_name="Row Count",
        category="data_quality",
        description="Total number of rows in the dataset",
        required_roles=[],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="scalar",
        chart_recommendation="none",
        threshold_support=True,
        calculation_fn=_calc_row_count,
    )
)


def _calc_duplicate_count(df: pd.DataFrame, **kwargs) -> MetricResult:
    count = int(df.duplicated().sum())
    status = "warning" if count > 0 else "ok"
    return MetricResult(
        status=status,
        scalar_value=float(count),
    )

register_metric(
    MetricDefinition(
        metric_key="data_quality_duplicate_count",
        display_name="Duplicate Row Count",
        category="data_quality",
        description="Number of fully duplicated rows",
        required_roles=[],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="scalar",
        chart_recommendation="none",
        threshold_support=True,
        calculation_fn=_calc_duplicate_count,
    )
)


def _calc_null_rates(df: pd.DataFrame, **kwargs) -> MetricResult:
    mapping = kwargs.get("mapping")
    role_map = mapping.mappings if mapping else {}
    
    table_data = []
    has_warning = False
    
    for col in df.columns:
        null_count = int(df[col].isna().sum())
        null_pct = float(null_count / len(df))
        status = "warning" if null_pct > 0.05 else "ok"
        if status == "warning":
            has_warning = True
            
        table_data.append({
            "column": col,
            "null_count": null_count,
            "null_pct": null_pct,
            "role": role_map.get(col, "unmapped"),
            "status": status,
        })
        
    return MetricResult(
        status="warning" if has_warning else "ok",
        table_data=table_data,
    )

register_metric(
    MetricDefinition(
        metric_key="data_quality_null_rates",
        display_name="Null Rates",
        category="data_quality",
        description="Null rates across all columns",
        required_roles=[],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="table",
        chart_recommendation="none",
        threshold_support=False,
        calculation_fn=_calc_null_rates,
    )
)


def _calc_invalid_probability(df: pd.DataFrame, mapped_roles: dict[str, list[str]], **kwargs) -> MetricResult:
    col = mapped_roles["prediction_probability"][0]
    invalid = df[(df[col] < 0) | (df[col] > 1)]
    count = len(invalid)
    return MetricResult(
        status="error" if count > 0 else "ok",
        scalar_value=float(count),
    )

register_metric(
    MetricDefinition(
        metric_key="data_quality_invalid_probability",
        display_name="Invalid Probability Count",
        category="data_quality",
        description="Number of probabilities outside [0, 1]",
        required_roles=["prediction_probability"],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="scalar",
        chart_recommendation="none",
        threshold_support=True,
        calculation_fn=_calc_invalid_probability,
    )
)


def _calc_invalid_target(df: pd.DataFrame, mapped_roles: dict[str, list[str]], **kwargs) -> MetricResult:
    col = mapped_roles["target"][0]
    invalid = df[~df[col].isin([0, 1]) & df[col].notna()]
    count = len(invalid)
    return MetricResult(
        status="error" if count > 0 else "ok",
        scalar_value=float(count),
    )

register_metric(
    MetricDefinition(
        metric_key="data_quality_invalid_target",
        display_name="Invalid Target Count",
        category="data_quality",
        description="Number of targets not in {0, 1}",
        required_roles=["target"],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="scalar",
        chart_recommendation="none",
        threshold_support=True,
        calculation_fn=_calc_invalid_target,
    )
)


def _calc_readiness_summary(mapped_roles: dict[str, list[str]], **kwargs) -> MetricResult:
    all_roles = [
        "target", "prediction_score", "prediction_probability", 
        "decision", "record_id", "event_time", "dpd_field"
    ]
    table_data = []
    
    for role in all_roles:
        cols = mapped_roles.get(role, [])
        table_data.append({
            "role": role,
            "mapped_column": cols[0] if cols else None,
            "available": bool(cols),
            "warning": "Missing critical role" if not cols else None
        })
        
    return MetricResult(
        status="ok",
        table_data=table_data,
    )

register_metric(
    MetricDefinition(
        metric_key="data_quality_readiness_summary",
        display_name="Monitoring Readiness Summary",
        category="data_quality",
        description="Status of required roles",
        required_roles=[],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="table",
        chart_recommendation="none",
        threshold_support=False,
        calculation_fn=_calc_readiness_summary,
    )
)


def _calc_score_pd_coherence(df: pd.DataFrame, mapped_roles: dict[str, list[str]], mapping, **kwargs) -> MetricResult:
    score_col = mapped_roles["prediction_score"][0]
    pd_col = mapped_roles["prediction_probability"][0]
    
    clean_df = df[[score_col, pd_col]].dropna()
    if len(clean_df) < 10:
        return MetricResult(
            status="skipped",
            skipped_reason="Insufficient data for coherence test"
        )
        
    rho, _ = spearmanr(clean_df[score_col], clean_df[pd_col])
    
    # Evaluate based on configured score direction
    direction = mapping.score_direction
    status = "ok"
    finding = None
    
    if abs(rho) < 0.3:
        status = "critical"
        finding = "score and PD disagree"
    elif (direction == "higher_is_better" and rho > 0) or (direction == "lower_is_better" and rho < 0):
        # We expect higher_is_better -> negative correlation (higher score = lower risk = lower PD)
        # We expect lower_is_better -> positive correlation
        status = "critical"
        finding = "direction misconfigured"
        
    res = MetricResult(
        status=status,
        scalar_value=float(rho),
        scalar_label=f"Spearman ρ: {rho:.3f}",
    )
    if finding:
        res.metadata = {"finding": finding}
    return res

register_metric(
    MetricDefinition(
        metric_key="dq_score_pd_coherence",
        display_name="Score-PD Coherence",
        category="data_quality",
        description="Spearman correlation between prediction_score and prediction_probability",
        required_roles=["prediction_score", "prediction_probability"],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="scalar",
        chart_recommendation="none",
        threshold_support=False,
        calculation_fn=_calc_score_pd_coherence,
    )
)


def _calc_band_consistency(df: pd.DataFrame, mapped_roles: dict[str, list[str]], **kwargs) -> MetricResult:
    score_col = mapped_roles["prediction_score"][0]
    band_col = mapped_roles["score_band"][0]
    
    clean_df = df[[score_col, band_col]].dropna()
    if len(clean_df) < 10:
        return MetricResult(status="skipped", skipped_reason="Not enough data")
        
    # Derive bands empirically from quantiles or just standard 600, 700, 800 boundaries if known
    # Or just check if the band monotonically increases/decreases with score.
    # The spec F1: share of rows where the band column matches the band derived from the score.
    # Wait, derivation logic isn't fully defined. Let's assume standard boundaries for FICO-like:
    def _derive_band(s: float) -> str:
        if s < 600: return "<600"
        if s < 700: return "600-700"
        if s < 800: return "700-800"
        return "800+"
        
    derived = clean_df[score_col].apply(_derive_band)
    match_rate = (clean_df[band_col].astype(str).str.strip() == derived).mean()
    
    status = "warning" if match_rate < 0.95 else "ok"
    return MetricResult(
        status=status,
        scalar_value=float(match_rate),
    )

register_metric(
    MetricDefinition(
        metric_key="dq_band_consistency",
        display_name="Band Consistency",
        category="data_quality",
        description="Check if score_band matches score-derived bands",
        required_roles=["prediction_score", "score_band"],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="scalar",
        chart_recommendation="none",
        threshold_support=False,
        calculation_fn=_calc_band_consistency,
    )
)
