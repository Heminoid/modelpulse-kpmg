"""
GROUND TRUTH for data/underwriting_scorecard_clean.csv — computed directly
from the file (pandas 2.x, scikit-learn roc_auc_score, scipy ks_2samp).
scripts/smoke_test.py imports these and asserts against API responses.
Tolerance: abs diff <= 1e-3 for floats unless noted.

NOTE: several values CONTRADICT the demo numbers claimed in docs/SPEC.md
Section 26 / Module 15. This file wins. See SPEC_AMENDMENTS.md Section E.
"""

ROW_COUNT = 197
COLUMN_COUNT = 22
TOTAL_NULLS = 0
DUPLICATE_FULL_ROWS = 0

# --- IDs: application_id is NOT unique (20 values, each ~10 rows) ---
UNIQUE_APPLICATION_IDS = 20            # APP00000 .. APP00019
ID_UNIQUENESS_RATIO = 0.1015           # value-pattern ID heuristic will NOT fire
APPLICATION_TIME_UNIQUE_VALUES = 1     # constant "46:27.6" -> time-series impossible

# --- Target / decision ---
N_DEFAULTS = 11
BAD_RATE = 0.055838
N_APPROVED = 152
N_DECLINED = 45
APPROVAL_RATE = 0.771574
BAD_RATE_ON_APPROVED = 0.052632        # 8 / 152

# --- Score / PD ranges ---
MODEL_SCORE_MIN, MODEL_SCORE_MAX = 448, 850
PD_MIN, PD_MAX = 0.001872, 0.287841
AVG_PREDICTED_PD = 0.094079

# --- Performance (score_direction = "higher_is_better" per mapping) ---
# The model's rank-ordering is BROKEN in this data (synthetic noise):
AUC_MODEL_SCORE = 0.334066   # < 0.5 => worse than random in the mapped direction
GINI_MODEL_SCORE = -0.331867
AUC_PD = 0.579179            # using probability_of_default as risk score
KS_MODEL_SCORE = 0.356305
KS_PD = 0.245357
SCORE_TARGET_CORR = +0.1238  # higher score correlates with MORE defaults

# --- Calibration (model over-predicts risk ~40%) ---
BRIER = 0.055933
BRIER_NULL = 0.052720
BRIER_SKILL = -0.060942      # negative: worse than predicting the base rate
CALIBRATION_RATIO = 0.593518 # < 0.60 => "critical" band per spec Section 13D

# --- Bad rate / approval by score_band (ANTI-monotonic: monotonicity FAILS) ---
SCORE_BAND_STATS = {         # band: (n, bads, bad_rate, approval_rate)
    "<600":    (69, 1, 0.0145, 0.8116),
    "600-700": (68, 5, 0.0735, 0.7206),
    "700-800": (47, 4, 0.0851, 0.7872),
    "800+":    (13, 1, 0.0769, 0.7692),
}
MONOTONICITY_EXPECTED = "FAIL"
# score_band matches band(model_score) for only 86.8% of rows (bands are noisy)
SCORE_BAND_CONSISTENCY = 0.868

# --- Risk rating (also inverted: LOW has the highest bad rate) ---
RISK_RATING_STATS = {        # rating: (n, bads, bad_rate, approval_rate)
    "LOW":      (85, 7, 0.0824, 0.8118),
    "MEDIUM":   (57, 3, 0.0526, 0.7544),
    "HIGH":     (41, 1, 0.0244, 0.6829),
    "VERY_HIG": (14, 0, 0.0000, 0.8571),
}

# --- Delinquency (both severe and 30+ breach CRITICAL thresholds) ---
DPD_BUCKETS = {"Current": 100, "1-29 DPD": 0, "30-59 DPD": 24,
               "60-89 DPD": 26, "90+ DPD": 47}   # the lone 50-DPD row -> 30-59
SEVERE_DPD_RATE = 0.238579   # > 0.20 critical threshold -> alert must fire
DPD_30PLUS_RATE = 0.492386   # > 0.25 critical threshold -> alert must fire

# --- Override analysis (cutoff: model_score < 600) ---
OVERRIDE_MODEL_DECLINES = 73          # rows with model_score < 600
OVERRIDE_APPROVED = 60                # of those, business approved
OVERRIDE_RATE = 0.8219
OVERRIDE_BAD_RATE = 0.0333            # 2/60
NORMAL_APPROVED_BAD_RATE = 0.0652     # score>=600 & approved: 6/92
OVERRIDE_PERFORMING_BETTER = True

# --- Fairness DI vs overall approval (spec's claims verified EXACTLY) ---
DI_BORDERLINE = {                     # 0.80 <= DI < 0.90
    ("loan_purpose", "credit_car"): 0.8308,
    ("income_band", "75-100K"):     0.8439,
}
DI_HOME_OWNERSHIP_OTHER = 0.9258      # n=14 -> low_power_warning expected

# --- Strategy misc ---
AVG_SCORE_APPROVED = 643.138          # nearly identical to declined (644.844)
AVG_SCORE_DECLINED = 644.844          # => Mann-Whitney should NOT be significant
AVG_LOAN_APPROVED = 29760.81
AVG_LOAN_DECLINED = 25409.78
