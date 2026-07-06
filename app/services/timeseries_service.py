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
        except:
            return {"available": False, "reason": "event_time column could not be parsed"}
            
        return {
            "available": True,
            "data": "Placeholder for real time-series data when dataset supports it."
        }
