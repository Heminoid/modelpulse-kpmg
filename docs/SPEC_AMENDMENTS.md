# SPEC AMENDMENTS — canonical resolutions & bug fixes

**This file overrides `docs/SPEC.md` wherever the two conflict.** The spec grew
by accretion (v2.0 → v2.1 → v3) and contains duplicate, contradictory
definitions of several components. This file picks the winner for each and
fixes bugs in the spec's sample code. When implementing, follow this file first.

---

## A. Supersession rules (which section wins)

| Component | Winner | Losers (ignore) |
|---|---|---|
| Folder structure | Section 33 | Section 4 |
| Chart renderer | **Section 32** (`ChartRenderer`, dark theme, stateless, ChartPayload-only) | Section 17's function renderer; Section 29's `ChartRenderer` (light palette, takes DataFrames — violates Rule 3) |
| ChartPayload schema | Section 17 base + `image_url: Optional[str] = None` (Section 32 addition) | Section 29's variant (`image_path`, `image_base64` fields — drop them) |
| Image generation timing | **On-demand** (Section 0 Rule 2): render at request time from stored `charts.json`. Exception: report generation persists its embedded images. | Section 29's "render all PNGs during the run + StaticFiles" flow |
| Mapping suggestion schema | Section 28 (`ColumnSuggestion` + rich `MappingSuggestion`, float confidence) | Section 10's simpler `MappingSuggestion` |
| Save-mapping request body | Section 28 `SaveMappingRequest` → service converts to persisted `ColumnMapping` (Section 10) | Section 21's claim that the body is `ColumnMapping` directly |
| Endpoint list | Section 34 (50 endpoints) | Section 21 where they differ |
| `GET /runs/{run_id}/charts?format=png` | Section 32: returns ZIP of all PNGs | Section 21's "not valid on list endpoint" |
| Requirements | Section 3 list, **minus** any seaborn. Do NOT add seaborn (Section 29 mentions it; Section 32's renderer doesn't use it). | — |
| Static file serving | Do NOT mount all of `storage/` (Section 29 exposes uploaded CSVs & configs). Serve chart images only via the `/charts/{chart_id}/image` endpoint; serve generated reports only via the `/reports/{report_id}/download` endpoint. No `StaticFiles` mount needed. | Section 29's `app.mount("/static", StaticFiles(directory="storage"))` |

## B. Design decisions the spec leaves ambiguous

1. **Run lifecycle vs sync execution.** Computation is synchronous (Section 5),
   so `POST /monitors/{id}/run` blocks until the run finishes and returns the
   final `RunSummary`. The PENDING/RUNNING states still exist and are persisted
   at the appropriate moments (they matter for crash forensics and future async
   support), but a successful response always reflects COMPLETED or FAILED.
2. **Baseline feature-overlay charts.** Section 19 forbids reloading the raw
   baseline CSV, but Section 29's feature grid needs baseline distributions.
   Resolution: extend `BaselineStats` with per-numeric-column histogram data
   (`{col: {"bin_edges": [...], "counts": [...]}}`, 20 bins) computed once at
   baseline designation. Overlay charts are built from these stored bins.
   Never reload the baseline CSV during a run.
3. **Calibration bin count is adaptive** (spec buries this in the known-issues
   table): use `n_bins = 5 if row_count < 200 else settings.default_calibration_bins`.
   Apply the same rule to Hosmer–Lemeshow groups.
4. **Pagination totals.** `PaginatedResponse` requires `total`. Every store
   `list()` returns `tuple[list[dict], int]` — (page items, total count).
5. **PSI degenerate-bins guard.** After `np.unique(bin_edges)`, if fewer than
   3 edges remain (near-constant column), return the metric with
   `status="skipped"`, `skipped_reason="insufficient value variation for binning"`.
