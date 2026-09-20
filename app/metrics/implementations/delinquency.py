"""Delinquency Metrics."""

import pandas as pd

from app.metrics.registry import MetricDefinition, register_metric
from app.schemas.metrics import MetricResult


def _get_dpd_buckets(df: pd.DataFrame, mapped_roles: dict[str, list[str]]) -> dict[str, int]:
    dpd_col = mapped_roles["dpd_field"][0]
    clean_df = df[dpd_col].dropna()
    return {
        "Current": int((clean_df == 0).sum()),
        "1-29": int(((clean_df > 0) & (clean_df < 30)).sum()),
        "30-59": int(((clean_df >= 30) & (clean_df < 60)).sum()),
        "60-89": int(((clean_df >= 60) & (clean_df < 90)).sum()),
        "90+": int((clean_df >= 90).sum()),
    }


def _calc_dpd_buckets(df: pd.DataFrame, mapped_roles: dict[str, list[str]], **kwargs) -> MetricResult:
    buckets = _get_dpd_buckets(df, mapped_roles)
    table_data = [
        {"bucket": k, "count": v} for k, v in buckets.items()
    ]
    return MetricResult(
        metric_key="delinq_buckets",
        display_name="DPD Buckets",
        category="delinquency",
        status="ok",
        output_type="table",
        table_data=table_data,
    )


def _calc_delinq_severe_rate(df: pd.DataFrame, mapped_roles: dict[str, list[str]], **kwargs) -> MetricResult:
    buckets = _get_dpd_buckets(df, mapped_roles)
    total_count = sum(buckets.values())
    severe_rate = float(buckets.get("90+", 0)) / total_count if total_count > 0 else 0.0
    return MetricResult(
        metric_key="delinq_severe_rate",
        display_name="Severe Delinquency Rate",
        category="delinquency",
        status="ok",
        scalar_value=severe_rate,
    )


def _calc_delinq_30plus_rate(df: pd.DataFrame, mapped_roles: dict[str, list[str]], **kwargs) -> MetricResult:
    buckets = _get_dpd_buckets(df, mapped_roles)
    total_count = sum(buckets.values())
    rate_30plus = (
        float(buckets.get("30-59", 0) + buckets.get("60-89", 0) + buckets.get("90+", 0)) / total_count
        if total_count > 0
        else 0.0
    )
    return MetricResult(
        metric_key="delinq_30plus_rate",
        display_name="30+ DPD Rate",
        category="delinquency",
        status="ok",
        scalar_value=rate_30plus,
    )

register_metric(
    MetricDefinition(
        metric_key="delinq_buckets",
        display_name="DPD Buckets",
        category="delinquency",
        description="Counts of days past due in standard buckets",
        required_roles=["dpd_field"],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="table",
        chart_recommendation="bar",
        threshold_support=False,
        calculation_fn=_calc_dpd_buckets,
    )
)

register_metric(
    MetricDefinition(
        metric_key="delinq_severe_rate",
        display_name="Severe Delinquency Rate",
        category="delinquency",
        description="Percentage of rows in the 90+ DPD bucket",
        required_roles=["dpd_field"],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="scalar",
        chart_recommendation="none",
        threshold_support=True,
        calculation_fn=_calc_delinq_severe_rate,
    )
)

register_metric(
    MetricDefinition(
        metric_key="delinq_30plus_rate",
        display_name="30+ DPD Rate",
        category="delinquency",
        description="Percentage of rows in 30+ DPD buckets",
        required_roles=["dpd_field"],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="scalar",
        chart_recommendation="none",
        threshold_support=True,
        calculation_fn=_calc_delinq_30plus_rate,
    )
)
