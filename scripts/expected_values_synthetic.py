"""
GROUND TRUTH for the synthetic test-data suite (data/healthy_*.csv,
fraud_sample.csv, edge_cases.csv) — computed from the SHIPPED files using the
spec's exact PSI implementation (quantile bins fitted on baseline, 10 bins,
eps=1e-4). Float tolerance 1e-3 unless noted; PSI tolerance 0.02 (binning
implementations may differ slightly at edges).

Purpose of each dataset (see docs/EXPERT_PLAYBOOK.md for the full matrix):
  healthy_baseline         POSITIVE CONTROL — everything green
  healthy_current_stable   NO-FALSE-ALARM control vs baseline
  healthy_current_drifted  ALERT control vs baseline — known breach set
  fraud_sample             dataset-agnostic + lower_is_better direction control
  edge_cases               data-quality detection control
"""

# ── healthy_baseline.csv ────────────────────────────────────────────────────
BASE = dict(
    rows=5000, bads=458, bad_rate=0.0916,
    auc=0.7854, gini=0.5708, ks=0.4353,          # healthy discrimination
    approval_rate=0.8012, bad_rate_on_approved=0.0632,
    calibration_ratio=1.0000,                     # perfectly calibrated
    severe_dpd_rate=0.0660,                       # below 0.10 warning
    monotonicity="PASS",
    band_bad_rates={"<600": 0.2774, "600-700": 0.0753, "700-800": 0.0189, "800+": 0.0},
    time_parseable=True,                          # time-series module ACTIVATES
)
# Expected run outcome: NO critical alerts; health score in "healthy" band.

# ── healthy_current_stable.csv (vs baseline) ────────────────────────────────
STABLE = dict(
    rows=2500, bad_rate=0.1048, auc=0.7948, ks=0.4664,
    approval_rate=0.7920, calibration_ratio=1.1053, monotonicity="PASS",
)
STABLE_PSI = {   # ALL well below 0.10 — no drift alerts may fire
    "model_score": 0.0077, "probability_of_default": 0.0052,
    "credit_score": 0.0042, "debt_to_income": 0.0074,
    "annual_income": 0.0047, "revolving_utilization": 0.0052,
}
STABLE_AUC_DELTA = +0.0095   # improvement — no decline alert
# Expected run outcome vs baseline: GREEN. Any warning/critical drift or
# performance alert here is a FALSE POSITIVE and a smoke-test failure.

# ── healthy_current_drifted.csv (vs baseline) ───────────────────────────────
DRIFTED = dict(
    rows=2500, bads=695, bad_rate=0.2780, auc=0.7490, ks=0.3716,
    approval_rate=0.6048, bad_rate_on_approved=0.1832,
    calibration_ratio=1.4797,   # model UNDER-predicts risk (unseen macro shock)
    severe_dpd_rate=0.2088, monotonicity="PASS",
)
DRIFTED_PSI = {
    "model_score": 0.2622,            # > 0.25  -> CRITICAL drift alert
    "probability_of_default": 0.2719, # > 0.25  -> CRITICAL
    "credit_score": 0.1252,           # 0.10-0.25 -> monitor/warning
    "debt_to_income": 0.1724,         # 0.10-0.25 -> monitor/warning
    "annual_income": 0.0377,          # stable
    "revolving_utilization": 0.0776,  # stable
}
DRIFTED_CAT_PSI_LOAN_PURPOSE = 0.0917
DRIFTED_AUC_DECLINE = 0.0364          # > 0.03 warning (below 0.05 critical)
DRIFTED_APPROVAL_CHANGE = -0.1964     # |Δ| > 0.10 -> CRITICAL policy shift
DRIFTED_BAD_ON_APPROVED_INCREASE = +0.1200  # > 0.05 -> CRITICAL
# Expected alerts (minimum set): critical PSI (score + pd), warning CSI
# (credit_score, dti), warning AUC decline, warning-high calibration ratio,
# critical approval-rate change, critical bad-rate-on-approved increase,
# critical severe-DPD (0.209 > 0.20), "strategy deterioration" finding
# (approval down + bad rate up). Health score must land deteriorating/critical.

# ── fraud_sample.csv ────────────────────────────────────────────────────────
FRAUD = dict(
    rows=800, frauds=31, fraud_rate=0.03875,
    auc_higher_is_risk=0.7549,   # mapped with score_direction="lower_is_better"
    decisions={"APPROVED": 743, "BLOCKED": 39, "REVIEW": 18},
)
# Controls: generic heuristics map txn_id/txn_date/fraud_score/
# fraud_probability/is_fraud/decision_flag with zero code changes;
# 31 positives -> low_bad_count warning; 3-valued decision -> validator
# warning (not failure); direction lower_is_better must yield AUC 0.755,
# not 0.245 — this is THE score-direction regression test.

# ── edge_cases.csv ──────────────────────────────────────────────────────────
EDGE = dict(
    rows=420, duplicate_rows=20,
    null_pct={"annual_income": 0.0976, "employment_length": 0.1738,
              "model_score": 0.0738},                # score > 5% -> score_null_high
    invalid_prob_gt1=3, invalid_prob_lt0=2,          # data_quality_invalid_probability = 5
    malformed_time_rows=125,                         # ~30% -> event_time parse warning
    constant_column="channel",                       # PSI/CSI must skip, not crash
    id_like_free_text="notes",                       # uniq ratio 0.952 -> id-candidate
)
# Controls: upload+profile+map+run must COMPLETE (status=completed) with
# warnings — a monitoring platform that crashes on dirty data is useless.
