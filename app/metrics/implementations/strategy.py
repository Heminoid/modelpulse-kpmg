"""Strategy / Business Metrics."""

import pandas as pd

from app.metrics.registry import MetricDefinition, register_metric
from app.schemas.metrics import MetricResult


def _calc_approval_rate(df: pd.DataFrame, mapped_roles: dict[str, list[str]], mapping, **kwargs) -> MetricResult:
    decision_col = mapped_roles["decision"][0]
    approved_label = mapping.decision_positive_label
    
    clean_df = df[decision_col].dropna()
    if len(clean_df) == 0:
        return MetricResult(status="skipped", skipped_reason="Empty decision column")
        
    ar = (clean_df == approved_label).mean()
    return MetricResult(
        status="ok",
        scalar_value=float(ar),
    )

register_metric(
    MetricDefinition(
        metric_key="strategy_approval_rate",
        display_name="Approval Rate",
        category="strategy",
        description="Percentage of applications approved",
        required_roles=["decision"],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="scalar",
        chart_recommendation="none",
        threshold_support=True,
        calculation_fn=_calc_approval_rate,
    )
)


def _calc_bad_rate(df: pd.DataFrame, mapped_roles: dict[str, list[str]], **kwargs) -> MetricResult:
    target_col = mapped_roles["target"][0]
    
    clean_df = df[target_col].dropna()
    if len(clean_df) == 0:
        return MetricResult(status="skipped", skipped_reason="Empty target column")
        
    br = clean_df.mean()
    return MetricResult(
        status="ok",
        scalar_value=float(br),
    )

register_metric(
    MetricDefinition(
        metric_key="strategy_bad_rate",
        display_name="Overall Bad Rate",
        category="strategy",
        description="Overall realized default rate",
        required_roles=["target"],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="scalar",
        chart_recommendation="none",
        threshold_support=True,
        calculation_fn=_calc_bad_rate,
    )
)
