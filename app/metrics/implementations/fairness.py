"""Fairness Analysis."""

import pandas as pd
from app.schemas.fairness import FairnessAnalysis

def compute_disparate_impact(
    df: pd.DataFrame,
    decision_col: str,
    group_col: str,
    positive_decision: str = "APPROVED",
    reference_mode: str = "overall",
) -> list[dict]:
    # Amendment C7: guard overall_ar == 0; skip groups with n == 0.
    if df[decision_col].dtype == object:
        is_approved = df[decision_col].astype(str).str.upper() == positive_decision.upper()
    else:
        is_approved = df[decision_col] == 1
        
    overall_ar = is_approved.mean()
    if overall_ar == 0:
        return []
        
    results = []
    for val in df[group_col].dropna().unique():
        sub_mask = df[group_col] == val
        n = sub_mask.sum()
        if n == 0:
            continue
            
        ar = is_approved[sub_mask].mean()
        di = ar / overall_ar
        
        results.append({
            "group_col": group_col,
            "group_value": str(val),
            "n": int(n),
            "approval_rate": round(ar, 4),
            "reference_rate": round(overall_ar, 4),
            "di_ratio": round(di, 4),
            "status": "critical" if di < 0.80 else ("warning" if di < 0.90 else "ok"),
            "fourfifths_rule_breach": di < 0.80,
            "low_power_warning": n < 30,
            "is_proxy": True,
            "proxy_note": f"{group_col} used as proxy variable. Not a legally protected class.",
        })
    return sorted(results, key=lambda x: x["di_ratio"])

def run_fairness_analysis(df: pd.DataFrame, mapping, group_cols: list[str]) -> FairnessAnalysis:
    mapped_roles = {}
    for col, role in mapping.mappings.items():
        mapped_roles.setdefault(role, []).append(col)
        
    decision_col = mapped_roles.get("decision", [None])[0]
    if not decision_col or decision_col not in df.columns:
        return FairnessAnalysis(
            proxy_groups_analyzed=[],
            overall_approval_rate=0.0,
            di_results=[],
            adverse_impact_flags=[],
            borderline_flags=[],
            regulatory_note="Missing decision column for fairness analysis.",
            recommended_actions=[],
            ecoa_compliance_summary="Unable to compute."
        )
        
    positive_label = mapping.mappings.get(decision_col + "_positive_label", "APPROVED")
    if df[decision_col].dtype == object:
        is_approved = df[decision_col].astype(str).str.upper() == positive_label.upper()
    else:
        is_approved = df[decision_col] == 1
        
    overall_ar = float(is_approved.mean())
    
    di_results = []
    analyzed_cols = []
    
    for g_col in group_cols:
        if g_col in df.columns:
            analyzed_cols.append(g_col)
            res = compute_disparate_impact(df, decision_col, g_col, positive_label)
            di_results.extend(res)
            
    di_results = sorted(di_results, key=lambda x: x["di_ratio"])
    
    adverse = [r for r in di_results if r["fourfifths_rule_breach"]]
    borderline = [r for r in di_results if r["status"] == "warning"]
    
    actions = []
    if adverse:
        actions.append("Investigate adverse impact on critical groups using less discriminatory alternatives.")
    if borderline:
        actions.append("Monitor borderline groups for emerging adverse impact trends.")
        
    if not adverse and not borderline:
        summary = "No direct adverse impact detected."
    elif not adverse:
        # Get lowest borderline
        lowest = borderline[0]
        summary = f"No direct adverse impact detected. Borderline: {lowest['group_value']} (DI={lowest['di_ratio']})"
    else:
        lowest = adverse[0]
        summary = f"Adverse impact detected on {len(adverse)} proxy groups. Critical: {lowest['group_value']} (DI={lowest['di_ratio']})"
        
    return FairnessAnalysis(
        proxy_groups_analyzed=analyzed_cols,
        overall_approval_rate=overall_ar,
        di_results=di_results,
        adverse_impact_flags=adverse,
        borderline_flags=borderline,
        regulatory_note="Proxy analysis only. ECOA/FHA require actual protected class data.",
        recommended_actions=actions,
        ecoa_compliance_summary=summary
    )
