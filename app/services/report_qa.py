"""Report QA Checklist — validates report completeness against regulatory standards."""

REPORT_REQUIREMENTS = {
    "sr_11_7": {
        "name": "SR 11-7 Model Validation",
        "required_sections": [
            {"id": "performance", "name": "Performance Analysis", "checks": ["perf_auc", "perf_gini"]},
            {"id": "calibration", "name": "Calibration Assessment", "checks": ["calib_summary"]},
            {"id": "stability", "name": "Stability / Drift", "checks": ["psi_prediction_score"]},
            {"id": "data_quality", "name": "Data Quality", "checks": ["data_quality_null_rates", "data_quality_row_count"]},
            {"id": "fairness", "name": "Discrimination Testing", "checks": []},
        ],
        "required_artifacts": ["metrics.json", "alerts.json", "health.json", "stat_tests.json"],
        "narrative_required": True,
    },
    "executive_summary": {
        "name": "Executive Summary",
        "required_sections": [
            {"id": "health", "name": "Health Score", "checks": []},
            {"id": "alerts", "name": "Alert Summary", "checks": []},
            {"id": "narrative", "name": "AI Narrative", "checks": []},
        ],
        "required_artifacts": ["health.json", "alerts.json"],
        "narrative_required": True,
    },
    "full_technical": {
        "name": "Full Technical Report",
        "required_sections": [
            {"id": "performance", "name": "Performance Analysis", "checks": ["perf_auc", "perf_gini", "perf_ks"]},
            {"id": "calibration", "name": "Calibration", "checks": ["calib_summary"]},
            {"id": "stability", "name": "Stability", "checks": ["psi_prediction_score"]},
            {"id": "strategy", "name": "Strategy Metrics", "checks": ["strategy_approval_rate", "strategy_bad_rate"]},
            {"id": "fairness", "name": "Fairness", "checks": []},
            {"id": "vintage", "name": "Vintage Analysis", "checks": []},
            {"id": "stat_tests", "name": "Statistical Tests", "checks": []},
        ],
        "required_artifacts": ["metrics.json", "alerts.json", "health.json", "stat_tests.json", "fairness.json", "vintage.json"],
        "narrative_required": True,
    },
    "data_quality": {
        "name": "Data Quality Report",
        "required_sections": [
            {"id": "completeness", "name": "Data Completeness", "checks": ["data_quality_null_rates", "data_quality_row_count"]},
            {"id": "drift", "name": "Data Drift", "checks": ["psi_prediction_score"]},
        ],
        "required_artifacts": ["metrics.json"],
        "narrative_required": False,
    },
    "ifrs9": {
        "name": "IFRS 9 Monitoring",
        "required_sections": [
            {"id": "delinquency", "name": "Delinquency Analysis", "checks": ["delinq_severe_rate", "delinq_30plus_rate"]},
            {"id": "calibration", "name": "PD Calibration", "checks": ["calib_summary"]},
            {"id": "vintage", "name": "Vintage/Roll Rate", "checks": []},
        ],
        "required_artifacts": ["metrics.json", "vintage.json"],
        "narrative_required": False,
    },
}

METRIC_ALIASES = {
    "calib_summary": ["calib_summary", "calib_ratio_overall"],
    "calib_ratio_overall": ["calib_summary", "calib_ratio_overall"],
    "data_quality_null_rates": ["data_quality_null_rates", "dq_missing_rate", "data_quality_null_rate"],
    "dq_missing_rate": ["data_quality_null_rates", "dq_missing_rate", "data_quality_null_rate"],
    "data_quality_row_count": ["data_quality_row_count", "dq_row_count"],
    "dq_row_count": ["data_quality_row_count", "dq_row_count"],
    "strategy_approval_rate": ["strategy_approval_rate", "approval_rate"],
    "approval_rate": ["strategy_approval_rate", "approval_rate"],
    "strategy_bad_rate": ["strategy_bad_rate", "bad_rate"],
    "bad_rate": ["strategy_bad_rate", "bad_rate"],
}


def run_qa_check(report_type: str, run_store, run_id: str) -> dict:
    """Run QA checklist for a given report type and run."""
    requirements = REPORT_REQUIREMENTS.get(report_type)
    if not requirements:
        return {"complete": True, "score": 100.0, "missing": [], "warnings": [], "checks": []}
    
    checks = []
    missing = []
    warnings = []
    
    # Check required artifacts exist
    for artifact_name in requirements["required_artifacts"]:
        data = run_store.load_artifact(run_id, artifact_name)
        exists = data is not None and (data != [] and data != {})
        checks.append({
            "check": f"Artifact: {artifact_name}",
            "status": "pass" if exists else "fail",
            "category": "artifact"
        })
        if not exists:
            missing.append(f"Missing or empty artifact: {artifact_name}")
    
    # Check narrative exists if required
    if requirements["narrative_required"]:
        narrative = run_store.load_artifact(run_id, "narratives.json")
        has_narrative = narrative is not None and narrative.get("executive_summary")
        checks.append({
            "check": "AI Narrative generated",
            "status": "pass" if has_narrative else "fail",
            "category": "narrative"
        })
        if not has_narrative:
            warnings.append("AI narrative not generated — report will have empty narrative sections")
    
    # Check required metrics exist
    metrics = run_store.load_artifact(run_id, "metrics.json") or []
    metric_keys = {m.get("metric_key") for m in metrics}
    
    for section in requirements["required_sections"]:
        section_has_data = True
        for metric_key in section["checks"]:
            accepted = METRIC_ALIASES.get(metric_key, [metric_key])
            if not any(k in metric_keys for k in accepted):
                section_has_data = False
                missing.append(f"Section '{section['name']}': missing metric '{metric_key}'")
        
        checks.append({
            "check": f"Section: {section['name']}",
            "status": "pass" if section_has_data else ("warning" if len(section['checks']) == 0 else "fail"),
            "category": "section"
        })
    
    # Calculate score
    total_checks = len(checks)
    passed = sum(1 for c in checks if c["status"] == "pass")
    score = round((passed / total_checks) * 100, 1) if total_checks > 0 else 100.0
    
    return {
        "complete": len(missing) == 0,
        "score": score,
        "report_type": report_type,
        "report_name": requirements["name"],
        "total_checks": total_checks,
        "passed_checks": passed,
        "missing": missing,
        "warnings": warnings,
        "checks": checks
    }
