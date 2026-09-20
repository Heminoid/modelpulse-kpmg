import pandas as pd
from app.schemas.mapping import ColumnMapping

class TimeSeriesService:
    def analyze(self, df: pd.DataFrame, mapping: ColumnMapping) -> dict:
        mapped_roles = {}
        for col, role in mapping.mappings.items():
            mapped_roles.setdefault(role, []).append(col)
            
        time_col = mapped_roles.get("event_time", [None])[0]
        
        if not time_col or time_col not in df.columns:
            return {"available": False, "reason": "No event_time column mapped"}
            
        series = df[time_col]
        if series.nunique() <= 1:
            return {"available": False, "reason": "event_time column contains single unique value or is entirely malformed — time-series analysis requires time variation"}
            
        try:
            parsed = pd.to_datetime(series, errors="coerce")
            if parsed.notna().mean() < 0.8:
                return {"available": False, "reason": "event_time column could not be parsed as datetimes (majority invalid)"}
        except Exception:
            return {"available": False, "reason": "event_time column could not be parsed"}
            
        temp_df = df.copy()
        temp_df["_period"] = parsed.dt.to_period("M").astype(str)
        
        target_col = mapped_roles.get("target", [None])[0]
        score_col = mapped_roles.get("prediction_score", [None])[0]
        decision_col = mapped_roles.get("decision", [None])[0]
        
        periods_data = []
        for period, grp in temp_df.groupby("_period"):
            if period in ("NaT", "nan"):
                continue
            item = {
                "period": str(period),
                "volume": int(len(grp)),
            }
            if target_col and target_col in grp.columns and pd.api.types.is_numeric_dtype(grp[target_col]):
                item["default_rate"] = round(float(grp[target_col].dropna().mean()), 4)
            if score_col and score_col in grp.columns and pd.api.types.is_numeric_dtype(grp[score_col]):
                item["mean_score"] = round(float(grp[score_col].dropna().mean()), 2)
            if decision_col and decision_col in grp.columns:
                dec_vals = grp[decision_col].dropna()
                if pd.api.types.is_numeric_dtype(dec_vals):
                    item["approval_rate"] = round(float(dec_vals.mean()), 4)
                else:
                    # check for string labels like APPROVE / 1
                    approves = dec_vals.astype(str).str.upper().isin(["1", "TRUE", "APPROVE", "APPROVED"]).mean()
                    item["approval_rate"] = round(float(approves), 4)
            periods_data.append(item)
            
        periods_data.sort(key=lambda x: x["period"])
        
        return {
            "available": True,
            "time_column": time_col,
            "periods": periods_data,
            "total_periods": len(periods_data),
            "trend_summary": f"Analyzed {len(periods_data)} cohorts from {periods_data[0]['period'] if periods_data else 'N/A'} to {periods_data[-1]['period'] if periods_data else 'N/A'}"
        }
