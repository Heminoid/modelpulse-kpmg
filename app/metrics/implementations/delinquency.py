"""Delinquency Metrics."""

import pandas as pd

from app.metrics.registry import MetricDefinition, register_metric
from app.schemas.metrics import MetricResult


def _calc_dpd_buckets(df: pd.DataFrame, mapped_roles: dict[str, list[str]], **kwargs) -> MetricResult:
    dpd_col = mapped_roles["dpd_field"][0]
    
    clean_df = df[dpd_col].dropna()
    
    buckets = {
        "Current": (clean_df == 0).sum(),
        "1-29": ((clean_df > 0) & (clean_df < 30)).sum(),
        "30-59": ((clean_df >= 30) & (clean_df < 60)).sum(),
        "60-89": ((clean_df >= 60) & (clean_df < 90)).sum(),
        "90+": (clean_df >= 90).sum(),
    }
    
    table_data = [
        {"bucket": k, "count": int(v)} for k, v in buckets.items()
    ]
    
    return MetricResult(
        status="ok",
        table_data=table_data,
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
