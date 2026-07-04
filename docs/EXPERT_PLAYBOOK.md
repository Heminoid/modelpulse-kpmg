# EXPERT PLAYBOOK — model monitoring design, test matrix, and demo strategy

Written from the perspective of a model risk / MRM consulting practice. This is
the layer that turns the SPEC from "computes metrics" into "behaves like a
platform a bank's model validation team would trust." Claude Code: read this
before Phase 4 and again before Phase 8.

---

## 1. Platform philosophy

A monitoring platform has exactly three jobs, in order:
**detect → explain → recommend.** Every run output must survive three questions
a Head of Model Risk will ask: *What changed? Why does it matter? What should
we do?* Deterministic findings answer all three (finding → evidence →
possible_causes → recommended_actions). A dashboard of numbers without that
chain is a reporting tool, not a monitoring platform.

Two corollaries baked into the test strategy:
- **Never crash on client data.** Real bank extracts are dirty: truncated
  categories, constant timestamp columns, duplicate ingestion, unit changes.
  Every anomaly is a *finding*, not an exception. (`edge_cases.csv` and the
  original `underwriting_scorecard_clean.csv` enforce this.)
- **Never cry wolf.** A platform that flags a healthy model gets ignored
  within a month, and then misses the real event. The stable-current run is a
  hard no-false-positive gate, as important as the drifted run's alerts.

## 2. Detection taxonomy — the full checklist (what a Big 4 review covers)

Pillars 1–9 map to SPEC modules; ★ items are EXPERT ADDITIONS specified in
SPEC_AMENDMENTS §F — cheap to implement, disproportionately valuable, and each
one is actually triggered by at least one shipped dataset.

1. **Data integrity** — nulls, duplicates, invalid probabilities/targets,
   malformed timestamps, ★ duplicate record IDs, ★ constant columns,
   ★ band–score consistency (does `score_band` actually equal
   `band(model_score)`? the client demo file disagrees on 13% of rows),
   ★ score–PD coherence (Spearman ρ between `model_score` and
   `probability_of_default`; with higher_is_better expect strongly negative;
   |ρ| < 0.3 ⇒ critical "score and PD disagree — one of them is wrong").
2. **Population stability** — PSI on score & PD, CSI per feature, categorical
   PSI on segments, segment share drift.
3. **Discrimination** — AUC/Gini/KS, decile table + lift, monotonicity of bad
   rate across bands, ★ inverted-ranking guard (AUC < 0.5 ⇒ critical "rank
   ordering inverted vs configured direction — model broken or direction
   misconfigured"), ★ leakage suspicion (AUC > 0.97 ⇒ warning "suspiciously
   perfect — check target leakage / post-outcome features").
4. **Calibration** — Brier + skill, observed-vs-predicted by bin, overall
   ratio, Hosmer–Lemeshow, direction of miss (under-prediction is the
   dangerous one — provisions understated).
5. **Strategy / policy** — approval & decline rates vs baseline, bad rate on
   approved, ★ decision–score separation (approved vs declined score gap +
   Mann-Whitney; near-zero gap ⇒ "decisions are not score-driven" — true of
   the client demo file: 643.1 vs 644.8), override analysis with cutoff
   sensitivity.
6. **Portfolio quality** — DPD buckets, severe rate, roll-rate matrix,
   concentration (segment shares).
7. **Fairness** — DI ratio per proxy group vs 4/5ths rule, low-power flags,
   explicit proxy disclaimers.
8. **Statistical rigor** — significance tests with small-sample fallbacks and
   BH-FDR correction; every metric that fires on <30 bads carries a power
   warning.
9. **Governance** — model registry, champion/challenger, run audit trail,
   SR 11-7 / IFRS 9 report packs, thresholds stored per monitor (overridable,
   defaults from config).

## 3. Test-data matrix (the acceptance grid)

| Dataset | Role | Must produce | Must NOT produce |
|---|---|---|---|
| `underwriting_scorecard_clean.csv` | client-style dirty snapshot, broken model | inverted-ranking critical, score–PD coherence critical (ρ≈−0.03), monotonicity FAIL, calib critical (0.594), severe-DPD critical, dup-ID + truncation + malformed-time findings, low-bad-count | a crash; a healthy health score |
| `healthy_baseline.csv` | positive control (standalone run) | health score "healthy", monotonic PASS, calib ratio 1.00, time-series AVAILABLE | any warning/critical alert (info findings OK) |
| `healthy_current_stable.csv` vs baseline | false-positive gate | all PSI < 0.10, no performance/strategy alerts | ANY drift/decline alert (= smoke failure) |
| `healthy_current_drifted.csv` vs baseline | true-positive gate | the exact alert set pinned in `expected_values_synthetic.py` (critical PSI, warning AUC decline, warning-high calibration, critical approval shift, critical bad-on-approved, critical severe-DPD, strategy-deterioration finding) | silence |
| `fraud_sample.csv` | schema-agnostic + direction control | generic-heuristic mapping, `lower_is_better` AUC = 0.755, low-bad-count warning, 3-value decision validator warning | AUC 0.245 (direction bug), any hardcoded-column error |
| `edge_cases.csv` | data-quality gauntlet | run COMPLETES; null/dup/invalid-prob/malformed-time/score-null-high/constant-column findings | 500s, crashes, PSI exceptions on constant column |

Passing all six is the Phase 8 definition of done. This grid is worth more
than any amount of code review.

## 4. The two-act demo (10 minutes, replaces SPEC §26's script)

**Act 1 — "It knows healthy" (3 min).** Upload `healthy_baseline.csv`, map
(one-click accept — all high confidence), run standalone: green dashboard,
health "healthy", calibration on the line, monotonic lift chart, time-series
available. Then run `healthy_current_stable.csv` against baseline: still green
— *"and it doesn't nag you when nothing is wrong."*

**Act 2 — "It catches deterioration and dirty data" (7 min).** Run
`healthy_current_drifted.csv` against the same baseline: PSI chart lights up
red at the 0.25 line, calibration plot bends under the diagonal
(under-prediction — provisioning risk), approval −20pp with bad-rate-on-booked
tripling, strategy-deterioration finding with recommended actions, health
"critical". Generate the SR 11-7 PDF live. Close with the client-style file
`underwriting_scorecard_clean.csv`: *"and when the data itself is the problem —
duplicate IDs, truncated categories, a score that contradicts its own PD —
it tells you that too, instead of producing confident nonsense."* That last
beat lands hardest with risk audiences.

## 5. Threshold governance note

Defaults in config are industry folklore (PSI 0.10/0.25 etc.), fine for POC.
Say so in the README: production thresholds should be calibrated per portfolio
via backtesting, and every override is stored on the monitor config
(auditable). Alerts must always echo the threshold they compared against —
"observed vs limit" phrasing, never bare judgments.

## 6. Post-POC roadmap (name these when asked "what's next", do NOT build)

Scheduled runs + webhook/email alerting; multi-model portfolio heat-map
(EWI aggregation); reject inference for through-the-door vs booked bias;
true two-snapshot roll rates & vintage curves (data model already supports it
the moment valid timestamps arrive — demonstrated by healthy_baseline);
retraining triggers wired to health score; IFRS 9 staging/ECL sensitivity
hooks; SS1/23 (UK) mapping alongside SR 11-7; approval workflow & sign-off on
runs; DB swap behind the existing store interfaces.
