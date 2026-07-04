"""Performance Metrics."""

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.metrics import confusion_matrix, roc_auc_score

from app.metrics.registry import MetricDefinition, register_metric
from app.schemas.metrics import MetricResult


def _calc_auc(df: pd.DataFrame, mapped_roles: dict[str, list[str]], mapping, **kwargs) -> MetricResult:
    target_col = mapped_roles["target"][0]
    
    # Prefer Score, else use PD
    if "prediction_score" in mapped_roles:
        score_col = mapped_roles["prediction_score"][0]
        scores = df[score_col]
        # Invert score if higher_is_better since sklearn roc_auc assumes higher score = higher risk
        if mapping.score_direction == "higher_is_better":
            scores = -scores
    elif "prediction_probability" in mapped_roles:
        score_col = mapped_roles["prediction_probability"][0]
        scores = df[score_col]
    else:
        return MetricResult(status="skipped", skipped_reason="No score or PD mapped")
        
    clean_mask = df[target_col].notna() & scores.notna()
    y_true = df.loc[clean_mask, target_col]
    y_score = scores[clean_mask]
    
    if len(y_true) == 0 or y_true.nunique() < 2:
        return MetricResult(status="skipped", skipped_reason="Target needs exactly 2 classes")
        
    positives = y_true.sum()
    if positives < 30:
        # Just a warning note
        pass
        
    auc = float(roc_auc_score(y_true, y_score))
    
    status = "ok"
    finding = None
    
    # Expert additions
    if auc < 0.5:
        status = "critical"
        finding = "Score rank-ordering is inverted vs the configured score direction — model may be broken or direction misconfigured; review mapping."
    elif auc > 0.97:
        status = "warning"
        finding = "suspiciously perfect discrimination — check target leakage / post-outcome features"
        
    res = MetricResult(
        status=status,
        scalar_value=auc,
    )
    if finding:
        res.metadata = {"finding": finding}
    return res

register_metric(
    MetricDefinition(
        metric_key="perf_auc",
        display_name="ROC AUC",
        category="performance",
        description="Area Under the Receiver Operating Characteristic Curve",
        required_roles=["target"],
        optional_roles=["prediction_probability", "prediction_score"],
        template_compatibility=["all"],
        output_type="scalar",
        chart_recommendation="none",
        threshold_support=True,
        calculation_fn=_calc_auc,
    )
)


def _calc_gini(df: pd.DataFrame, mapped_roles: dict[str, list[str]], mapping, **kwargs) -> MetricResult:
    auc_res = _calc_auc(df, mapped_roles, mapping, **kwargs)
    if auc_res.status == "skipped":
        return auc_res
        
    gini = 2 * auc_res.scalar_value - 1
    return MetricResult(
        status=auc_res.status,
        scalar_value=gini,
        metadata=auc_res.metadata,
    )

register_metric(
    MetricDefinition(
        metric_key="perf_gini",
        display_name="Gini Coefficient",
        category="performance",
        description="Gini Coefficient (2*AUC - 1)",
        required_roles=["target"],
        optional_roles=["prediction_probability", "prediction_score"],
        template_compatibility=["all"],
        output_type="scalar",
        chart_recommendation="none",
        threshold_support=True,
        calculation_fn=_calc_gini,
    )
)


def _calc_ks(df: pd.DataFrame, mapped_roles: dict[str, list[str]], mapping, **kwargs) -> MetricResult:
    target_col = mapped_roles["target"][0]
    
    if "prediction_score" in mapped_roles:
        score_col = mapped_roles["prediction_score"][0]
    elif "prediction_probability" in mapped_roles:
        score_col = mapped_roles["prediction_probability"][0]
    else:
        return MetricResult(status="skipped", skipped_reason="No score or PD mapped")
        
    clean_df = df[[target_col, score_col]].dropna()
    good_scores = clean_df.loc[clean_df[target_col] == 0, score_col].values
    bad_scores = clean_df.loc[clean_df[target_col] == 1, score_col].values
    
    if len(good_scores) == 0 or len(bad_scores) == 0:
        return MetricResult(status="skipped", skipped_reason="Missing good or bad instances")
        
    ks_stat, _ = ks_2samp(good_scores, bad_scores)
    # The KS stat is absolute, but F3 implies direction should be respected.
    # To respect direction, we could compute the signed KS, but ks_2samp gives the absolute max distance.
    # For now, return ks_stat as requested.
    
    return MetricResult(
        status="ok",
        scalar_value=float(ks_stat),
    )

register_metric(
    MetricDefinition(
        metric_key="perf_ks",
        display_name="KS Statistic",
        category="performance",
        description="Kolmogorov-Smirnov Statistic",
        required_roles=["target"],
        optional_roles=["prediction_probability", "prediction_score"],
        template_compatibility=["all"],
        output_type="scalar",
        chart_recommendation="none",
        threshold_support=True,
        calculation_fn=_calc_ks,
    )
)


def _calc_decile_table(df: pd.DataFrame, mapped_roles: dict[str, list[str]], mapping, **kwargs) -> MetricResult:
    target_col = mapped_roles["target"][0]
    score_col = mapped_roles["prediction_score"][0]
    
    clean_df = df[[target_col, score_col]].dropna().copy()
    if len(clean_df) < 10:
        return MetricResult(status="skipped", skipped_reason="Insufficient data")
        
    # Per amendment C5: rank first
    # Sort by model_score descending so highest score = decile 1.
    # Wait, if lower_is_better, ascending=True.
    ascending = True if mapping.score_direction == "lower_is_better" else False
    
    clean_df["decile"] = pd.qcut(
        clean_df[score_col].rank(method="first", ascending=ascending), 
        10, 
        labels=False
    ) + 1
    
    overall_bad_rate = clean_df[target_col].mean()
    
    table_data = []
    cum_bads = 0
    cum_goods = 0
    tot_bads = clean_df[target_col].sum()
    tot_goods = len(clean_df) - tot_bads
    
    for d in range(1, 11):
        d_df = clean_df[clean_df["decile"] == d]
        n = len(d_df)
        bads = int(d_df[target_col].sum())
        goods = n - bads
        
        cum_bads += bads
        cum_goods += goods
        
        bad_rate = float(bads / n) if n > 0 else 0.0
        lift = float(bad_rate / overall_bad_rate) if overall_bad_rate > 0 else 0.0
        
        table_data.append({
            "decile": d,
            "n": n,
            "n_bads": bads,
            "n_goods": goods,
            "bad_rate": bad_rate,
            "cumulative_bad_pct": float(cum_bads / tot_bads) if tot_bads > 0 else 0.0,
            "cumulative_good_pct": float(cum_goods / tot_goods) if tot_goods > 0 else 0.0,
            "lift": lift,
        })
        
    return MetricResult(
        status="ok",
        table_data=table_data,
    )

register_metric(
    MetricDefinition(
        metric_key="perf_decile_table",
        display_name="Decile Table",
        category="performance",
        description="Performance split by score deciles",
        required_roles=["target", "prediction_score"],
        optional_roles=[],
        template_compatibility=["all"],
        output_type="table",
        chart_recommendation="none",
        threshold_support=False,
        calculation_fn=_calc_decile_table,
    )
)
