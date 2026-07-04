# BUILD PLAN — phased implementation with verification gates

Replaces SPEC.md Section 25 (which predates v3 and omits ~15 files). Work one
phase per session/turn-group. **A phase is done only when its exit criteria
pass.** Use plan mode at the start of each phase: read the referenced spec
sections + SPEC_AMENDMENTS.md, propose the file list, then implement.

Conventions: after each phase, update `scripts/smoke_test.py` so `--phase N`
covers the new surface, run it, fix failures, then commit
(`git commit -m "phase N: <summary>"`).

---

## Phase 0 — Scaffold
Files: `.gitignore`, `requirements.txt` (SPEC §3 minus seaborn), empty
package tree per SPEC §33. Data: `data/underwriting_scorecard_clean.csv` is
committed; run `python scripts/generate_demo_data.py` (already provided) to
produce `healthy_scorecard_baseline.csv`, `healthy_scorecard_current.csv`,
`fraud_sample.csv`, and `data/edge_cases/*`. Read `docs/VALIDATION_MATRIX.md`
and `docs/EXPERT_NOTES.md` once now — they define the acceptance behavior.
**Exit:** `pip install -r requirements.txt` succeeds (if weasyprint fails,
comment it and note the fallback per amendment B6); `python -c "import fastapi, pandas, sklearn, scipy, matplotlib"` OK;
all generated CSVs load in pandas with the shapes pinned in
`scripts/expected_values*.py`.

## Phase 1 — Foundation
Spec: §6, §7, §22, §24. Files: `main.py`, `app/core/*`, `app/storage/*`
(excluding model_registry_store), `app/schemas/common.py`, `app/utils/*`,
`app/api/routes/health.py`.
**Exit:** `uvicorn main:app` starts clean; `GET /api/v1/health` → 200 envelope;
a scratch script round-trips create/get/list/update/delete on one store;
CORS middleware present.

## Phase 2 — Datasets, profiling, mapping
Spec: §2, §8, §9, §10, §27, §28 (+ amendments A: mapping schema winners).
Files: `app/schemas/dataset.py`, `app/schemas/mapping.py`,
`app/profiling/profiler.py`, `app/mapping/heuristics.py` (two-pass: exact
vocab → generic pattern/value inference), `app/mapping/validator.py`,
`app/services/dataset_service.py`, `app/services/mapping_service.py`,
routes `datasets.py`, `mappings.py`.
**Exit (smoke --phase 2):** upload underwriting CSV → 197 rows / 22 cols;
profile flags `application_time_malformed`, `risk_rating_truncated`,
`low_bad_count`, and `record_id_not_unique` (amendment E3 — only 20 distinct
IDs); suggest-mapping assigns target/prediction_score/
prediction_probability/decision/dpd_field correctly with high confidence;
save-mapping then GET mapping round-trips. **Then the same flow on
`fraud_sample.csv`:** `is_fraud`→target, `fraud_probability`→
prediction_probability, `fraud_score`→prediction_score, `decision_flag`→
decision via generic heuristics. Upload `edge_cases/edge_messy_headers.csv`
→ normalization maps `Application ID` / `Model-Score` / `APPLICATION.STATUS`
to the right roles. Rejects a .txt upload with 400.

## Phase 3 — Metric engine + core metrics
Spec: §12, §13 (+ amendments B3, B5, C5, C6). Files: `app/schemas/metrics.py`,
`app/schemas/charts.py` (canonical ChartPayload per amendment A),
`app/metrics/base.py`, `registry.py`, `engine.py`, implementations:
`data_quality.py`, `drift.py`, `performance.py`, `calibration.py`,
`strategy.py`, `delinquency.py`, plus the four expert additions from
amendment F1 (score–PD coherence, inverted-ranking guard, leakage suspicion,
band consistency).
**Exit:** a scratch script loads the sample CSV + saved mapping, runs the
engine directly and matches `scripts/expected_values.py` (±1e-3):
AUC=0.3341 / Gini=−0.3319 (yes, below 0.5 — see amendment E2), KS=0.3563,
bad_rate=0.0558, approval_rate=0.7716, calibration_ratio=0.5935,
decile table rows == 10, DPD buckets == {Current:100, 1-29:0, 30-59:24,
60-89:26, 90+:47}; every metric missing a role returns `skipped` (test by
removing `decision` from mapping); PSI on a constant column returns `skipped`
not an exception.