6. **WeasyPrint fallback.** WeasyPrint needs OS-level pango/cairo and often
   fails to install. Import it lazily inside `report_service.py`; if the import
   fails, PDF requests return a 400 with message
   `"PDF rendering unavailable (weasyprint not installed) — request format=html instead"`,
   and HTML report generation must work regardless. README documents the
   system-package requirement (e.g. `apt install libpango-1.0-0 libpangocairo-1.0-0`).
7. **Missing endpoints to add** (implied by the spec but absent from Section 34):
   `DELETE /api/v1/datasets/{dataset_id}` (store already defines `delete`).
   Also ship a root `.gitignore` covering `storage/`, `.venv/`, `__pycache__/`, `.env`.
8. **`GET /runs?monitor_id=` filter** (Section 21) applies before pagination.

## C. Bug fixes — the spec's sample code is WRONG here; implement these instead

1. **Hosmer–Lemeshow statistic (Section 31, Module 11).** The spec's expression
   algebraically cancels to nonsense. Correct per-group term, then sum:
   ```python
   pi_bar = grouped["exp"] / grouped["n"]          # mean predicted prob per group
   hl_stat = (((grouped["obs"] - grouped["exp"]) ** 2)
              / (grouped["n"] * pi_bar * (1 - pi_bar))).sum()
   ```
   Guard: drop groups where `pi_bar` is 0 or 1; require ≥3 groups after drops
   else return `skipped`.

2. **Chi-square categorical drift (Module 11, Test 2).** `chi2_contingency`
   expects a contingency table, not obs/exp columns. Use goodness-of-fit:
   ```python
   from scipy.stats import chisquare
   cats = sorted(set(baseline_freqs) | set(current_counts.index))
   f_obs = np.array([current_counts.get(c, 0) for c in cats], dtype=float)
   f_exp = np.array([baseline_freqs.get(c, 0.0) for c in cats]) * f_obs.sum()
   f_exp = np.clip(f_exp, 1e-6, None)          # avoid zero expected
   stat, p = chisquare(f_obs, f_exp)
   ```
   Set `small_sample_warning=True` if any expected cell < 5.

3. **Health score component scorers (Section 18).** The spec's lambdas are off
   by a factor of 100 (`v * 100 / 0.7 * 100`). Correct versions:
   ```python
   "perf_gini":           lambda v: min(100.0, max(0.0, v / 0.7 * 100)),
   "perf_ks":             lambda v: min(100.0, max(0.0, v / 0.5 * 100)),
   "psi_model_score":     lambda v: max(0.0, 100 - (v / 0.25) * 100),
   "calib_ratio_overall": lambda v: max(0.0, 100 - abs(1 - v) * 200),
   "perf_auc":            lambda v: min(100.0, max(0.0, (v - 0.5) / 0.3 * 100)),
   ```
   Also: the scorer dict key must be `calib_ratio_overall` to match
   `HEALTH_WEIGHTS` (spec uses `calib_ratio` in one place — a silent lookup miss).
   If a weighted component is unavailable (metric skipped), renormalize the
   remaining weights instead of scoring it 0.

4. **`app/schemas/common.py`** — the spec uses `Field(default_factory=...)`
   without importing `Field`. Import it. And per CLAUDE.md rule 4, every
   Optional field across ALL schemas gets an explicit `= None`.

5. **Decile table with 11 bads / 197 rows.** `pd.qcut` on scores with ties can
   fail or produce uneven bins. Rank first:
   `df["decile"] = pd.qcut(df[score].rank(method="first", ascending=False), 10, labels=False) + 1`
   (descending because higher score = lower risk → decile 1 = best scores).
   Lift for decile d = (bad_rate_d / overall_bad_rate); guard division by zero
   when overall bad rate is 0.

6. **`ks_2samp` guard:** if either goods or bads group is empty, skip with reason.

7. **Fairness DI:** guard `overall_ar == 0`; skip groups with n == 0.

8. **`false_discovery_control`** exists only in scipy ≥ 1.11 — fine with pinned
   1.13.0, but wrap in try/except and fall back to Bonferroni if unavailable.

