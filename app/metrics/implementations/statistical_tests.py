"""Statistical Testing Suite."""

import pandas as pd
import numpy as np
from pydantic import BaseModel, ConfigDict
from typing import Optional
from scipy.stats import chisquare, binomtest, fisher_exact, mannwhitneyu

class StatTestResult(BaseModel):
    test_name: str
    test_key: str
    statistic: float
    p_value: float
    degrees_of_freedom: Optional[int] = None
    conclusion: str
    pass_fail: str
    alpha: float = 0.05
    small_sample_warning: bool = False
    notes: Optional[str] = None

class StatTestsPayload(BaseModel):
    tests: list[StatTestResult]
    correction_method: str
    n_significant: int

def run_statistical_tests(df: pd.DataFrame, mapping, baseline_stats: dict | None) -> StatTestsPayload:
    tests = []
    mapped_roles = {}
    for col, role in mapping.mappings.items():
        mapped_roles.setdefault(role, []).append(col)
        
    target_col = mapped_roles.get("target", [None])[0]
    pd_col = mapped_roles.get("prediction_probability", [None])[0]
    score_col = mapped_roles.get("prediction_score", [None])[0]
    decision_col = mapped_roles.get("decision", [None])[0]
    band_col = mapped_roles.get("score_band", [None])[0]
    
    # Test 1: Hosmer-Lemeshow (requires target and prediction_probability)
    if target_col and pd_col and target_col in df.columns and pd_col in df.columns:
        clean_df = df[[target_col, pd_col]].dropna()
        if len(clean_df) > 0:
            y_true = clean_df[target_col]
            y_prob = clean_df[pd_col]
            # adaptive bins: 5 if n < 200 else 10
            n_groups = 5 if len(clean_df) < 200 else 10
            
            # Amendment C1 logic
            df_hl = pd.DataFrame({"y": y_true, "p": y_prob})
            df_hl["decile"] = pd.qcut(df_hl["p"].rank(method="first"), q=n_groups, labels=False)
            grouped = df_hl.groupby("decile").agg(n=("y","count"), obs=("y","sum"), exp=("p","sum"))
            
            # Drop groups where pi_bar is 0 or 1
            pi_bar = grouped["exp"] / grouped["n"]
            valid = (pi_bar > 0) & (pi_bar < 1)
            grouped = grouped[valid]
            pi_bar = pi_bar[valid]
            
            if len(grouped) >= 3:
                hl_stat = (((grouped["obs"] - grouped["exp"]) ** 2) / (grouped["n"] * pi_bar * (1 - pi_bar))).sum()
                df_free = len(grouped) - 2
                from scipy import stats
                p_value = stats.chi2.sf(hl_stat, df=df_free)
                
                tests.append(StatTestResult(
                    test_name="Hosmer-Lemeshow Test",
                    test_key="hosmer_lemeshow",
                    statistic=float(hl_stat),
                    p_value=float(p_value),
                    degrees_of_freedom=df_free,
                    conclusion="Fail to reject H₀ — distributions are similar" if p_value > 0.05 else "Reject H₀ — distributions differ",
                    pass_fail="pass" if p_value > 0.05 else "fail",
                    small_sample_warning=len(clean_df) < 30
                ))

    # Test 2: Chi-square categorical drift (requires baseline)
    if baseline_stats and "categorical_distributions" in baseline_stats:
        for col, b_dist in baseline_stats["categorical_distributions"].items():
            if col in df.columns:
                current_counts = df[col].value_counts()
                baseline_freqs = {k: v / sum(b_dist.values()) for k, v in b_dist.items()}
                
                cats = sorted(set(baseline_freqs.keys()) | set(current_counts.index))
                f_obs = np.array([current_counts.get(c, 0) for c in cats], dtype=float)
                f_exp = np.array([baseline_freqs.get(c, 0.0) for c in cats]) * f_obs.sum()
                f_exp = np.clip(f_exp, 1e-6, None)  # avoid zero expected
                
                if len(f_obs) > 1 and f_obs.sum() > 0:
                    stat, p = chisquare(f_obs, f_exp)
                    tests.append(StatTestResult(
                        test_name=f"Chi-square Drift: {col}",
                        test_key=f"chi2_{col}",
                        statistic=float(stat),
                        p_value=float(p),
                        degrees_of_freedom=len(f_obs) - 1,
                        conclusion="Fail to reject H₀ — distributions are similar" if p > 0.05 else "Reject H₀ — distributions differ",
                        pass_fail="pass" if p > 0.05 else "fail",
                        small_sample_warning=(f_exp < 5).any()
                    ))

    # Test 3: Binomial and Test 4: Fisher exact
    if target_col and target_col in df.columns:
        overall_bad_rate = df[target_col].mean()
        group_col = band_col if band_col and band_col in df.columns else score_col
        if group_col and group_col in df.columns:
            if group_col == score_col:
                # Bin into 5 groups
                bands = pd.qcut(df[score_col].rank(method="first"), 5, labels=False)
            else:
                bands = df[group_col]
                
            for band in bands.dropna().unique():
                sub = df[bands == band]
                k = int(sub[target_col].sum())
                n = len(sub)
                if n > 0:
                    if n >= 30:
                        # Binomial
                        res = binomtest(k=k, n=n, p=float(overall_bad_rate), alternative="greater")
                        tests.append(StatTestResult(
                            test_name=f"Binomial Test: Band {band}",
                            test_key=f"binom_band_{band}",
                            statistic=float(k),
                            p_value=float(res.pvalue),
                            conclusion="Fail to reject H₀ — distributions are similar" if res.pvalue > 0.05 else "Reject H₀ — distributions differ",
                            pass_fail="pass" if res.pvalue > 0.05 else "fail",
                            small_sample_warning=False
                        ))
                    else:
                        # Fisher exact
                        bads_overall = df[target_col].sum()
                        goods_overall = len(df) - bads_overall
                        goods_in_band = n - k
                        oddsratio, p_val = fisher_exact([[k, goods_in_band], [bads_overall, goods_overall]], alternative="greater")
                        tests.append(StatTestResult(
                            test_name=f"Fisher Exact Test: Band {band}",
                            test_key=f"fisher_band_{band}",
                            statistic=float(oddsratio),
                            p_value=float(p_val),
                            conclusion="Fail to reject H₀ — distributions are similar" if p_val > 0.05 else "Reject H₀ — distributions differ",
                            pass_fail="pass" if p_val > 0.05 else "fail",
                            small_sample_warning=True
                        ))

    # Test 5: Mann-Whitney U
    if decision_col and score_col and decision_col in df.columns and score_col in df.columns:
        positive_label = mapping.mappings.get(decision_col + "_positive_label", "APPROVED")
        # Handle string "APPROVED" or boolean/int
        if df[decision_col].dtype == object:
            approved_scores = df.loc[df[decision_col].astype(str).str.upper() == positive_label.upper(), score_col]
            declined_scores = df.loc[df[decision_col].astype(str).str.upper() != positive_label.upper(), score_col]
        else:
            approved_scores = df.loc[df[decision_col] == 1, score_col]
            declined_scores = df.loc[df[decision_col] == 0, score_col]
            
        if len(approved_scores) > 0 and len(declined_scores) > 0:
            approved_scores = approved_scores.dropna()
            declined_scores = declined_scores.dropna()
            # alternative="greater" if higher_is_better. Wait.
            # If higher_is_better, approved scores should be stochastically GREATER than declined scores.
            # If lower_is_better, approved scores should be stochastically LESS than declined scores.
            alt = "greater" if mapping.score_direction == "higher_is_better" else "less"
            stat, p = mannwhitneyu(approved_scores, declined_scores, alternative=alt)
            tests.append(StatTestResult(
                test_name="Mann-Whitney U: Approved vs Declined Scores",
                test_key="mann_whitney_scores",
                statistic=float(stat),
                p_value=float(p),
                conclusion="Fail to reject H₀ — distributions are similar" if p > 0.05 else "Reject H₀ — distributions differ",
                pass_fail="pass" if p > 0.05 else "fail",
                small_sample_warning=len(approved_scores) < 30 or len(declined_scores) < 30
            ))

    # Multiple testing correction
    correction_method = "none"
    if tests:
        p_values = [t.p_value for t in tests]
        try:
            from scipy.stats import false_discovery_control
            corrected = false_discovery_control(p_values, method="bh")
            correction_method = "bh"
        except ImportError:
            # Fallback to Bonferroni
            corrected = np.clip(np.array(p_values) * len(p_values), 0, 1)
            correction_method = "bonferroni"
            
        for i, t in enumerate(tests):
            t.p_value = float(corrected[i])
            t.pass_fail = "pass" if t.p_value > 0.05 else "fail"
            t.conclusion = "Fail to reject H₀ — distributions are similar" if t.p_value > 0.05 else "Reject H₀ — distributions differ"
            
    n_sig = sum(1 for t in tests if t.pass_fail == "fail")
    
    return StatTestsPayload(
        tests=tests,
        correction_method=correction_method,
        n_significant=n_sig
    )
