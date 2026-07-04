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
        "delinq_buckets", "dq_score_pd_coherence", "psi_model_score"
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
    results_const = run_metrics(df_constant, mapping_const, ["psi_model_score"], baseline_df=df_constant)
    check("Constant column PSI returns skipped", results_const[0].status == "skipped")

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

    # Summary
    total = PASS + FAIL
    heading(f"Results: {PASS}/{total} passed, {FAIL} failed")
    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    main()