## D. Demo & acceptance artifacts (required deliverables)

1. `data/underwriting_scorecard_clean.csv` — the sample dataset (place it here;
   if absent, generate a synthetic 197-row file matching Section 2's exact
   columns, value domains, and quirks — including the constant `"46:27.6"`
   application_time, `VERY_HIG`, `MORTGAG`, one `past_due_days=50`, 11 defaults).
2. `scripts/generate_demo_data.py` (PROVIDED — do not rewrite) generates the
   synthetic controls, all seeded/deterministic:
   `healthy_scorecard_baseline.csv` (3000 rows, positive control),
   `healthy_scorecard_current.csv` (1500 rows, drift case),
   `fraud_sample.csv` (400 rows, agnostic control: different vocabulary,
   `lower_is_better` score direction, `APPROVE`/`DECLINE` labels), and 8
   adversarial files in `data/edge_cases/`.
3. `docs/VALIDATION_MATRIX.md` — the QA contract: every dataset's required
   platform behavior. `docs/EXPERT_NOTES.md` §2 adds ~9 deterministic finding
   rules beyond SPEC §20 (quiet decay, selection-bias caveat,
   outcome-for-declines anomaly, band inconsistency, etc.) — implement the
   [POC]-tagged ones in `insight_service.py`. Pinned numbers live in
   `scripts/expected_values.py` and `scripts/expected_values_healthy.py`.
4. `scripts/smoke_test.py` — httpx script executing the full Section 26 demo
   flow against a running server for BOTH datasets, asserting status codes,
   presence of expected warnings/findings, non-empty PNG bytes (magic number
   `\x89PNG`), and **exact values from `scripts/expected_values.py`**
   (tolerance 1e-3). Exit non-zero on any failure. Accepts `--phase N` to run
   only checks available up to phase N.

---

## E. GROUND TRUTH CORRECTIONS — the spec's demo numbers are WRONG for this CSV

`scripts/expected_values.py` contains values computed directly from
`data/underwriting_scorecard_clean.csv`. Where SPEC.md claims different
numbers, **expected_values.py wins.** Key corrections:

1. **SPEC §26 step 7 is fiction.** It claims AUC=0.82, Gini=0.64, KS=0.43,
   health_score=78. Actual (with the mapped `higher_is_better` direction):
   AUC=0.334, Gini=−0.332, KS=0.356, Brier skill negative, calibration ratio
   0.594 (critical band). Do NOT tune code to reproduce the spec's numbers —
   they are unreachable from this data.
2. **The model in this dataset is genuinely broken, and that IS the demo.**
   `model_score` has ~zero correlation with `probability_of_default` (−0.03)
   and *positive* correlation with default (+0.12). Bad rate by score band is
   anti-monotonic (`<600` band is the SAFEST at 1.45%); `risk_rating` is
   inverted (LOW has the highest bad rate, VERY_HIG has zero). Keep
   `score_direction="higher_is_better"` as mapped and let the platform report
   the truth: monotonicity check FAILS, AUC-below-0.5 triggers a critical
   rank-ordering finding, calibration critical, severe-DPD (23.9% > 20%) and
   30+ DPD (49.2% > 25%) critical alerts fire. Add one deterministic finding
   template for AUC < 0.5: "Score rank-ordering is inverted vs the configured
   score direction — model may be broken or direction misconfigured; review
   mapping." The demo narrative (README §demo) becomes: *"the platform
   correctly detects a deteriorated/broken scorecard"* — far more convincing
   for a monitoring product than an all-green dashboard.
3. **`application_id` is NOT unique**: 20 distinct values × ~10 rows each
   (uniqueness ratio 0.10). The value-pattern ID heuristic (>90% unique) must
   NOT fire; the name heuristic maps it to `record_id` with medium confidence
   and the profiler adds a new warning `record_id_not_unique` (+ a data
   quality finding). Do not let mapping validation hard-fail on this.
