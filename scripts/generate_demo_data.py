"""
generate_demo_data.py — reproducible synthetic test-data suite for ModelPulse.

Produces (all under data/):
  healthy_baseline.csv        5,000 rows — well-behaved scorecard (positive control)
  healthy_current_stable.csv  2,500 rows — same population, healthy model (green run)
  healthy_current_drifted.csv 2,500 rows — shifted population + degraded model +
                                           unseen macro shock (red run: PSI, AUC
                                           decline, calibration, approval alerts)
  fraud_sample.csv              800 rows — different schema; fraud_score direction
                                           is lower_is_better (higher = riskier)
  edge_cases.csv                420 rows — nulls, invalid probabilities, duplicate
                                           rows, constant column, malformed dates

Production realism: the score scaling (MU/SIG) and PD calibration intercept are
FITTED ON BASELINE ONLY and applied unchanged to the current datasets — exactly
like a deployed scorecard. The drifted set's extra default risk (unseen_shock)
is invisible to the model, which is what genuinely breaks calibration.

Deterministic (fixed seeds). The shipped CSVs are the source of truth for
scripts/expected_values_synthetic.py — regenerate only to re-pin those numbers.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)


def _sig(z):
    return 1.0 / (1.0 + np.exp(-z))


def _raw(n, seed, shift, noise, unseen_shock):
    """Features + true defaults + the model's latent view (z_model)."""
    rng = np.random.default_rng(seed)
    cs = np.clip(rng.normal(690 - 35 * shift, 55, n), 440, 850).round().astype(int)
    inc = np.clip(rng.lognormal(11.05 - 0.18 * shift, 0.45, n), 18_000, 400_000).round().astype(int)
    dti = np.clip(rng.normal(24 + 7 * shift, 9, n), 1, 60).round(2)
    emp = np.clip(rng.exponential(6, n), 0, 40).round().astype(int)
    amt = np.clip(rng.lognormal(9.9 + 0.10 * shift, 0.6, n), 1_000, 90_000).round().astype(int)
    rev = np.clip(rng.normal(45 + 12 * shift, 22, n), 0, 100).round(2)
    inq = rng.poisson(1.2 + 0.6 * shift, n)
    dq = rng.poisson(0.6 + 0.3 * shift, n)
    dq_m = np.where(dq > 0, rng.poisson(4, n), 0)
    dq_since = np.where(dq > 0, rng.integers(1, 60, n), 0)
    purpose_p = [0.28, 0.22, 0.18, 0.18, 0.14] if shift <= 0.3 else [0.40, 0.24, 0.12, 0.12, 0.12]
    purpose = rng.choice(["debt_consolidation", "credit_card", "home_improvement",
                          "major_purchase", "other"], n, p=purpose_p)
    home = rng.choice(["RENT", "MORTGAGE", "OWN", "OTHER"], n, p=[0.42, 0.40, 0.12, 0.06])

    z_seen = (-3.55 - 0.021 * (cs - 690) + 0.058 * (dti - 24) + 0.016 * (rev - 45)
              + 0.24 * inq + 0.48 * dq - 0.42 * np.log(inc / 60_000))
    default = rng.binomial(1, np.clip(_sig(z_seen + unseen_shock), 0, 0.98))
    z_model = z_seen + rng.normal(0, noise, n)
    feats = dict(credit_score=cs, annual_income=inc, debt_to_income=dti,
                 employment_length=emp, loan_amount=amt, loan_purpose=purpose,
                 home_ownership=home, number_of_delinquent_accounts=dq,
                 delinquent_months=dq_m, months_since_last_delinquent=dq_since,
                 revolving_utilization=rev, inquiries_last_6m=inq)
    return feats, z_model, default, rng


