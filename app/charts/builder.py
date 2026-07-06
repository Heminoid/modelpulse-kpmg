"""Chart payload builders."""

import pandas as pd
from typing import Optional
from app.schemas.charts import ChartPayload, ChartSeries
from app.schemas.metrics import MetricResult
from app.schemas.baseline import BaselineStats
from app.schemas.mapping import ColumnMapping

def build_charts(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    metrics: list[MetricResult],
    baseline_stats: Optional[BaselineStats] = None
) -> list[ChartPayload]:
    """Build all applicable chart payloads based on available roles."""
    charts = []
    
    # Reverse the mapping for easy role lookups
    mapped_roles = {}
    for col, role in mapping.mappings.items():
        mapped_roles.setdefault(role, []).append(col)
        
    def get_col(role: str) -> Optional[str]:
        cols = mapped_roles.get(role)
        return cols[0] if cols else None

    target_col = get_col("target")
    score_col = get_col("prediction_score")
    pd_col = get_col("prediction_probability")
    decision_col = get_col("decision")
    band_col = get_col("score_band")
    risk_col = get_col("risk_rating")
    dpd_col = get_col("dpd_field") or get_col("past_due_days")
    segments = mapped_roles.get("selected_segments", [])
    
    # 1. chart_score_distribution (histogram)
    if score_col and score_col in df.columns:
        counts, edges = pd.cut(df[score_col], bins=10, retbins=True, right=False)
        freqs = counts.value_counts(sort=False)
        data = [{"x": f"{edges[i]:.0f}-{edges[i+1]:.0f}", "y": int(val)} for i, val in enumerate(freqs)]
        charts.append(ChartPayload(
            chart_id="chart_score_distribution",
            chart_type="bar",
            title="Score Distribution",
            x_label="Score Band",
            y_label="Count",
            series=[ChartSeries(name="Current", data=data, color="#3b82f6")]
        ))
        
    # 2. chart_pd_distribution (histogram)
    if pd_col and pd_col in df.columns:
        counts, edges = pd.cut(df[pd_col], bins=10, retbins=True, right=False)
        freqs = counts.value_counts(sort=False)
        data = [{"x": f"{edges[i]:.2f}-{edges[i+1]:.2f}", "y": int(val)} for i, val in enumerate(freqs)]
        charts.append(ChartPayload(
            chart_id="chart_pd_distribution",
            chart_type="bar",
            title="Probability of Default Distribution",
            x_label="PD Band",
            y_label="Count",
            series=[ChartSeries(name="Current", data=data, color="#8b5cf6")]
        ))
        
    # 3. chart_bad_rate_by_score_band
    # requires prediction_score or score_band, and target
    if target_col and target_col in df.columns:
        group_col = band_col if band_col else (score_col if score_col else None)
        if group_col and group_col in df.columns:
            if group_col == score_col:
                # Bin it
                df_temp = df.copy()
                df_temp["_bin"] = pd.qcut(df_temp[score_col].rank(method="first"), 5, labels=False)
                grouped = df_temp.groupby("_bin")[target_col].mean()
                data = [{"x": f"Bin {i}", "y": float(val)} for i, val in grouped.items()]
            else:
                grouped = df.groupby(group_col)[target_col].mean()
                data = [{"x": str(k), "y": float(val)} for k, val in grouped.items()]
                
            charts.append(ChartPayload(
                chart_id="chart_bad_rate_by_score_band",
                chart_type="bar",
                title="Bad Rate by Score Band",
                x_label="Band",
                y_label="Bad Rate",
                series=[ChartSeries(name="Bad Rate", data=data, color="#ef4444")]
            ))
            
    # 4. chart_approval_by_risk_band
    if risk_col or band_col or score_col:
        if decision_col and decision_col in df.columns:
            group_col = risk_col or band_col or score_col
            if group_col and group_col in df.columns:
                # We need to calculate approval rate = (decision == positive_label).mean()
                positive_label = mapping.mappings.get(decision_col + "_positive_label", "APPROVED") # Approximate, we don't have this in ColumnMapping easily here, assume "APPROVED" or 1
                
                # Check how many are "APPROVED" vs 1
                approvals = df[decision_col].astype(str).str.upper() == "APPROVED"
                if not approvals.any():
                    approvals = df[decision_col] == 1
                    
                df_temp = df.copy()
                df_temp["_approved"] = approvals.astype(int)
                
                if group_col == score_col:
                    df_temp["_bin"] = pd.qcut(df_temp[score_col].rank(method="first"), 5, labels=False)
                    grouped = df_temp.groupby("_bin")["_approved"].mean()
                    data = [{"x": f"Bin {i}", "y": float(val)} for i, val in grouped.items()]
                else:
                    grouped = df_temp.groupby(group_col)["_approved"].mean()
                    data = [{"x": str(k), "y": float(val)} for k, val in grouped.items()]
                    
                charts.append(ChartPayload(
                    chart_id="chart_approval_by_risk_band",
                    chart_type="bar",
                    title="Approval Rate by Risk Band",
                    x_label="Band",
                    y_label="Approval Rate",
                    series=[ChartSeries(name="Approval Rate", data=data, color="#10b981")]
                ))
                
    # 5. chart_calibration
    if pd_col and target_col and pd_col in df.columns and target_col in df.columns:
        df_temp = df.copy()
        df_temp["_bin"] = pd.qcut(df_temp[pd_col].rank(method="first"), 10, labels=False)
        grouped = df_temp.groupby("_bin").agg({pd_col: "mean", target_col: "mean"})
        
        predicted_data = [{"x": f"Bin {i+1}", "y": float(row[pd_col])} for i, row in grouped.iterrows()]
        observed_data = [{"x": f"Bin {i+1}", "y": float(row[target_col])} for i, row in grouped.iterrows()]
        
        charts.append(ChartPayload(
            chart_id="chart_calibration",
            chart_type="line",
            title="Calibration Curve",
            x_label="Decile",
            y_label="Probability",
            series=[
                ChartSeries(name="Predicted PD", data=predicted_data, color="#3b82f6"),
                ChartSeries(name="Observed Bad Rate", data=observed_data, color="#ef4444")
            ]
        ))
        
    # 6. chart_dpd_distribution
    if dpd_col and dpd_col in df.columns:
        def get_bucket(val):
            if pd.isna(val) or val <= 0: return "Current"
            if val <= 29: return "1-29"
            if val <= 59: return "30-59"
            if val <= 89: return "60-89"
            return "90+"
        buckets = df[dpd_col].apply(get_bucket).value_counts()
        ordered_buckets = ["Current", "1-29", "30-59", "60-89", "90+"]
        data = [{"x": b, "y": int(buckets.get(b, 0))} for b in ordered_buckets]
        
        charts.append(ChartPayload(
            chart_id="chart_dpd_distribution",
            chart_type="bar",
            title="DPD Distribution",
            x_label="Days Past Due",
            y_label="Count",
            series=[ChartSeries(name="Current", data=data, color="#f59e0b")]
        ))
        
    # 7. chart_psi_breakdown
    if baseline_stats:
        # Get PSI metrics from results
        psi_metrics = [m for m in metrics if m.metric_key.startswith("psi_") and m.scalar_value is not None]
        if psi_metrics:
            data = [{"x": m.display_name.replace("PSI ", ""), "y": m.scalar_value} for m in psi_metrics]
            charts.append(ChartPayload(
                chart_id="chart_psi_breakdown",
                chart_type="bar",
                title="PSI Breakdown",
                x_label="Feature",
                y_label="PSI",
                series=[ChartSeries(name="PSI", data=data, color="#f43f5e")],
                annotations=[{"y": 0.25, "color": "red", "label": "Critical"}, {"y": 0.10, "color": "orange", "label": "Warning"}]
            ))
            
    # 8. chart_segment_bad_rate
    # Skip for now if too complex or just use the first segment
    if target_col and target_col in df.columns and segments:
        seg_col = segments[0]
        if seg_col in df.columns:
            grouped = df.groupby(seg_col)[target_col].mean()
            data = [{"x": str(k), "y": float(val)} for k, val in grouped.items()]
            charts.append(ChartPayload(
                chart_id="chart_segment_bad_rate",
                chart_type="bar",
                title=f"Bad Rate by {seg_col}",
                x_label=seg_col,
                y_label="Bad Rate",
                series=[ChartSeries(name="Bad Rate", data=data, color="#14b8a6")]
            ))
            
    # 9. chart_decile_lift
    if score_col and target_col and score_col in df.columns and target_col in df.columns:
        overall_bad_rate = df[target_col].mean()
        if overall_bad_rate > 0:
            df_temp = df.copy()
            ascending = True if mapping.score_direction == "lower_is_better" else False
            df_temp["_decile"] = pd.qcut(df_temp[score_col].rank(method="first", ascending=ascending), 10, labels=False) + 1
            grouped = df_temp.groupby("_decile")[target_col].mean()
            data = [{"x": f"Decile {int(k)}", "y": float(val / overall_bad_rate)} for k, val in grouped.items()]
            charts.append(ChartPayload(
                chart_id="chart_decile_lift",
                chart_type="bar",
                title="Decile Lift",
                x_label="Decile",
                y_label="Lift",
                series=[ChartSeries(name="Lift", data=data, color="#6366f1")],
                annotations=[{"y": 1.0, "color": "gray", "label": "Baseline"}]
            ))
            
    # 10. chart_roc_curve
    if score_col and target_col and score_col in df.columns and target_col in df.columns:
        from sklearn.metrics import roc_curve
        # If higher_is_better, invert score for standard sklearn ROC
        clean_df = df[[target_col, score_col]].dropna()
        if len(clean_df) > 0:
            y_score = clean_df[score_col]
            if mapping.score_direction == "higher_is_better":
                y_score = -y_score
            fpr, tpr, _ = roc_curve(clean_df[target_col], y_score)
            step = max(1, len(fpr) // 20)
            data = [{"x": float(f), "y": float(t)} for f, t in zip(fpr[::step], tpr[::step])]
            if len(fpr) > 0 and (data[-1]["x"] != fpr[-1] or data[-1]["y"] != tpr[-1]):
                data.append({"x": float(fpr[-1]), "y": float(tpr[-1])})
            
            charts.append(ChartPayload(
                chart_id="chart_roc_curve",
                chart_type="line",
                title="ROC Curve",
                x_label="False Positive Rate",
                y_label="True Positive Rate",
                series=[ChartSeries(name="ROC", data=data, color="#8b5cf6")],
                annotations=[{"x": 0, "y": 0, "label": "Diagonal", "color": "gray", "linestyle": "dotted"}] # Just a hint
            ))

    return charts