4. **Override analysis (SPEC Module 15) numbers corrected**: at
   `model_score < 600` cutoff → 73 model-declines (not 69), 60 approved
   (82.2% override rate, not 81.2%/56), override bad rate 3.33% vs normal
   approved 6.52% (not 1.8% vs 7.3%). The headline insight
   (overrides outperform) still holds. Note: the `score_band` COLUMN has 69
   rows in `<600` but disagrees with `band(model_score)` on ~13% of rows —
   compute the override analysis from raw `model_score`, never from the band
   column, and add a data-quality note about band inconsistency.
5. **Fairness numbers verified exactly as spec claims**: credit_car DI=0.831,
   75-100K DI=0.844, home_ownership OTHER DI=0.926 with n=14 low-power flag.
6. **Zero nulls, zero duplicate full rows** in the file — the null-rate and
   duplicate metrics must report 0, and the `1-29 DPD` bucket must report 0
   (only DPD values present: 0, 30, 50, 60, 90, 120; the single 50 → 30-59).
7. **Approved vs declined scores are statistically identical** (643.1 vs
   644.8) — the Mann-Whitney test (Module 11 Test 5) should NOT reject H₀;
   don't treat a non-significant result there as a bug.

---

## F. EXPERT ADDITIONS + SYNTHETIC TEST SUITE (see docs/EXPERT_PLAYBOOK.md)

### F1. Four new metrics/findings (small, high-value; add to Phase 3/4 scope)
1. `dq_score_pd_coherence` — Spearman ρ between mapped `prediction_score` and
   `prediction_probability` (requires both roles). With
   `higher_is_better`, expect ρ strongly negative (positive for
   `lower_is_better`). |ρ| < 0.3 ⇒ **critical** finding "score and PD
   disagree"; wrong sign with |ρ| ≥ 0.3 ⇒ critical "direction misconfigured".
   (Client demo file: ρ ≈ −0.03 ⇒ fires.)
2. `perf_inverted_ranking` — if computed AUC < 0.5 in the configured
   direction ⇒ **critical** finding with template: "Score rank-ordering is
   inverted vs the configured score direction — model may be broken or
   direction misconfigured; review mapping." Report AUC as computed (do NOT
   silently flip it).
3. `perf_leakage_suspicion` — AUC > 0.97 ⇒ warning "suspiciously perfect
   discrimination — check target leakage / post-outcome features".
4. `dq_band_consistency` — if both a band column (`score_band` role) and the
   score are mapped: share of rows where the band column matches the band
   derived from the score. < 0.95 ⇒ warning finding (client file: 0.868).
   Also promote Module 11 Test 5 into a finding: if approved-vs-declined
   score separation is not significant ⇒ info/warning "decisions do not
   appear score-driven".

### F2. Synthetic test-data suite (shipped in data/, generator in scripts/)
`healthy_baseline.csv` (5,000), `healthy_current_stable.csv` (2,500),
`healthy_current_drifted.csv` (2,500), `fraud_sample.csv` (800),
`edge_cases.csv` (420). Regenerable via `scripts/generate_demo_data.py`
(seeded; score scaling and PD calibration fitted on baseline and applied
fixed to the current sets — production-style). Pinned ground truth:
`scripts/expected_values_synthetic.py`. The acceptance grid in
EXPERT_PLAYBOOK §3 is the Phase 8 definition of done — including the
**no-false-positive gate**: the stable-vs-baseline run must produce ZERO
warning/critical drift or performance alerts.

### F3. Score-direction is a first-class regression test
`fraud_sample.csv` must be mapped with `score_direction="lower_is_better"`
(higher fraud_score = riskier) and yield AUC ≈ 0.755. Getting 0.245 means the
direction handling is inverted somewhere (deciles, KS ordering, lift, and
inverted-ranking guard must all respect direction too).

### F4. Demo script
EXPERT_PLAYBOOK §4 (two-act demo) replaces SPEC §26's walkthrough in the
README. Keep SPEC §26's endpoint sequence as the mechanical reference only.
