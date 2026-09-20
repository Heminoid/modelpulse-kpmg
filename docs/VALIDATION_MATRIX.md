# ModelPulse Validation Matrix & QA Contract

This document serves as the formal Quality Assurance (QA) and regulatory validation contract for the ModelPulse platform. It specifies expected behaviors, ground-truth metrics, and acceptance criteria across all control datasets in accordance with **SR 11-7 / OCC 2011-12** guidance on Model Risk Management (MRM).

---

## 1. Control Dataset Catalog

| Dataset File | Rows | Purpose | Expected Model State | Key Regulatory Signals |
| :--- | :--- | :--- | :--- | :--- |
| `underwriting_scorecard_clean.csv` | 197 | Retail Credit Scorecard (Degraded) | Deteriorating / Critical | Inverted rank-ordering (AUC ~0.334, Gini < 0), severe calibration breach (Ratio ~0.59), single timestamp (time-series disabled). |
| `healthy_baseline.csv` | 3000 | Benchmark Baseline (Positive Control) | Healthy (Score > 90) | Benchmark score distributions, baseline histograms for PSI/CSI, stable default rate (~5%). |
| `healthy_current_stable.csv` | 1500 | Production Monitoring (Stable) | Healthy (Score > 85) | Population Stability Index (PSI < 0.10), Feature CSI (< 0.10), consistent default rate. |
| `healthy_current_drifted.csv` | 1500 | Production Monitoring (Drift Case) | Critical (Score < 50) | Score PSI > 0.25, multiple features with CSI > 0.25, automated drift alerts. |
| `fraud_sample.csv` | 400 | Transaction Fraud (Vocabulary Agnostic) | Custom Direction | `lower_is_better` score direction, `APPROVE`/`DECLINE` decision strings, binary target. |
| `edge_cases.csv` | Varied | Adversarial & Boundary Testing | Error / Skipped Handlers | Constant columns, null percentages > 50%, missing roles, extreme outliers. |

---

## 2. Pinned Ground Truth Metrics (`underwriting_scorecard_clean.csv`)

Ground-truth metrics computed directly from `data/underwriting_scorecard_clean.csv` via deterministic calculations. Test tolerance is $| \Delta | \le 10^{-3}$ unless specified.

| Metric Key | Metric Name | Ground Truth Value | Alert Severity | Expected Platform Behavior |
| :--- | :--- | :--- | :--- | :--- |
| `perf_auc` | ROC Area Under Curve | `0.3341` | Critical | Flags inverted model ranking (AUC < 0.50). |
| `perf_gini` | Gini Coefficient | `-0.3319` | Critical | Negative discrimination capacity detected. |
| `perf_ks` | Kolmogorov-Smirnov | `0.3563` | OK / Watch | Separation between goods and bads. |
| `calib_summary` | Calibration Ratio | `0.5935` | Critical | Severe under-prediction of risk (Ratio < 0.60). |
| `calib_brier_score` | Brier Score | `0.0528` | OK | Probability accuracy baseline. |
| `strategy_approval_rate` | Approval Rate | `0.7716` (77.16%) | OK | Approvals: 152 / 197 rows. |
| `strategy_bad_rate` | Bad Rate (Overall) | `0.0558` (5.58%) | OK | Defaults: 11 / 197 rows. |
| `strategy_bad_rate_approved` | Bad Rate on Approved | `0.0526` (5.26%) | OK | Approved Defaults: 8 / 152 rows. |
| `delinq_severe_rate` | 90+ DPD Rate | `0.0000` | OK | Zero rows with 90+ DPD in clean sample. |
| `delinq_30plus_rate` | 30+ DPD Rate | `0.0000` | OK | Zero rows with 30+ DPD in clean sample. |

---

## 3. Stability & Drift Standards (PSI & CSI)

In accordance with industry standards (Basel II / SR 11-7 validation practices):

| Stability Index Metric | Range | Status | Platform Action |
| :--- | :--- | :--- | :--- |
| **PSI / CSI < 0.10** | Low Drift | Healthy | No action required. Green badge displayed. |
| **0.10 ≤ PSI / CSI < 0.25** | Moderate Drift | Watch / Warning | Warning alert dispatched; recommend monitoring feature cohorts. |
| **PSI / CSI ≥ 0.25** | Significant Drift | Critical | Critical alert dispatched; trigger model recalibration or retrain recommendation. |

---

## 4. Fair Lending & ECOA Compliance Thresholds

Under the Equal Credit Opportunity Act (ECOA) and Consumer Financial Protection Bureau (CFPB) guidelines, disparate impact is evaluated using the **Four-Fifths (80%) Rule**:

$$\text{Disparate Impact Ratio (DI)} = \frac{\text{Approval Rate}_{\text{Protected}}}{\text{Approval Rate}_{\text{Control}}}$$

* **DI Ratio $\ge 0.90$**: Compliant (Healthy).
* **$0.80 \le \text{DI Ratio} < 0.90$**: Borderline Warning.
* **DI Ratio $< 0.80$**: Regulatory Adverse Impact Breach (Critical Alert, mandatory audit note).
* **Sample Size Caveat ($N < 30$)**: Disparate impact flags low statistical power warning when subgroup $N < 30$.

---

## 5. Automated Acceptance Test Gates

All platform builds must pass `scripts/smoke_test.py`:
1. **HTTP Status Code Verification**: All API endpoints return status `200` (or `404`/`400` when given invalid IDs).
2. **Deterministic Value Asserts**: Exact match to ground-truth values in Section 2.
3. **Chart Rendering**: Chart endpoints must return valid image bytes (`\x89PNG` for PNG, XML for SVG).
4. **Report Generation**: PDF, HTML, and Word DOCX must generate without unhandled exceptions.
5. **Deduplication Check**: No duplicate metric keys or duplicate alerts generated per execution.
