"""Override Analysis."""

import pandas as pd
from app.schemas.override import OverrideAnalysis
from app.schemas.mapping import ColumnMapping

def run_override_analysis(df: pd.DataFrame, mapping: ColumnMapping, score_cutoff: float = 600) -> OverrideAnalysis:
    mapped_roles = {}
    for col, role in mapping.mappings.items():
        mapped_roles.setdefault(role, []).append(col)
        
    score_col = mapped_roles.get("prediction_score", [None])[0]
    decision_col = mapped_roles.get("decision", [None])[0]
    target_col = mapped_roles.get("target", [None])[0]
    
    empty_result = OverrideAnalysis(
        score_cutoff_used=score_cutoff,
        total_model_declines=0,
        total_model_approves=0,
        positive_override_count=0,
        positive_override_rate=0.0,
        positive_override_bad_rate=0.0,
        positive_override_avg_score=0.0,
        normal_approved_count=0,
        normal_approved_bad_rate=0.0,
        normal_approved_avg_score=0.0,
        negative_override_count=0,
        negative_override_rate=0.0,
        override_performing_better=False,
        insight_narrative="Missing required roles for override analysis.",
        override_by_segment=[]
    )
    
    if not score_col or not decision_col or not target_col:
        return empty_result
        
    clean_df = df[[score_col, decision_col, target_col]].dropna().copy()
    if len(clean_df) == 0:
        empty_result.insight_narrative = "Insufficient data for override analysis."
        return empty_result
        
    positive_label = mapping.mappings.get(decision_col + "_positive_label", "APPROVED")
    if clean_df[decision_col].dtype == object:
        is_approved = clean_df[decision_col].astype(str).str.upper() == positive_label.upper()
    else:
        is_approved = clean_df[decision_col] == 1
        
    clean_df["_is_approved"] = is_approved
    
    is_lower_better = (mapping.score_direction == "lower_is_better")
    
    if is_lower_better:
        model_declines = clean_df[clean_df[score_col] > score_cutoff]
        model_approves = clean_df[clean_df[score_col] <= score_cutoff]
    else:
        model_declines = clean_df[clean_df[score_col] < score_cutoff]
        model_approves = clean_df[clean_df[score_col] >= score_cutoff]
        
    n_model_declines = len(model_declines)
    n_model_approves = len(model_approves)
    
    # Positive Override = model declined, but business approved
    positive_overrides = model_declines[model_declines["_is_approved"]]
    n_positive_overrides = len(positive_overrides)
    positive_override_rate = n_positive_overrides / n_model_declines if n_model_declines > 0 else 0.0
    positive_override_bad_rate = positive_overrides[target_col].mean() if n_positive_overrides > 0 else 0.0
    positive_override_avg_score = positive_overrides[score_col].mean() if n_positive_overrides > 0 else 0.0
    
    # Normal Approved = model approved, and business approved
    normal_approved = model_approves[model_approves["_is_approved"]]
    n_normal_approved = len(normal_approved)
    normal_approved_bad_rate = normal_approved[target_col].mean() if n_normal_approved > 0 else 0.0
    normal_approved_avg_score = normal_approved[score_col].mean() if n_normal_approved > 0 else 0.0
    
    # Negative Override = model approved, but business declined
    negative_overrides = model_approves[~model_approves["_is_approved"]]
    n_negative_overrides = len(negative_overrides)
    negative_override_rate = n_negative_overrides / n_model_approves if n_model_approves > 0 else 0.0
    
    better = False
    narrative = "Not enough data to form insight."
    
    if n_positive_overrides > 0 and n_normal_approved > 0:
        if positive_override_bad_rate < normal_approved_bad_rate:
            better = True
            narrative = f"Overridden accounts in this dataset show LOWER bad rate than model-approved accounts ({positive_override_bad_rate*100:.1f}% vs {normal_approved_bad_rate*100:.1f}%), suggesting underwriters are exercising sound judgment for this risk segment. Review override criteria."
        else:
            narrative = f"Overridden accounts show a HIGHER bad rate than model-approved accounts ({positive_override_bad_rate*100:.1f}% vs {normal_approved_bad_rate*100:.1f}%), indicating possible excessive risk taking on model-declines."
            
    return OverrideAnalysis(
        score_cutoff_used=score_cutoff,
        total_model_declines=n_model_declines,
        total_model_approves=n_model_approves,
        positive_override_count=n_positive_overrides,
        positive_override_rate=float(positive_override_rate),
        positive_override_bad_rate=float(positive_override_bad_rate),
        positive_override_avg_score=float(positive_override_avg_score),
        normal_approved_count=n_normal_approved,
        normal_approved_bad_rate=float(normal_approved_bad_rate),
        normal_approved_avg_score=float(normal_approved_avg_score),
        negative_override_count=n_negative_overrides,
        negative_override_rate=float(negative_override_rate),
        override_performing_better=better,
        insight_narrative=narrative,
        override_by_segment=[]
    )

def run_override_analysis_all(df: pd.DataFrame, mapping: ColumnMapping, cutoffs: list[float] = [550, 600, 650, 700]) -> dict[str, OverrideAnalysis]:
    results = {}
    for c in cutoffs:
        results[str(c)] = run_override_analysis(df, mapping, c)
    return results
