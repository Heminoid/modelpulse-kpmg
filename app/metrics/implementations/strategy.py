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


def _calc_bad_rate_approved(df: pd.DataFrame, mapped_roles: dict[str, list[str]], mapping, **kwargs) -> MetricResult:
    decision_col = mapped_roles["decision"][0]
    target_col = mapped_roles["target"][0]
    approved_label = mapping.decision_positive_label

    clean_df = df[[decision_col, target_col]].dropna()
    if len(clean_df) == 0:
        return MetricResult(status="skipped", skipped_reason="Empty decision/target columns")

    if clean_df[decision_col].dtype == object:
        is_approved = clean_df[decision_col].astype(str).str.upper() == str(approved_label).upper()
    else:
        is_approved = clean_df[decision_col] == 1

    approved = clean_df[is_approved]
    if len(approved) == 0:
        return MetricResult(status="skipped", skipped_reason="No approved records")

    br = float(approved[target_col].mean())
    return MetricResult(
        status="ok",
        scalar_value=br,
    )

register_metric(
    MetricDefinition(
        metric_key="strategy_bad_rate_approved",
        display_name="Bad Rate (Approved Only)",
        category="strategy",
        description="Realized default rate among approved accounts only",
        required_roles=["decision", "target"],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="scalar",
        chart_recommendation="none",
        threshold_support=True,
        calculation_fn=_calc_bad_rate_approved,
    )
)


def _calc_decline_rate(df: pd.DataFrame, mapped_roles: dict[str, list[str]], mapping, **kwargs) -> MetricResult:
    decision_col = mapped_roles["decision"][0]
    approved_label = mapping.decision_positive_label

    clean_df = df[decision_col].dropna()
    if len(clean_df) == 0:
        return MetricResult(status="skipped", skipped_reason="Empty decision column")

    if clean_df.dtype == object:
        is_approved = clean_df.astype(str).str.upper() == str(approved_label).upper()
    else:
        is_approved = clean_df == 1

    dr = float((~is_approved).mean())
    return MetricResult(
        status="ok",
        scalar_value=dr,
    )

register_metric(
    MetricDefinition(
        metric_key="strategy_decline_rate",
        display_name="Decline Rate",
        category="strategy",
        description="Percentage of applications declined",
        required_roles=["decision"],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="scalar",
        chart_recommendation="none",
        threshold_support=True,
        calculation_fn=_calc_decline_rate,
    )
)
