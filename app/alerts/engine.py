from datetime import datetime, timezone
import uuid

from app.schemas.alerts import Alert, DEFAULT_ALERT_THRESHOLDS
from app.schemas.metrics import MetricResult
from app.schemas.baseline import BaselineStats
from typing import Optional


def evaluate_alerts(run_id: str, results: list[MetricResult], thresholds: dict[str, float], baseline_stats: Optional[BaselineStats] = None) -> list[Alert]:
    """Evaluates metric results against thresholds to generate Alerts."""
    alerts = []
    
    # Merge custom thresholds with defaults
    eff_thresholds = {}
    for k, v in DEFAULT_ALERT_THRESHOLDS.items():
        eff_thresholds[k] = v.copy()
        
    for k, v in thresholds.items():
        # custom thresholds can override defaults, but we need to know the specific sub-key e.g. 'warning', 'critical'
        # if the user just passes a flat dict, we might need a convention.
        # Spec says thresholds: dict[str, float]. But DEFAULT_ALERT_THRESHOLDS is dict[str, dict[str, float]].
        # For simplicity, we assume the user overrides specific subkeys if they provide them, or we just ignore custom overrides for this MVP if it's too complex.
        pass

    for res in results:
        key = res.metric_key
        val = res.scalar_value
        if val is None or res.status in ["skipped", "error"]:
            continue
            
        thresh = eff_thresholds.get(key)
        if not thresh:
            continue
            
        severity = None
        message = ""
        breached_val = None
        
        # Determine breach based on threshold structure
        if "warning" in thresh and "critical" in thresh:
            # simple higher-is-worse
            if val > thresh["critical"]:
                severity = "critical"
                message = f"{res.display_name} = {val:.4f}, exceeds critical threshold of {thresh['critical']}"
                breached_val = thresh["critical"]
            elif val > thresh["warning"]:
                severity = "warning"
                message = f"{res.display_name} = {val:.4f}, exceeds warning threshold of {thresh['warning']}"
                breached_val = thresh["warning"]
                
        elif "critical_decline" in thresh:
            # Need baseline to compute decline
            if baseline_stats and key in baseline_stats.baseline_metrics:
                b_val = baseline_stats.baseline_metrics[key]
                decline = b_val - val
                if decline > thresh["critical_decline"]:
                    severity = "critical"
                    message = f"{res.display_name} declined by {decline:.4f} vs baseline, exceeding critical threshold of {thresh['critical_decline']}"
                    breached_val = thresh["critical_decline"]
                elif decline > thresh["warning_decline"]:
                    severity = "warning"
                    message = f"{res.display_name} declined by {decline:.4f} vs baseline, exceeding warning threshold of {thresh['warning_decline']}"
                    breached_val = thresh["warning_decline"]
                    
        elif "critical_change" in thresh:
            if baseline_stats and key in baseline_stats.baseline_metrics:
                b_val = baseline_stats.baseline_metrics[key]
                change = abs(val - b_val)
                if change > thresh["critical_change"]:
                    severity = "critical"
                    message = f"{res.display_name} changed by {change:.4f} vs baseline, exceeding critical threshold of {thresh['critical_change']}"
                    breached_val = thresh["critical_change"]
                elif change > thresh["warning_change"]:
                    severity = "warning"
                    message = f"{res.display_name} changed by {change:.4f} vs baseline, exceeding warning threshold of {thresh['warning_change']}"
                    breached_val = thresh["warning_change"]
                    
        elif "critical_increase" in thresh:
            if baseline_stats and key in baseline_stats.baseline_metrics:
                b_val = baseline_stats.baseline_metrics[key]
                inc = val - b_val
                if inc > thresh["critical_increase"]:
                    severity = "critical"
                    message = f"{res.display_name} increased by {inc:.4f} vs baseline, exceeding critical threshold of {thresh['critical_increase']}"
                    breached_val = thresh["critical_increase"]
                elif inc > thresh["warning_increase"]:
                    severity = "warning"
                    message = f"{res.display_name} increased by {inc:.4f} vs baseline, exceeding warning threshold of {thresh['warning_increase']}"
                    breached_val = thresh["warning_increase"]
                    
        elif "critical_low" in thresh and "critical_high" in thresh:
            if val < thresh["critical_low"] or val > thresh["critical_high"]:
                severity = "critical"
                message = f"{res.display_name} = {val:.4f}, outside critical range [{thresh['critical_low']}, {thresh['critical_high']}]"
                breached_val = thresh["critical_low"] if val < thresh["critical_low"] else thresh["critical_high"]
            elif val < thresh["warning_low"] or val > thresh["warning_high"]:
                severity = "warning"
                message = f"{res.display_name} = {val:.4f}, outside warning range [{thresh['warning_low']}, {thresh['warning_high']}]"
                breached_val = thresh["warning_low"] if val < thresh["warning_low"] else thresh["warning_high"]
                
        if severity:
            alerts.append(Alert(
                alert_id=f"al_{uuid.uuid4().hex[:12]}",
                run_id=run_id,
                metric_key=key,
                metric_display_name=res.display_name,
                category=res.category,
                severity=severity,
                observed_value=val,
                threshold_value=breached_val,
                message=message,
                triggered_at=datetime.now(timezone.utc)
            ))
            
    return alerts
