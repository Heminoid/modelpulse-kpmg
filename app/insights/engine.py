import uuid
from datetime import datetime, timezone
from typing import Optional
from app.schemas.insights import Finding, InsightContext
from app.schemas.metrics import MetricResult
from app.schemas.segments import SegmentResult
from app.schemas.alerts import Alert


def generate_deterministic_findings(results: list[MetricResult], alerts: list[Alert], segments: list[SegmentResult]) -> list[Finding]:
    """Generates findings based on deterministic rules."""
    findings = []
    
    # helper to check if metric breached a certain severity
    def has_alert(key: str, severity: str) -> bool:
        return any(a.metric_key == key and a.severity == severity for a in alerts)
        
    def get_metric(key: str) -> Optional[MetricResult]:
        for r in results:
            if r.metric_key == key:
                return r
        return None

    # Expert additions
    # dq_score_pd_coherence
    cohere = get_metric("dq_score_pd_coherence")
    if cohere and cohere.status == "critical":
        findings.append(Finding(
            finding_id=f"fnd_{uuid.uuid4().hex[:12]}",
            category="data_quality",
            severity="critical",
            title="Score-PD Coherence Failed",
            narrative=cohere.metadata.get("finding", "Score and PD disagree or direction is misconfigured."),
            evidence_metrics=["dq_score_pd_coherence"]
        ))
        
    # perf_inverted_ranking
    auc = get_metric("perf_auc")
    if auc and auc.status == "critical":
        findings.append(Finding(
            finding_id=f"fnd_{uuid.uuid4().hex[:12]}",
            category="performance",
            severity="critical",
            title="Inverted Rank Ordering",
            narrative="Score rank-ordering is inverted vs the configured score direction — model may be broken or direction misconfigured; review mapping.",
            evidence_metrics=["perf_auc"]
        ))
        
    # perf_leakage_suspicion
    if auc and auc.status == "warning" and auc.scalar_value and auc.scalar_value > 0.97:
        findings.append(Finding(
            finding_id=f"fnd_{uuid.uuid4().hex[:12]}",
            category="performance",
            severity="warning",
            title="Suspiciously High AUC",
            narrative="suspiciously perfect discrimination — check target leakage / post-outcome features",
            evidence_metrics=["perf_auc"]
        ))
        
    # dq_band_consistency
    band = get_metric("dq_band_consistency")
    if band and band.status == "warning":
        findings.append(Finding(
            finding_id=f"fnd_{uuid.uuid4().hex[:12]}",
            category="data_quality",
            severity="warning",
            title="Score Band Inconsistency",
            narrative="Score band column does not consistently match bands derived from the score.",
            evidence_metrics=["dq_band_consistency"]
        ))
        
    # Drift
    if has_alert("psi_model_score", "critical"):
        findings.append(Finding(
            finding_id=f"fnd_{uuid.uuid4().hex[:12]}",
            category="drift", severity="critical",
            title="Major Score Drift",
            narrative="Score distribution shows critical population drift. Model may be scoring a different population than training.",
            evidence_metrics=["psi_model_score"]
        ))
    elif has_alert("psi_model_score", "warning"):
        findings.append(Finding(
            finding_id=f"fnd_{uuid.uuid4().hex[:12]}",
            category="drift", severity="warning",
            title="Score Drift Detected",
            narrative="Score distribution shows warning population drift.",
            evidence_metrics=["psi_model_score"]
        ))
        
    # Calibration
    calib = get_metric("calib_summary")
    if has_alert("calib_ratio_overall", "critical") or (calib and calib.status == "critical"):
        findings.append(Finding(
            finding_id=f"fnd_{uuid.uuid4().hex[:12]}",
            category="calibration", severity="critical",
            title="Calibration Critical",
            narrative="Overall calibration ratio is critically out of bounds.",
            evidence_metrics=["calib_summary"]
        ))
        
    # Strategy
    app_ar = has_alert("strategy_approval_rate", "critical")
    app_br = has_alert("strategy_bad_rate_approved", "critical")
    if app_ar and app_br:
        findings.append(Finding(
            finding_id=f"fnd_{uuid.uuid4().hex[:12]}",
            category="strategy", severity="critical",
            title="Strategy Deterioration",
            narrative="Strategy deterioration: approval fell while portfolio quality worsened.",
            evidence_metrics=["strategy_approval_rate", "strategy_bad_rate_approved"]
        ))
        
    # Delinquency
    if has_alert("delinq_severe_rate", "critical"):
        findings.append(Finding(
            finding_id=f"fnd_{uuid.uuid4().hex[:12]}",
            category="delinquency", severity="critical",
            title="High Severe Delinquency",
            narrative="Severe delinquency rate (>90 DPD) has breached the critical threshold.",
            evidence_metrics=["delinq_severe_rate"]
        ))
        
    # Data Quality
    t_count = get_metric("data_quality_invalid_target")
    if t_count and t_count.scalar_value and t_count.scalar_value < 30 and t_count.status != "error":
        # Wait, the rule says target_low_bad_count. Need a metric that returns the total defaults.
        # strategy_bad_rate has the rate. data_quality_invalid_target is different.
        # We can just count total defaults from dataset rows * bad_rate.
        pass # implemented in data profile instead

    return findings


def build_insight_context(run_id, monitor_name, template_type, dataset_rows, has_baseline, results, segments, alerts, findings) -> InsightContext:
    
    br_metric = next((m for m in results if m.metric_key == "strategy_bad_rate"), None)
    ar_metric = next((m for m in results if m.metric_key == "strategy_approval_rate"), None)
    
    return InsightContext(
        run_id=run_id,
        monitor_name=monitor_name,
        template_type=template_type,
        run_date=datetime.now(timezone.utc).isoformat(),
        dataset_rows=dataset_rows,
        has_baseline=has_baseline,
        target_base_rate=br_metric.scalar_value if br_metric else 0.0,
        approval_rate=ar_metric.scalar_value if ar_metric else None,
        metric_status_table=[{"metric_key": r.metric_key, "value": r.scalar_value, "status": r.status} for r in results if r.scalar_value is not None],
        threshold_breaches=[{"metric_key": a.metric_key, "value": a.observed_value, "severity": a.severity} for a in alerts],
        deterministic_findings=findings,
        finding_count_by_severity={
            "critical": len([f for f in findings if f.severity == "critical"]),
            "warning": len([f for f in findings if f.severity == "warning"]),
            "info": len([f for f in findings if f.severity == "info"])
        }
    )
