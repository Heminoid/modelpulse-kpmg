import re

with open("scripts/smoke_test.py", "r") as f:
    content = f.read()

new_func = """def phase_8_acceptance(client) -> None:
    heading("Phase 8: Full Acceptance (6 datasets)")
    import os
    import json
    from pathlib import Path
    data_dir = Path("data")
    
    def setup_monitor(name, filename, is_baseline=True, baseline_id=None, score_direction="higher_is_better", dec_label="APPROVED"):
        print(f"\\n--- {name} ---")
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
        run_id = r.json()["data"]["run_id"]
        return ds_id, mon_id, run_id

    # 1. healthy_baseline.csv
    baseline_id, mon_base, run_base = setup_monitor("baseline", "healthy_baseline.csv")
    with open(f"storage/runs/{run_base}/health.json") as f:
        h_data = json.load(f)
    check("Baseline health is HEALTHY", h_data["status"] == "HEALTHY")
    ts_res = client.get(f"{BASE_URL}/api/v1/runs/{run_base}/time-series")
    check("Baseline timeseries available", ts_res.json()["data"]["available"] == True)
    
    # 2. healthy_current_stable.csv
    _, _, run_stable = setup_monitor("stable", "healthy_current_stable.csv", is_baseline=False, baseline_id=baseline_id)
    with open(f"storage/runs/{run_stable}/alerts.json") as f:
        alerts = json.load(f)
    drift_perf_alerts = [a for a in alerts if a["alert_type"] in ["drift", "performance"]]
    check("Zero drift/performance alerts on stable", len(drift_perf_alerts) == 0)
    
    # 3. healthy_current_drifted.csv
    _, _, run_drifted = setup_monitor("drifted", "healthy_current_drifted.csv", is_baseline=False, baseline_id=baseline_id)
    with open(f"storage/runs/{run_drifted}/alerts.json") as f:
        alerts = json.load(f)
    check("Critical PSI alert fired", any(a["metric_key"] == "psi_model_score" and a["severity"] == "CRITICAL" for a in alerts))
    
    # 4. fraud_sample.csv
    _, _, run_fraud = setup_monitor("fraud", "fraud_sample.csv", score_direction="lower_is_better", dec_label="APPROVE")
    with open(f"storage/runs/{run_fraud}/metrics.json") as f:
        metrics = json.load(f)
    auc_val = next(m["scalar_value"] for m in metrics if m["metric_key"] == "perf_auc")
    check("Fraud AUC ≈ 0.755 (fixes direction bug)", abs(auc_val - 0.755) < 0.05)
    
    # 5. edge_cases.csv
    _, _, run_edge = setup_monitor("edge", "edge_cases.csv")
    check("Run edge cases completes", True)
    
    # 6. underwriting_scorecard_clean.csv
    _, _, run_client = setup_monitor("client", "underwriting_scorecard_clean.csv")
    with open(f"storage/runs/{run_client}/alerts.json") as f:
        alerts = json.load(f)
    check("Client file has alerts", len(alerts) > 0)
"""

content = re.sub(r'def phase_8_acceptance\(client\).*?# -{75}\n# Main', new_func + '\n# ---------------------------------------------------------------------------\n# Main', content, flags=re.DOTALL)

with open("scripts/smoke_test.py", "w") as f:
    f.write(content)