def _assemble(feats, z_model, default, rng, *, mu, sig, pd_adj, cutoff,
              id_prefix, start, months, score_seed):
    n = len(default)
    r2 = np.random.default_rng(score_seed)
    model_score = np.clip(660 - 58 * (z_model - mu) / sig + r2.normal(0, 10, n),
                          350, 850).round().astype(int)
    pod = np.clip(_sig(z_model + pd_adj), 1e-4, 0.999).round(6)
    approved = r2.random(n) < _sig((model_score - cutoff) / 35.0)
    status = np.where(approved, "APPROVED", "DECLINED")

    dpd = np.zeros(n, dtype=int)
    bad = default == 1
    dpd[bad] = rng.choice([60, 90, 120, 150], bad.sum(), p=[0.25, 0.35, 0.25, 0.15])
    slip = (~bad) & (rng.random(n) < 0.06)
    dpd[slip] = rng.choice([30, 60], slip.sum(), p=[0.75, 0.25])

    s_band = np.select([model_score < 600, model_score < 700, model_score < 800],
                       ["<600", "600-700", "700-800"], default="800+")
    q = np.quantile(pod, [0.25, 0.5, 0.85])
    risk = np.select([pod <= q[0], pod <= q[1], pod <= q[2]],
                     ["LOW", "MEDIUM", "HIGH"], default="VERY_HIGH")
    inc = feats["annual_income"]
    i_band = np.select([inc < 50_000, inc < 75_000, inc < 100_000],
                       ["<50K", "50-75K", "75-100K"], default="100K+")
    t0 = pd.Timestamp(start)
    ts = (t0 + pd.to_timedelta(rng.integers(0, months * 30, n), unit="D")
          + pd.to_timedelta(rng.integers(0, 86_400, n), unit="s"))
    return pd.DataFrame({
        "application_id": [f"{id_prefix}{i:06d}" for i in range(n)],
        "application_time": pd.Series(ts).dt.strftime("%Y-%m-%d %H:%M:%S"),
        **feats,
        "model_score": model_score, "probability_of_default": pod,
        "risk_rating": risk, "application_status": status,
        "actual_default": default, "past_due_days": dpd,
        "score_band": s_band, "income_band": i_band,
    })


def gen_fraud(n: int = 800, seed: int = 7) -> pd.DataFrame:
    """Different schema + OPPOSITE score direction (higher fraud_score = riskier)."""
    rng = np.random.default_rng(seed)
    amount = np.clip(rng.lognormal(4.2, 1.1, n), 1, 20_000).round(2)
    cat = rng.choice(["electronics", "travel", "grocery", "fashion", "gaming", "crypto"],
                     n, p=[0.20, 0.15, 0.25, 0.18, 0.12, 0.10])
    risky = np.isin(cat, ["crypto", "gaming"]).astype(float)
    z = -3.8 + 0.00025 * amount + 1.3 * risky + rng.normal(0, 0.7, n)
    is_fraud = rng.binomial(1, _sig(z))
    zm = z + rng.normal(0, 0.8, n)
    prob = np.clip(_sig(zm), 1e-4, 0.999).round(6)
    fscore = np.clip(500 + 130 * (zm - zm.mean()) / zm.std(), 0, 1000).round().astype(int)
    flag = np.where(fscore > 720, "BLOCKED", "APPROVED")
    flag = np.where(rng.random(n) < 0.02, "REVIEW", flag)   # 3rd value: validator warn path
    dates = pd.Series(pd.Timestamp("2025-01-01")
                      + pd.to_timedelta(rng.integers(0, 180, n), unit="D")).dt.strftime("%Y-%m-%d")
    return pd.DataFrame({"txn_id": [f"TXN{i:07d}" for i in range(n)],
                         "txn_date": dates, "txn_amount": amount,
                         "merchant_category": cat, "fraud_score": fscore,
                         "fraud_probability": prob, "decision_flag": flag,
                         "is_fraud": is_fraud})


