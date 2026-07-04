import pandas as pd
from typing import Optional

from app.schemas.segments import SegmentResult
from app.schemas.mapping import ColumnMapping
from app.schemas.baseline import BaselineStats


def compute_segments(df: pd.DataFrame, mapping: ColumnMapping, selected_segments: list[str], baseline_stats: Optional[BaselineStats] = None) -> list[SegmentResult]:
    """Computes SegmentResult for each selected segment column."""
    
    results = []
    
    # We need target, decision, score, pd, amount, dpd cols
    target_col = None
    decision_col = None
    score_col = None
    pd_col = None
    amount_col = None
    dpd_col = None
    
    for col, role in mapping.mappings.items():
        if role == "target": target_col = col
        if role == "decision": decision_col = col
        if role == "prediction_score": score_col = col
        if role == "prediction_probability": pd_col = col
        if role == "amount_field": amount_col = col
        if role == "dpd_field": dpd_col = col

    decision_pos = mapping.decision_positive_label

    total_rows = len(df)
    if total_rows == 0:
        return []

    for seg_col in selected_segments:
        if seg_col not in df.columns:
            continue
            
        grouped = df.groupby(seg_col)
        
        for val, group in grouped:
            n = len(group)
            share = n / total_rows
            
            bad_rate = None
            if target_col and target_col in group.columns:
                bad_rate = float(group[target_col].mean())
                
            approval_rate = None
            if decision_col and decision_col in group.columns:
                approval_rate = float((group[decision_col] == decision_pos).mean())
                
            avg_score = None
            if score_col and score_col in group.columns:
                avg_score = float(group[score_col].mean())
                
            avg_pd = None
            if pd_col and pd_col in group.columns:
                avg_pd = float(group[pd_col].mean())
                
            avg_amount = None
            if amount_col and amount_col in group.columns:
                avg_amount = float(group[amount_col].mean())
                
            severe_dpd = None
            if dpd_col and dpd_col in group.columns:
                severe_dpd = float((group[dpd_col] >= 90).mean())
                
            res = SegmentResult(
                segment_column=seg_col,
                segment_value=str(val),
                count=n,
                share_pct=share,
                bad_rate=bad_rate,
                approval_rate=approval_rate,
                avg_model_score=avg_score,
                avg_probability_of_default=avg_pd,
                avg_loan_amount=avg_amount,
                severe_dpd_rate=severe_dpd
            )
            
            # Baseline comparison
            if baseline_stats and seg_col in baseline_stats.categorical_stats:
                bs_cat = baseline_stats.categorical_stats[seg_col]
                b_share = bs_cat.get("value_counts", {}).get(str(val), 0.0)
                b_count = int(b_share * bs_cat.get("total", 0))
                
                res.baseline_count = b_count
                res.baseline_share_pct = b_share
                res.share_drift = share - b_share
                
                # We do not have baseline bad rate per segment stored yet. Wait, the spec says SegmentResult has baseline_bad_rate?
                # "bad_rate_drift: current_bad_rate - baseline_bad_rate"
                # If we don't have it, we can't compute drift for bad rate unless we store it.
                # Let's check BaselineStats schema again. It only has categorical_stats (value_counts). 
                # So we might not have bad_rate_drift unless we compute it at baseline time. 
                # For now, drift_status based on share.
                if abs(res.share_drift) > 0.05:
                    res.drift_status = "alert"
                elif abs(res.share_drift) > 0.02:
                    res.drift_status = "watch"
                else:
                    res.drift_status = "stable"
                    
            results.append(res)
            
    return results
