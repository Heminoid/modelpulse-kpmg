"""Score Distribution Analysis."""

import pandas as pd
from app.metrics.registry import MetricDefinition, register_metric
from app.schemas.metrics import MetricResult

def _calc_score_distribution(df: pd.DataFrame, mapped_roles: dict[str, list[str]], mapping, **kwargs) -> MetricResult:
    target_col = mapped_roles.get("target", [None])[0]
    score_col = mapped_roles.get("prediction_score", [None])[0]
    band_col = mapped_roles.get("score_band", [None])[0]
    
    if not target_col or target_col not in df.columns:
        return MetricResult(status="skipped", skipped_reason="Target required")
        
    group_col = band_col if band_col and band_col in df.columns else score_col
    if not group_col or group_col not in df.columns:
        return MetricResult(status="skipped", skipped_reason="Score or band required")
        
    df_temp = df.copy()
    if group_col == score_col:
        # If no explicit band column, bin into deciles
        ascending = True if mapping.score_direction == "lower_is_better" else False
        df_temp["_band"] = pd.qcut(df_temp[score_col].rank(method="first", ascending=ascending), 5, labels=False) + 1
        df_temp["_band"] = df_temp["_band"].apply(lambda x: f"Quintile {x}")
        group_col = "_band"
        
    # Make sure we process standard FICO-like bands correctly if they are strings like "<600", "600-700"
    def band_sort_key(b):
        b_str = str(b).strip()
        if b_str.startswith("<"): return 0
        if b_str.endswith("+"): return 9999
        try:
            return float(b_str.split("-")[0])
        except:
            return b_str
            
    bands = sorted(df_temp[group_col].dropna().unique(), key=band_sort_key)
    
    band_table = []
    tot_n = len(df_temp)
    
    for b in bands:
        sub = df_temp[df_temp[group_col] == b]
        n = len(sub)
        bad_rate = float(sub[target_col].mean()) if n > 0 else 0.0
        
        # Calculate approval rate if decision exists
        approval_rate = None
        decision_col = mapped_roles.get("decision", [None])[0]
        if decision_col and decision_col in df_temp.columns:
            # We don't have positive_label directly in mapped_roles, approximate it
            approvals = (sub[decision_col].astype(str).str.upper() == "APPROVED").mean()
            approval_rate = float(approvals)
            
        band_table.append({
            "band": b,
            "n": n,
            "pct_of_portfolio": float(n / tot_n) if tot_n > 0 else 0.0,
            "bad_rate": bad_rate,
            "approval_rate": approval_rate
        })
        
    if len(band_table) < 2:
        return MetricResult(status="ok", table_data=band_table)
        
    # Check monotonicity
    # If higher_is_better: bad_rate should DECREASE as score increases
    # If lower_is_better: bad_rate should INCREASE as score increases
    is_lower_better = (mapping.score_direction == "lower_is_better")
    
    monotonic = True
    for i in range(len(band_table) - 1):
        rate1 = band_table[i]["bad_rate"]
        rate2 = band_table[i+1]["bad_rate"]
        if is_lower_better:
            if rate1 > rate2:
                monotonic = False
                break
        else:
            if rate1 < rate2:
                monotonic = False
                break
                
    status = "ok" if monotonic else "critical"
    metadata = {}
    if not monotonic:
        metadata["finding"] = "Score rank-ordering is inverted/non-monotonic across bands. Review score definitions."
        
    return MetricResult(
        status=status,
        table_data=band_table,
        metadata=metadata if metadata else None
    )

register_metric(
    MetricDefinition(
        metric_key="score_distribution_analysis",
        display_name="Score Distribution Analysis",
        category="performance",
        description="Detailed score band analysis with monotonicity check",
        required_roles=["target", "prediction_score"],
        optional_roles=["score_band", "decision"],
        template_compatibility=["all"],
        output_type="table",
        chart_recommendation="none",
        threshold_support=False,
        calculation_fn=_calc_score_distribution,
    )
)