def gen_edge_cases(base_df: pd.DataFrame, seed: int = 99) -> pd.DataFrame:
    """Corrupt a healthy sample to exercise every data-quality path."""
    rng = np.random.default_rng(seed)
    df = base_df.copy().reset_index(drop=True)
    df["application_id"] = [f"EC{i:06d}" for i in range(len(df))]
    for c in ["annual_income", "employment_length", "model_score"]:
        df[c] = df[c].astype(float)
    df.loc[rng.choice(400, 40, replace=False), "annual_income"] = np.nan       # 10% nulls
    df.loc[rng.choice(400, 70, replace=False), "employment_length"] = np.nan   # 17.5% nulls
    df.loc[rng.choice(400, 30, replace=False), "model_score"] = np.nan         # 7.5% -> score_null_high
    bad_idx = rng.choice(400, 5, replace=False)
    df.loc[bad_idx[:3], "probability_of_default"] = [1.2, 1.05, 1.5]           # invalid > 1
    df.loc[bad_idx[3:], "probability_of_default"] = [-0.1, -0.02]              # invalid < 0
    df.loc[rng.choice(400, 120, replace=False), "application_time"] = "46:27.6"  # 30% malformed
    df["channel"] = "ONLINE"                                                    # constant column
    df["notes"] = [f"case-{rng.integers(1_000_000):06d}-{rng.integers(1_000_000):06d}"
                   for _ in range(400)]                                         # id-like free text
    return pd.concat([df, df.iloc[:20]], ignore_index=True)                     # 20 duplicate rows


if __name__ == "__main__":
    # 1) Baseline — fit MU/SIG and PD intercept here (the "deployed model")
    f_b, z_b, d_b, r_b = _raw(5000, 11, shift=0.0, noise=0.55, unseen_shock=0.0)
    MU, SIG = float(z_b.mean()), float(z_b.std())
    lo, hi = -3.0, 3.0
    for _ in range(40):
        adj = (lo + hi) / 2
        if _sig(z_b + adj).mean() > d_b.mean():
            hi = adj
        else:
            lo = adj
    PD_ADJ = adj

    baseline = _assemble(f_b, z_b, d_b, r_b, mu=MU, sig=SIG, pd_adj=PD_ADJ,
                         cutoff=590, id_prefix="BL", start="2024-01-01",
                         months=12, score_seed=101)

    # 2) Stable current — same population, same model quality, same policy
    f_s, z_s, d_s, r_s = _raw(2500, 12, shift=0.05, noise=0.55, unseen_shock=0.0)
    stable = _assemble(f_s, z_s, d_s, r_s, mu=MU, sig=SIG, pd_adj=PD_ADJ,
                       cutoff=590, id_prefix="CS", start="2025-01-01",
                       months=6, score_seed=102)

    # 3) Drifted current — shifted population, noisier model, unseen macro
    #    shock (breaks calibration), tightened cutoff (policy change)
    f_d, z_d, d_d, r_d = _raw(2500, 13, shift=0.55, noise=1.15, unseen_shock=0.70)
    drifted = _assemble(f_d, z_d, d_d, r_d, mu=MU, sig=SIG, pd_adj=PD_ADJ,
                        cutoff=600, id_prefix="CD", start="2025-01-01",
                        months=6, score_seed=103)

    baseline.to_csv(OUT / "healthy_baseline.csv", index=False)
    stable.to_csv(OUT / "healthy_current_stable.csv", index=False)
    drifted.to_csv(OUT / "healthy_current_drifted.csv", index=False)
    gen_fraud().to_csv(OUT / "fraud_sample.csv", index=False)
    edge_base = _assemble(*_raw(400, 99, shift=0.0, noise=0.55, unseen_shock=0.0),
                          mu=MU, sig=SIG, pd_adj=PD_ADJ, cutoff=590,
                          id_prefix="EC", start="2025-01-01", months=6, score_seed=104)
    gen_edge_cases(edge_base).to_csv(OUT / "edge_cases.csv", index=False)
    print("written:", sorted(p.name for p in OUT.glob("*.csv")))
