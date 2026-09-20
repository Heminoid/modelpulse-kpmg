"""Data profiler — inspects uploaded DataFrames for types, stats, and warnings."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from app.schemas.dataset import ColumnProfile, DatasetProfile
from app.utils.dataframe import normalize_col_name
from app.utils.formatting import safe_float


# ---------------------------------------------------------------------------
# Type inference (SPEC §9)
# ---------------------------------------------------------------------------

def _infer_type(series: pd.Series, nrows: int) -> str:
    """Infer the logical type of a pandas Series."""
    non_null = series.dropna()
    if len(non_null) == 0:
        return "unknown"

    nunique = non_null.nunique()

    # Boolean: exactly {0, 1}
    if series.dtype in ("int64", "float64"):
        unique_vals = set(non_null.unique())
        if unique_vals <= {0, 1, 0.0, 1.0}:
            return "boolean"

    # ID-like: high-cardinality string
    if series.dtype == "object" and nrows > 0 and nunique / nrows > 0.9:
        return "id"

    # Numeric
    if series.dtype in ("int64", "float64"):
        return "numeric"

    # Categorical: low-cardinality string
    if series.dtype == "object" and nunique <= 50:
        return "categorical"

    # Datetime attempt for high-cardinality strings
    if series.dtype == "object" and nunique > 50:
        sample = non_null.head(100)
        try:
            parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
            success_rate = parsed.notna().sum() / len(sample)
            if success_rate > 0.8:
                return "datetime"
        except Exception:
            pass
        return "unknown"

    return "unknown"


# ---------------------------------------------------------------------------
# Column profiling
# ---------------------------------------------------------------------------

def _profile_column(name: str, series: pd.Series, nrows: int) -> ColumnProfile:
    """Build a ColumnProfile for a single column."""
    null_count = int(series.isna().sum())
    null_pct = null_count / nrows if nrows > 0 else 0.0
    non_null = series.dropna()
    nunique = int(non_null.nunique())
    inferred = _infer_type(series, nrows)

    # Sample values (up to 5 distinct)
    sample_vals: list[Any] = []
    try:
        sample_vals = [_sanitize(v) for v in non_null.unique()[:5]]
    except Exception:
        pass

    profile = ColumnProfile(
        name=name,
        original_name=name,
        inferred_type=inferred,
        null_count=null_count,
        null_percent=round(null_pct * 100, 2),
        unique_count=nunique,
        sample_values=sample_vals,
    )

    # Numeric stats
    if inferred in ("numeric", "boolean"):
        profile.min_val = safe_float(non_null.min())
        profile.max_val = safe_float(non_null.max())
        profile.mean_val = safe_float(non_null.mean())
        profile.std_val = safe_float(non_null.std())
        profile.median_val = safe_float(non_null.median())

    # Categorical stats
    if inferred == "categorical":
        vc = non_null.value_counts().head(10)
        profile.top_categories = [
            {
                "value": str(val),
                "count": int(cnt),
                "pct": round(cnt / nrows * 100, 1),
            }
            for val, cnt in vc.items()
        ]

    # Datetime parse check
    if inferred == "datetime":
        try:
            parsed = pd.to_datetime(non_null, errors="coerce", format="mixed")
            success = parsed.notna().sum()
            profile.parse_success = bool(success == len(non_null))
            if not profile.parse_success:
                profile.parse_warning = (
                    f"Only {success}/{len(non_null)} values parsed as datetime"
                )
        except Exception as e:
            profile.parse_success = False
            profile.parse_warning = str(e)

    # ID-like flag
    if inferred == "id":
        profile.is_likely_id = True

    # MRM Protected Class Detection
    _PROTECTED_CLASS_PATTERNS = {"gender", "race", "age", "zip", "ethnicity", "sex", "marital", "religion", "national_origin"}
    n = name.lower()
    if any(pat in n for pat in _PROTECTED_CLASS_PATTERNS):
        profile.flags.append("protected_class_risk")

    return profile


def _sanitize(val: Any) -> Any:
    """Make a value JSON-safe."""
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        v = float(val)
        if np.isnan(v) or np.isinf(v):
            return None
        return v
    if isinstance(val, (np.bool_, bool)):
        return bool(val)
    return val


# ---------------------------------------------------------------------------
# Monitoring readiness warnings (SPEC §9 + Amendment E3)
# ---------------------------------------------------------------------------

_EVENT_TIME_PATTERNS = {"date", "time", "dt", "timestamp", "created", "applied", "originated"}
_TARGET_PATTERNS = {"default", "bad", "fraud", "target", "label", "outcome", "flag"}
_SCORE_PATTERNS = {"score", "modelscore", "decisionscore"}
_RISK_PATTERNS = {"riskrating", "riskband", "riskgrade"}
_ID_PATTERNS = {"id", "key", "uuid", "applicationid", "customerid", "loanid"}


def _generate_warnings(
    df: pd.DataFrame, columns: list[ColumnProfile]
) -> list[str]:
    """Generate monitoring-readiness warnings from profiled columns."""
    warnings: list[str] = []
    nrows = len(df)

    col_map = {c.name: c for c in columns}

    # Check each column for domain-specific issues
    found_target = False
    found_prob = False
    found_time = False
    found_decision = False
    found_score = False

    for col in columns:
        norm = normalize_col_name(col.name)

        # Event-time detection
        if any(p in norm for p in _EVENT_TIME_PATTERNS):
            found_time = True
            # Check if parse fails
            if col.inferred_type != "datetime":
                # Try explicit parse
                try:
                    parsed = pd.to_datetime(df[col.name], errors="coerce")
                    if parsed.notna().sum() == 0:
                        warnings.append("application_time_malformed")
                except Exception:
                    warnings.append("application_time_malformed")

        # Target detection
        if any(p in norm for p in _TARGET_PATTERNS):
            if col.inferred_type in ("boolean", "numeric", "categorical"):
                found_target = True
                # Low bad count
                non_null = df[col.name].dropna()
                if col.inferred_type in ("boolean", "numeric"):
                    positives = (non_null == 1).sum()
                    if 0 < positives < 30:
                        warnings.append("low_bad_count")

        # Probability detection
        if any(p in norm for p in {"prob", "probability", "pd", "likelihood"}):
            found_prob = True

        # Score detection
        if any(p in norm for p in _SCORE_PATTERNS):
            found_score = True
            # Score null high
            if col.null_count > 0 and nrows > 0:
                if col.null_count / nrows > 0.05:
                    warnings.append("score_null_high")

        # Decision detection
        if any(p in norm for p in {"status", "decision", "approve", "decline"}):
            found_decision = True

        # Risk rating truncation check
        if any(p in norm for p in _RISK_PATTERNS):
            if col.inferred_type == "categorical" and col.top_categories:
                values = {cat["value"] for cat in col.top_categories}
                if "VERY_HIG" in values:
                    warnings.append("risk_rating_truncated")

        # Record ID uniqueness check (Amendment E3)
        if any(p in norm for p in _ID_PATTERNS):
            if col.unique_count > 0 and nrows > 0:
                ratio = col.unique_count / nrows
                if ratio < 0.9:
                    warnings.append("record_id_not_unique")

    # Missing-role warnings
    if not found_target:
        warnings.append("target_missing")
    if not found_prob:
        warnings.append("no_probability_column")
    if not found_time:
        warnings.append("no_event_time")
    if not found_decision:
        warnings.append("decision_missing")
    if not found_score:
        warnings.append("no_score_column")

    return list(dict.fromkeys(warnings))  # deduplicate preserving order


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def profile_dataset(
    df: pd.DataFrame, dataset_id: str, file_size_bytes: int
) -> DatasetProfile:
    """Profile a DataFrame and return a DatasetProfile with warnings."""
    logger.info("Profiling dataset {} ({} rows, {} cols)", dataset_id, len(df), len(df.columns))

    nrows = len(df)
    ncols = len(df.columns)
    dup_count = int(df.duplicated().sum())

    # Column profiles
    col_profiles = [_profile_column(col, df[col], nrows) for col in df.columns]

    # Null summary
    null_summary = {col: int(df[col].isna().sum()) for col in df.columns}

    # Monitoring readiness warnings
    readiness = _generate_warnings(df, col_profiles)

    # Preview rows (first 10)
    preview = df.head(10).replace({np.nan: None}).to_dict(orient="records")
    # Sanitize numpy types in preview
    clean_preview = []
    for row in preview:
        clean_preview.append({k: _sanitize(v) for k, v in row.items()})

    profile = DatasetProfile(
        dataset_id=dataset_id,
        row_count=nrows,
        column_count=ncols,
        file_size_bytes=file_size_bytes,
        duplicate_row_count=dup_count,
        columns=col_profiles,
        null_summary=null_summary,
        monitoring_readiness=readiness,
        preview_rows=clean_preview,
    )

    logger.info(
        "Profile complete for {}: {} warnings", dataset_id, len(readiness)
    )
    return profile
