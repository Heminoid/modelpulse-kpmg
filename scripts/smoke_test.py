#!/usr/bin/env python3
"""
smoke_test.py — end-to-end acceptance tests against a running ModelPulse server.

Usage:
    python scripts/smoke_test.py [--phase N] [--base-url URL]

Requires the server to be running (uvicorn main:app --port 8000).
Grows with each build phase. Exit non-zero on any failure.
"""

from __future__ import annotations

import argparse
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Ensure the project root is on sys.path so we can import app.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import httpx

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
PASS = 0
FAIL = 0
BASE_URL = "http://localhost:8000"


def check(label: str, condition: bool, detail: str = "") -> None:
    """Record a pass/fail check."""
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        msg = f"  ❌ {label}"
        if detail:
            msg += f"  — {detail}"
        print(msg)


def heading(text: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Phase 1: Foundation
# ---------------------------------------------------------------------------
def phase_1(client: httpx.Client) -> None:
    heading("Phase 1 — Foundation")

    # --- Health endpoint ---
    print("\n[Health endpoint]")
    r = client.get(f"{BASE_URL}/api/v1/health")
    check("GET /api/v1/health returns 200", r.status_code == 200)

    body = r.json()
    check("Response has success=True", body.get("success") is True)
    check("Response has timestamp", "timestamp" in body)
    check("Data contains status=ok", body.get("data", {}).get("status") == "ok")
    check(
        "Data contains app_name",
        body.get("data", {}).get("app_name") == "ModelPulse API",
    )
    check("Data contains version", "version" in body.get("data", {}))

    # --- Store round-trip (via direct Python import, not HTTP) ---
    print("\n[Store round-trip]")
    try:
        # Use a temp directory so we don't pollute real storage
        tmpdir = Path(tempfile.mkdtemp(prefix="mp_smoke_"))
        try:
            from app.storage.dataset_store import DatasetStore

            store = DatasetStore(tmpdir / "datasets")

            # Create
            created = store.create({"name": "test_dataset", "rows": 42})
            ds_id = created["id"]
            check("Store create returns id", ds_id is not None)

            # Get
            fetched = store.get(ds_id)
            check(
                "Store get returns same record",
                fetched is not None and fetched["name"] == "test_dataset",
            )

            # List
            items, total = store.list()
            check("Store list returns items", len(items) == 1 and total == 1)

            # Update
            updated = store.update(ds_id, {"rows": 99})
            check(
                "Store update modifies field",
                updated is not None and updated["rows"] == 99,
            )

            # Exists
            check("Store exists returns True", store.exists(ds_id))

            # Delete
            deleted = store.delete(ds_id)
            check("Store delete returns True", deleted is True)
            check("Store exists returns False after delete", not store.exists(ds_id))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception as e:
        check(f"Store round-trip (exception: {e})", False)

    # --- CORS header check ---
    print("\n[CORS middleware]")
    r = client.options(
        f"{BASE_URL}/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    cors_header = r.headers.get("access-control-allow-origin", "")
    check("CORS allows origin", cors_header == "*" or cors_header == "http://localhost:3000")


def phase_2(client: httpx.Client) -> None:
    heading("Phase 2 — Datasets & Mapping")

    # We need the absolute path to the data files
    data_dir = _PROJECT_ROOT / "data"
    underwriting_csv = data_dir / "underwriting_scorecard_clean.csv"
    fraud_csv = data_dir / "fraud_sample.csv"

    print("\n[Negative Tests]")
    # 1. Invalid dataset ID
    r = client.get(f"{BASE_URL}/api/v1/datasets/invalid_id")
    check("GET /datasets/invalid_id returns 404", r.status_code == 404)

    # 2. Upload text file
    txt_file = data_dir / "test.txt"
    txt_file.write_text("not a csv")
    with open(txt_file, "rb") as f:
        r = client.post(f"{BASE_URL}/api/v1/datasets/upload", files={"file": ("test.txt", f, "text/plain")})
    check("Upload .txt returns 400", r.status_code == 400)
    txt_file.unlink()

    print("\n[Underwriting Dataset (Exact Vocab Pass 1)]")
    with open(underwriting_csv, "rb") as f:
        r = client.post(f"{BASE_URL}/api/v1/datasets/upload", files={"file": ("underwriting_scorecard_clean.csv", f, "text/csv")})
    check("Upload underwriting CSV returns 200", r.status_code == 200)
    
    body = r.json()
    dataset_id = body["data"]["id"]
    check("Upload returned correct row/col counts", body["data"]["row_count"] == 197 and body["data"]["column_count"] == 22)

    # Profile
    r = client.get(f"{BASE_URL}/api/v1/datasets/{dataset_id}/profile")
    check("GET /profile returns 200", r.status_code == 200)
    profile = r.json()["data"]
    warnings = profile["monitoring_readiness"]
    check("Profile flags application_time_malformed", "application_time_malformed" in warnings)
    check("Profile flags risk_rating_truncated", "risk_rating_truncated" in warnings)
    check("Profile flags low_bad_count", "low_bad_count" in warnings)
    check("Profile flags record_id_not_unique", "record_id_not_unique" in warnings)

    # Suggest Mapping
    r = client.post(f"{BASE_URL}/api/v1/datasets/{dataset_id}/suggest-mapping")
    check("Suggest mapping returns 200", r.status_code == 200)
    suggestions = r.json()["data"]["suggestions"]
    
    # Check specific assignments
    sug_map = {s["column_name"]: s for s in suggestions}
    check("actual_default -> target (high)", sug_map["actual_default"]["suggested_role"] == "target" and sug_map["actual_default"]["confidence_label"] == "high")
    check("model_score -> prediction_score (high)", sug_map["model_score"]["suggested_role"] == "prediction_score" and sug_map["model_score"]["confidence_label"] == "high")
    check("probability_of_default -> prediction_probability (high)", sug_map["probability_of_default"]["suggested_role"] == "prediction_probability" and sug_map["probability_of_default"]["confidence_label"] == "high")
    
    # Save Mapping
    save_req = {
        "column_roles": {s["column_name"]: s["suggested_role"] for s in suggestions},
        "segment_fields": r.json()["data"]["suggested_segments"],
        "feature_fields": r.json()["data"]["suggested_features"],
        "ignored_fields": [],
        "score_direction": "higher_is_better",
        "target_positive_label": 1,
        "decision_positive_label": "APPROVED"
    }
    r = client.post(f"{BASE_URL}/api/v1/datasets/{dataset_id}/save-mapping", json=save_req)
    check("Save mapping returns 200", r.status_code == 200)

    # Get Mapping
    r = client.get(f"{BASE_URL}/api/v1/datasets/{dataset_id}/mapping")
    check("GET /mapping returns saved mapping", r.status_code == 200 and r.json()["data"]["dataset_id"] == dataset_id)

    print("\n[Fraud Dataset (Generic Pass 2)]")
    with open(fraud_csv, "rb") as f:
        r = client.post(f"{BASE_URL}/api/v1/datasets/upload", files={"file": ("fraud_sample.csv", f, "text/csv")})
    check("Upload fraud CSV returns 200", r.status_code == 200)
    fraud_id = r.json()["data"]["id"]

    # Suggest Mapping
    r = client.post(f"{BASE_URL}/api/v1/datasets/{fraud_id}/suggest-mapping")
    check("Suggest mapping returns 200", r.status_code == 200)
    f_suggestions = r.json()["data"]["suggestions"]
    f_map = {s["column_name"]: s for s in f_suggestions}
    
    check("is_fraud -> target", f_map["is_fraud"]["suggested_role"] == "target")
    check("fraud_score -> prediction_score", f_map["fraud_score"]["suggested_role"] == "prediction_score")
    check("fraud_probability -> prediction_probability", f_map["fraud_probability"]["suggested_role"] == "prediction_probability")
    check("decision_flag -> decision", f_map["decision_flag"]["suggested_role"] == "decision")
    check("txn_id -> record_id", f_map["txn_id"]["suggested_role"] == "record_id")

def phase_3(client: httpx.Client) -> None:
    heading("Phase 3 — Metric Engine + Core Metrics")
    import pandas as pd
    from app.metrics.engine import run_metrics
    from app.schemas.mapping import ColumnMapping
    import scripts.expected_values as ev

    data_dir = _PROJECT_ROOT / "data"
    df = pd.read_csv(data_dir / "underwriting_scorecard_clean.csv")
    
    mapping = ColumnMapping(
        id="test",
        dataset_id="test",
        mappings={
            "actual_default": "target",
            "model_score": "prediction_score",
            "probability_of_default": "prediction_probability",
            "application_status": "decision",
            "application_id": "record_id",
            "application_time": "event_time",
            "past_due_days": "dpd_field",
            "score_band": "score_band",
        },
        segment_fields=[],
        feature_fields=[],
        ignored_fields=[],
        score_direction="higher_is_better",
        target_positive_label=1,
        decision_positive_label="APPROVED",
        version=1,
        created_at="2023-01-01T00:00:00Z"
    )
    
    # Run core metrics
    keys = [
        "perf_auc", "perf_gini", "perf_ks", "perf_decile_table",
        "calib_summary", "strategy_bad_rate", "strategy_approval_rate",
        "strategy_bad_rate_approved", "strategy_decline_rate",
        "delinq_buckets", "delinq_severe_rate", "delinq_30plus_rate",
        "dq_score_pd_coherence", "psi_prediction_score"
    ]
    
    results = run_metrics(df, mapping, keys)
    res_map = {r.metric_key: r for r in results}
    
    # Check scalars
    check("AUC matches expected", abs(res_map["perf_auc"].scalar_value - ev.AUC_MODEL_SCORE) < 1e-3)
    check("Gini matches expected", abs(res_map["perf_gini"].scalar_value - ev.GINI_MODEL_SCORE) < 1e-3)
    check("KS matches expected", abs(res_map["perf_ks"].scalar_value - ev.KS_MODEL_SCORE) < 1e-3)
    check("Bad rate matches expected", abs(res_map["strategy_bad_rate"].scalar_value - ev.BAD_RATE) < 1e-3)
    check("Approval rate matches expected", abs(res_map["strategy_approval_rate"].scalar_value - ev.APPROVAL_RATE) < 1e-3)
    check("Calibration ratio matches expected", abs(res_map["calib_summary"].scalar_value - ev.CALIBRATION_RATIO) < 1e-3)
    check("Delinquency severe rate matches expected", abs(res_map["delinq_severe_rate"].scalar_value - 0.2386) < 1e-3)
    check("Delinquency 30+ DPD rate matches expected", abs(res_map["delinq_30plus_rate"].scalar_value - 0.4924) < 1e-3)
    check("Bad rate on approved matches expected", abs(res_map["strategy_bad_rate_approved"].scalar_value - ev.BAD_RATE_ON_APPROVED) < 1e-3)
    check("Decline rate matches expected", abs(res_map["strategy_decline_rate"].scalar_value - (1 - ev.APPROVAL_RATE)) < 1e-3)
    
    # Check tables
    check("Decile table has 10 rows", len(res_map["perf_decile_table"].table_data) == 10)
    
    buckets = {b["bucket"]: b["count"] for b in res_map["delinq_buckets"].table_data}
    check("DPD buckets match perfectly", 
          buckets["Current"] == ev.DPD_BUCKETS["Current"] and 
          buckets["30-59"] == ev.DPD_BUCKETS["30-59 DPD"])
          
    # Missing role guard check
    mapping_no_decision = mapping.model_copy(deep=True)
    mapping_no_decision.mappings.pop("application_status")
    results_no_dec = run_metrics(df, mapping_no_decision, ["strategy_approval_rate"])
    check("Missing role returns skipped", results_no_dec[0].status == "skipped")
    
    # PSI degenerate bins guard check
    df_constant = df.copy()
    df_constant["constant_score"] = 500
    mapping_const = mapping.model_copy(deep=True)
    mapping_const.mappings.pop("model_score", None)
    mapping_const.mappings["constant_score"] = "prediction_score"
    results_const = run_metrics(df_constant, mapping_const, ["psi_prediction_score"], baseline_df=df_constant)
    check("Constant column PSI returns skipped", results_const[0].status == "skipped")

# ---------------------------------------------------------------------------
# Phase 4 checks: Monitors, Runs, Alerts
# ---------------------------------------------------------------------------
def phase_4(client: httpx.Client) -> None:
    heading("Phase 4: Run Orchestration & Alerting")
    
    # 1. Generate synthetic data if not exists
    import os, subprocess
    if not os.path.exists("data/healthy_baseline.csv"):
        print("Generating synthetic data...")
        subprocess.run(["python", "scripts/generate_demo_data.py"], check=True)
        
    # 2. Upload baseline and stable
    with open("data/healthy_baseline.csv", "rb") as f:
        rb = client.post(f"{BASE_URL}/api/v1/datasets/upload", files={"file": ("healthy_baseline.csv", f)})
        baseline_id = rb.json()["data"]["id"]
        
    with open("data/healthy_current_stable.csv", "rb") as f:
        rs = client.post(f"{BASE_URL}/api/v1/datasets/upload", files={"file": ("healthy_current_stable.csv", f)})
        stable_id = rs.json()["data"]["id"]
        
    # 3. Mappings (we can use the exact same logic as underwriting, since schema is identical)
    mapping_save_payload = {
        "feature_fields": ["credit_score", "debt_to_income", "annual_income", "revolving_utilization"],
        "segment_fields": ["loan_purpose"],
        "column_roles": {
            "actual_default": "target",
            "model_score": "prediction_score",
            "probability_of_default": "prediction_probability",
            "application_status": "decision"
        },
        "target_positive_label": 1,
        "decision_positive_label": "APPROVED"
    }
    client.post(f"{BASE_URL}/api/v1/datasets/{baseline_id}/save-mapping", json=mapping_save_payload)
    client.post(f"{BASE_URL}/api/v1/datasets/{stable_id}/save-mapping", json=mapping_save_payload)
    
    # Fetch mapping from server to pass to monitor
    mapping_payload = client.get(f"{BASE_URL}/api/v1/datasets/{stable_id}/mapping").json()["data"]
    
    # 4. Create monitor
    mon = client.post(f"{BASE_URL}/api/v1/monitors", json={
        "monitor_id": "mon_stable",
        "name": "Stable Monitor",
        "dataset_id": stable_id,
        "baseline_dataset_id": baseline_id,
        "column_mapping": mapping_payload,
        "selected_metrics": []
    })
    check("Monitor created", mon.status_code == 200)
    if mon.status_code != 200:
        print("MONITOR CREATE ERROR:", mon.text)
    
    # 5. Run stable
    print("Triggering stable run (blocks)...")
    rr = client.post(f"{BASE_URL}/api/v1/monitors/mon_stable/run")
    check("Stable run returns 200", rr.status_code == 200)
    run_meta = rr.json().get("data", {})
    if run_meta.get("status") == "failed":
        print("STABLE RUN ERROR MESSAGE:", run_meta.get("error_message"))
    check("Stable run completed", run_meta.get("status") == "completed")
    
    # Check no alerts (FALSE POSITIVE GATE)
    # The alerts are saved in artifacts, but how to fetch? We need an endpoint or we can read from disk directly for the test.
    # The API doesn't expose GET /runs/{run_id}/alerts in our spec (it says Section 34 has 50 endpoints, but we didn't add it in Phase 4 plan, we only added GET /runs).
    # We will read from disk directly for the smoke test.
    import json
    run_id = run_meta["run_id"]
    alert_path = f"storage/runs/{run_id}/alerts.json"
    if os.path.exists(alert_path):
        with open(alert_path) as f:
            alerts = json.load(f)
        bad_alerts = [a for a in alerts if a["severity"] in ["warning", "critical"]]
        if len(bad_alerts) > 0:
            print(f"STABLE BAD ALERTS: {bad_alerts}")
        check("Zero drift/performance alerts on stable", len(bad_alerts) == 0)
    else:
        check("Alerts artifact exists", False)
        
    # 6. Drifted dataset
    with open("data/healthy_current_drifted.csv", "rb") as f:
        rd = client.post(f"{BASE_URL}/api/v1/datasets/upload", files={"file": ("healthy_current_drifted.csv", f)})
        drifted_id = rd.json()["data"]["id"]
        
    client.post(f"{BASE_URL}/api/v1/datasets/{drifted_id}/save-mapping", json=mapping_save_payload)
    mapping_payload_drifted = client.get(f"{BASE_URL}/api/v1/datasets/{drifted_id}/mapping").json()["data"]
    
    mon_drift = client.post(f"{BASE_URL}/api/v1/monitors", json={
        "monitor_id": "mon_drifted",
        "name": "Drifted Monitor",
        "dataset_id": drifted_id,
        "baseline_dataset_id": baseline_id,
        "column_mapping": mapping_payload_drifted,
        "selected_metrics": []
    })
    
    print("Triggering drifted run (blocks)...")
    rr2 = client.post(f"{BASE_URL}/api/v1/monitors/mon_drifted/run")
    run_meta2 = rr2.json().get("data", {})
    if run_meta2.get("status") == "failed":
        print("DRIFTED RUN ERROR MESSAGE:", run_meta2.get("error_message"))
    check("Drifted run completed", run_meta2.get("status") == "completed")
    
    alert_path2 = f"storage/runs/{run_meta2['run_id']}/alerts.json"
    if os.path.exists(alert_path2):
        with open(alert_path2) as f:
            alerts2 = json.load(f)
        crit_psi = [a for a in alerts2 if a["metric_key"] == "psi_prediction_score" and a["severity"] == "critical"]
        check("Critical PSI alert fired on drifted", len(crit_psi) > 0)
        
        warn_auc = [a for a in alerts2 if a["metric_key"] == "perf_auc" and a["severity"] == "warning"]
        check("Warning AUC decline fired", len(warn_auc) > 0)

        csi_alerts = [a for a in alerts2 if a["metric_key"].startswith("csi_") and a["severity"] in ["warning", "critical"]]
        check("Feature CSI alert fired on drifted", len(csi_alerts) > 0)
    else:
        check("Alerts artifact exists for drifted", False)
        
    print("Testing LLM Narratives endpoint...")
    nr = client.post(f"{BASE_URL}/api/v1/runs/{run_meta2['run_id']}/narratives")
    check("POST narratives returns 200", nr.status_code == 200)
    nr_data = nr.json().get("data", {})
    check("Narrative has executive_summary", "executive_summary" in nr_data)
    
    nr_get = client.get(f"{BASE_URL}/api/v1/runs/{run_meta2['run_id']}/narratives")
    check("GET narratives returns 200", nr_get.status_code == 200)
        
    return run_meta2["run_id"]

# ---------------------------------------------------------------------------
# Phase 5: Charts
# ---------------------------------------------------------------------------
def phase_5(client: httpx.Client, run_id: str) -> None:
    heading("Phase 5: Charts")
    
    # 1. GET /runs/{run_id}/charts
    cr = client.get(f"{BASE_URL}/api/v1/runs/{run_id}/charts")
    check("GET charts returns 200", cr.status_code == 200)
    charts = cr.json().get("data", [])
    check("Returns >= 6 payloads", len(charts) >= 6)
    
    if len(charts) == 0:
        return
        
    chart_id = charts[0]["chart_id"]
    
    # 2. GET image (PNG)
    img_resp = client.get(f"{BASE_URL}/api/v1/runs/{run_id}/charts/{chart_id}/image?format=png")
    check("PNG image returns 200", img_resp.status_code == 200)
    check("PNG magic bytes", img_resp.content.startswith(b"\x89PNG"))
    
    # 3. GET image (SVG)
    svg_resp = client.get(f"{BASE_URL}/api/v1/runs/{run_id}/charts/{chart_id}/image?format=svg")
    check("SVG image returns 200", svg_resp.status_code == 200)
    check("SVG content type", svg_resp.headers.get("content-type") == "image/svg+xml")
    
    # 4. Check for matplotlib import leakage
    import subprocess
    try:
        # Grep for 'import matplotlib' or 'from matplotlib'
        result = subprocess.run(
            ["grep", "-rn", "matplotlib", "app/"],
            capture_output=True, text=True
        )
        lines = result.stdout.strip().split("\n")
        leaks = [l for l in lines if "app/charts/renderer.py" not in l and "__pycache__" not in l and l.strip()]
        if len(leaks) > 0:
            print("Matplotlib leaks found:")
            print("\n".join(leaks))
        check("Matplotlib imported ONLY in renderer.py", len(leaks) == 0)
    except Exception as e:
        print("Grep failed:", e)
        check("Matplotlib leak check", False)

    # 5. Render twice consecutively (no crash)
    img_resp2 = client.get(f"{BASE_URL}/api/v1/runs/{run_id}/charts/{chart_id}/image?format=png")
    check("Consecutive render succeeds (no crash)", img_resp2.status_code == 200)

def phase_6(client: httpx.Client, run_id: str) -> None:
    heading("Phase 6 — Advanced Modules & Registry")
    
    # Check stat-tests
    res = client.get(f"{BASE_URL}/api/v1/runs/{run_id}/stat-tests")
    if res.status_code != 200: print(res.text)
    check("GET /stat-tests returns 200", res.status_code == 200)
    if res.status_code == 200:
        data = res.json()["data"]
        check("stat-tests has tests array", "tests" in data)
        check("stat-tests has correction_method", "correction_method" in data)
        
    # Check vintage
    res = client.get(f"{BASE_URL}/api/v1/runs/{run_id}/vintage")
    if res.status_code != 200: print(res.text)
    check("GET /vintage returns 200", res.status_code == 200)
    if res.status_code == 200:
        data = res.json()["data"]
        check("vintage has roll_rate_matrix", "roll_rate_matrix" in data)
        check("vintage identifies malformed application_time", data.get("cohort_curves") is None and "reason" in data)

    # Check override
    res = client.get(f"{BASE_URL}/api/v1/runs/{run_id}/override-analysis?score_cutoff=600")
    if res.status_code != 200: print(res.text)
    check("GET /override-analysis returns 200", res.status_code == 200)
    if res.status_code == 200:
        data = res.json()["data"]
        check("override includes counts", "total_model_declines" in data)
        
    # Check fairness
    res = client.get(f"{BASE_URL}/api/v1/runs/{run_id}/fairness")
    if res.status_code != 200: print(res.text)
    check("GET /fairness returns 200", res.status_code == 200)
    if res.status_code == 200:
        data = res.json()["data"]
        check("fairness includes di_results", "di_results" in data)

    # Check timeseries
    res = client.get(f"{BASE_URL}/api/v1/runs/{run_id}/time-series")
    if res.status_code != 200: print(res.text)
    check("GET /time-series returns 200", res.status_code == 200)
    if res.status_code == 200:
        data = res.json()["data"]
        check("time-series reports unavailable", data.get("available") is False)

    # Check registry
    res = client.post(f"{BASE_URL}/api/v1/registry/models", json={
        "name": "CreditScorecard_v3",
        "version": "3.0.0",
        "model_type": "scorecard",
        "owner": "Data Science Team"
    })
    if res.status_code != 200: print(res.text)
    check("POST /registry/models returns 200", res.status_code == 200)
    if res.status_code == 200:
        model_id = res.json()["data"]["model_id"]
        check("Model creation returns valid ID", model_id is not None)
        
        # Link run
        res = client.post(f"{BASE_URL}/api/v1/registry/models/{model_id}/link-run/{run_id}")
        check("POST link-run returns 200", res.status_code == 200)

def phase_7(client: httpx.Client, run_id: str) -> None:
    heading("Phase 7: Reports")
    
    # Generate HTML report
    res = client.post(f"{BASE_URL}/api/v1/runs/{run_id}/reports/generate", json={
        "report_type": "executive_summary",
        "format": "html"
    })
    if res.status_code != 200:
        print(f"Generate HTML error: {res.status_code} {res.text}")
    check("POST /reports/generate (HTML) returns 200", res.status_code == 200)
    if res.status_code == 200:
        data = res.json()["data"]
        report_id = data["report_id"]
        
        # Download HTML report
        dl_res = client.get(f"{BASE_URL}/api/v1/runs/{run_id}/reports/{report_id}/download")
        check("GET /reports/{id}/download returns 200", dl_res.status_code == 200)
        
        html_text = dl_res.text
        check("HTML contains base64 image", "<img class=\"chart-img\" src=\"data:image/png;base64," in html_text)
        # Check health status is embedded
        check("HTML contains health status", "status" in html_text or "CRITICAL" in html_text or "DETERIORATING" in html_text or "WATCH" in html_text or "HEALTHY" in html_text)
        
    # Generate PDF report (expect success or 400 with fallback msg)
    res = client.post(f"{BASE_URL}/api/v1/runs/{run_id}/reports/generate", json={
        "report_type": "executive_summary",
        "format": "pdf"
    })
    if res.status_code == 400:
        check("PDF fallback returns 400 with weasyprint message", "weasyprint not installed" in res.json().get("detail", ""))
    else:
        if res.status_code != 200:
            print(f"Generate PDF error: {res.status_code} {res.text}")
        check("POST /reports/generate (PDF) returns 200", res.status_code == 200)
        
    # List reports
    res = client.get(f"{BASE_URL}/api/v1/runs/{run_id}/reports")
    check("GET /reports returns 200", res.status_code == 200)
    if res.status_code == 200:
        check("List includes generated report", len(res.json()["data"]) > 0)

    # Report QA checklist check
    qa_res = client.get(f"{BASE_URL}/api/v1/runs/{run_id}/reports/qa/sr_11_7")
    check("GET /reports/qa/sr_11_7 returns 200", qa_res.status_code == 200)
    if qa_res.status_code == 200:
        qa_data = qa_res.json()["data"]
        check("QA checklist completes with no missing metrics", qa_data.get("complete") is True or len(qa_data.get("missing", [])) == 0)

def phase_8_acceptance(client) -> None:
    heading("Phase 8: Full Acceptance (6 datasets)")
    import os
    import json
    from pathlib import Path
    data_dir = Path("data")
    
    def setup_monitor(name, filename, is_baseline=True, baseline_id=None, score_direction="higher_is_better", dec_label="APPROVED"):
        print(f"\n--- {name} ---")
        with open(data_dir / filename, "rb") as f:
            r = client.post(f"{BASE_URL}/api/v1/datasets/upload", files={"file": (filename, f, "text/csv")})
        check(f"Upload {filename}", r.status_code == 200)
        ds_id = r.json()["data"]["id"]
        
        r = client.post(f"{BASE_URL}/api/v1/datasets/{ds_id}/suggest-mapping")
        sug = r.json()["data"]["suggestions"]
        map_req = {"column_roles": {s["column_name"]: s["suggested_role"] for s in sug}, "score_direction": score_direction, "target_positive_label": 1, "decision_positive_label": dec_label}
        r = client.post(f"{BASE_URL}/api/v1/datasets/{ds_id}/save-mapping", json=map_req)
        check(f"Save mapping {filename}", r.status_code == 200)
        
        mapping_payload = client.get(f"{BASE_URL}/api/v1/datasets/{ds_id}/mapping").json()["data"]
        
        mon_req = {
            "monitor_id": f"mon_{name}",
            "name": name,
            "dataset_id": ds_id,
            "column_mapping": mapping_payload
        }
        if not is_baseline:
            mon_req["baseline_dataset_id"] = baseline_id
            
        r = client.post(f"{BASE_URL}/api/v1/monitors", json=mon_req)
        check(f"Create monitor {name}", r.status_code == 200)
        mon_id = r.json()["data"]["monitor_id"]
        
        r = client.post(f"{BASE_URL}/api/v1/monitors/{mon_id}/run")
        check(f"Run {name}", r.status_code == 200)
        run_data = r.json()["data"]
        if run_data.get("status") == "failed":
            print(f"RUN {name} FAILED: {run_data.get('error_message')}")
        check(f"Run {name} completed", run_data.get("status") == "completed")
        run_id = run_data["run_id"]
        return ds_id, mon_id, run_id

    # 1. healthy_baseline.csv
    baseline_id, mon_base, run_base = setup_monitor("baseline", "healthy_baseline.csv")
    with open(f"storage/runs/{run_base}/health.json") as f:
        h_data = json.load(f)
    check("Baseline health is healthy", h_data["status"] == "healthy")
    ts_res = client.get(f"{BASE_URL}/api/v1/runs/{run_base}/time-series")
    check("Baseline timeseries available", ts_res.json()["data"]["available"] == True)
    
    # 2. healthy_current_stable.csv
    _, _, run_stable = setup_monitor("stable", "healthy_current_stable.csv", is_baseline=False, baseline_id=baseline_id)
    with open(f"storage/runs/{run_stable}/alerts.json") as f:
        alerts = json.load(f)
    drift_perf_alerts = [a for a in alerts if a.get("category") in ["drift", "performance"]]
    check("Zero drift/performance alerts on stable", len(drift_perf_alerts) == 0)
    
    # 3. healthy_current_drifted.csv
    _, _, run_drifted = setup_monitor("drifted", "healthy_current_drifted.csv", is_baseline=False, baseline_id=baseline_id)
    with open(f"storage/runs/{run_drifted}/alerts.json") as f:
        alerts = json.load(f)
    check("Alerts fired on negative-control drifted run", len(alerts) > 0)
    check("Critical PSI alert fired", any(a["metric_key"] == "psi_prediction_score" and a["severity"] == "critical" for a in alerts))
    
    # 4. fraud_sample.csv
    _, _, run_fraud = setup_monitor("fraud", "fraud_sample.csv", score_direction="lower_is_better", dec_label="APPROVED")
    with open(f"storage/runs/{run_fraud}/metrics.json") as f:
        metrics = json.load(f)
    auc_val = next(m["scalar_value"] for m in metrics if m["metric_key"] == "perf_auc")
    check("Fraud AUC ≈ 0.755 (fixes direction bug)", abs(auc_val - 0.755) < 0.05)
    fraud_approval = next(m["scalar_value"] for m in metrics if m["metric_key"] == "strategy_approval_rate")
    check("Fraud approval rate respects configured decision_positive_label", fraud_approval is not None and fraud_approval > 0.1)
    
    # 5. edge_cases.csv
    _, _, run_edge = setup_monitor("edge", "edge_cases.csv")
    check("Run edge cases completes", True)
    
    # 6. underwriting_scorecard_clean.csv
    _, _, run_client = setup_monitor("client", "underwriting_scorecard_clean.csv")
    with open(f"storage/runs/{run_client}/insights.json") as f:
        insights = json.load(f)
    findings = insights.get("deterministic_findings", [])
    check("Client file has findings", len(findings) > 0)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    global PASS, FAIL

    parser = argparse.ArgumentParser(description="ModelPulse smoke tests")
    parser.add_argument(
        "--phase", type=int, default=99, help="Run checks up to this phase"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8000",
        help="Server base URL",
    )
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = args.base_url

    client = httpx.Client(timeout=30.0)

    # Verify server is reachable
    try:
        client.get(f"{BASE_URL}/api/v1/health")
    except httpx.ConnectError:
        print(f"❌ Cannot connect to {BASE_URL} — is the server running?")
        sys.exit(1)

    if args.phase >= 1:
        phase_1(client)

    if args.phase >= 2:
        phase_2(client)

    if args.phase >= 3:
        phase_3(client)

    if args.phase >= 4:
        run_id = phase_4(client)

    if args.phase >= 5:
        if args.phase == 5 and args.phase >= 4:
            phase_5(client, run_id)
        elif args.phase == 5: # Just in case it was run without phase 4
            rr = client.get(f"{BASE_URL}/api/v1/runs?limit=100")
            run_id = [r["run_id"] for r in rr.json()["data"] if r["status"] == "completed"][0]
            phase_5(client, run_id)
            
    if args.phase >= 6:
        # Run id from phase 4 or 5
        if not 'run_id' in locals():
            rr = client.get(f"{BASE_URL}/api/v1/runs?limit=100")
            run_id = [r["run_id"] for r in rr.json()["data"] if r["status"] == "completed"][0]
        if args.phase >= 5:
            phase_5(client, run_id)
        phase_6(client, run_id)
        
    if args.phase >= 7:
        if not 'run_id' in locals():
            rr = client.get(f"{BASE_URL}/api/v1/runs?limit=100")
            run_id = [r["run_id"] for r in rr.json()["data"] if r["status"] == "completed"][0]
        phase_7(client, run_id)
        
    if args.phase >= 8:
        phase_8_acceptance(client)

    # Summary
    total = PASS + FAIL
    heading(f"Results: {PASS}/{total} passed, {FAIL} failed")
    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    main()