## Phase 4 — Monitors, runs, segmentation, alerts, insights, health score
Spec: §11, §14, §15, §16, §18, §19, §20 (+ amendments B1, B4, C3).
Files: `app/schemas/monitor.py`, `run.py`, `segments.py`, `alerts.py`,
`insights.py`; `app/segmentation/engine.py`, `app/alerts/engine.py`,
`app/services/monitor_service.py`, `run_service.py`, `insight_service.py`,
`health_score_service.py`, `llm_service.py` (mock only); routes `monitors.py`,
`runs.py` (core endpoints), `helpers.py`. BaselineStats incl. histogram bins
(amendment B2).
**Exit (smoke --phase 4):** create monitor → run → COMPLETED;
`/runs/{id}/summary` populated; `/runs/{id}/results` returns the full
composite; alerts include CRITICAL `delinq_severe_rate` (0.239 > 0.20) and
CRITICAL `delinq_30plus_rate` (0.492 > 0.25); findings include
low-bad-count, truncated VERY_HIG, duplicate record IDs, calibration-critical
(ratio 0.594), and the inverted rank-ordering finding (AUC < 0.5 — amendment
E2); health score lands in the deteriorating/critical band, NOT 78; all run
artifact JSONs exist under `storage/runs/{run_id}/`; run with a deliberately
broken dataset_id → 404 envelope, not a 500.
**Baseline-comparison gates (expected_values_synthetic.py):** designate
`healthy_baseline.csv` as baseline; run `healthy_current_stable.csv` against
it → ZERO warning/critical drift or performance alerts (false-positive gate);
run `healthy_current_drifted.csv` against it → the pinned alert set fires
(score PSI ≈ 0.262 critical, AUC decline ≈ 0.036 warning, calibration ratio
≈ 1.48 warning-high, approval −19.6pp critical, bad-on-approved +12pp
critical, severe-DPD 0.209 critical, strategy-deterioration finding);
standalone run of `healthy_baseline.csv` → health status "healthy". Run of
`edge_cases.csv` → status COMPLETED with data-quality findings. **Then the two control runs
(VALIDATION_MATRIX §2–3):** run `healthy_scorecard_baseline.csv` standalone →
ZERO critical alerts, health "healthy", monotonicity PASS (any red = platform
bug); then run `healthy_scorecard_current.csv` WITH baseline attached →
perf CRITICAL alerts (AUC −0.0855, KS −0.1147), CSI annual_income 0.480
critical, PSI model_score 0.057 must NOT alert, quiet-decay finding fires
(EXPERT_NOTES §2.2), approval-rate change +4.7pp must NOT alert
(false-positive control). Values per `scripts/expected_values_healthy.py`.

## Phase 5 — Charts (payload generation + Agg renderer)
Spec: §17 chart list, §32 renderer (+ amendments A: renderer winner,
on-demand images, no StaticFiles). Files: chart-payload builders inside the
run pipeline (all 10 required charts when roles allow), `app/charts/renderer.py`,
chart endpoints on the runs router incl. `/charts/{chart_id}/image` and
`/charts?format=png` ZIP and `POST /charts/render-all`.
**Exit (smoke --phase 5):** `/runs/{id}/charts` returns ≥6 payloads for the
sample run; one image endpoint returns bytes starting `\x89PNG`; svg variant
returns `image/svg+xml`; grep confirms `matplotlib` imported only in
`app/charts/renderer.py`; two consecutive image requests succeed (no
figure-leak crash).

## Phase 6 — Advanced modules
Spec: §31 modules 8, 11, 14, 15, 17, 18, 19 (+ amendments C1, C2, C7, C8).
Files: implementations `score_distribution.py`, `statistical_tests.py`,
`vintage.py`, `override.py`, `fairness.py`; `app/services/timeseries_service.py`;
registry: `app/schemas/registry.py`, `app/storage/model_registry_store.py`,
`app/api/routes/registry.py`; schemas `fairness.py`, `override.py`.
**Exit (smoke --phase 6):** `/stat-tests` returns corrected p-values;
fraud dataset mapped with `score_direction="lower_is_better"` yields
AUC ≈ 0.755 (amendment F3 — 0.245 means direction handling is broken);
`/vintage` returns roll-rate matrix with `cohort_curves: null` + reason;
`/time-series` returns `available: false` for the sample data;
`/override-analysis?score_cutoff=600` returns counts consistent with the data;
`/fairness` returns DI per group with proxy notes; registry CRUD +
champion-challenger round-trip works.

## Phase 7 — Reports
Spec: §31 Module 6/20 (+ amendment B6). Files: `app/schemas/reports.py`,
`app/services/report_service.py`, `app/templates/reports/*` (base,
executive_summary, full_technical, sr_11_7, ifrs9 — self-contained inline CSS,
base64-embedded charts via `renderer.render_to_base64`), report endpoints.
**Exit (smoke --phase 7):** generate executive_summary as HTML → file exists,
contains `<img src="data:image/png;base64,` and the health status string;
download endpoint streams it with attachment headers; PDF either works or
returns the documented 400 fallback message.

## Phase 8 — Polish & full acceptance
Files: `README.md` (setup incl. weasyprint OS deps, run, 10-minute demo
script per SPEC §26), `.env.example`; final `scripts/smoke_test.py` covering
everything for BOTH datasets.
**Exit:** fresh clone simulation — delete `storage/`, restart server, run
`python scripts/smoke_test.py` end-to-end green for the ENTIRE validation
matrix: negative control (underwriting), positive control (healthy baseline),
drift case (baseline→current), agnostic control (fraud, incl.
lower_is_better direction and APPROVE label), and all 8 edge-case files
(graceful degradation, never a 500, no NaN in any JSON);
`grep -rn "model_score\|actual_default\|application_status" app/ --include=*.py`
shows hits only in `app/mapping/heuristics.py` vocab (dataset-agnostic check).
