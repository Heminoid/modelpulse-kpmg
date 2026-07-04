"""Two-pass column-role heuristic engine.

Pass 1 — Exact vocabulary match against known scorecard column names.
          This is the ONLY place in the codebase with literal column names
          like "modelscore", "actualdefault", etc. (CLAUDE.md Rule 1).

Pass 2 — Generic pattern + value-pattern inference for unknown schemas.
          Works on any CSV with arbitrary column names.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

from app.schemas.dataset import ColumnProfile, DatasetProfile
from app.schemas.mapping import ColumnSuggestion, MappingSuggestion
from app.utils.dataframe import normalize_col_name


# ═══════════════════════════════════════════════════════════════════════════
# PASS 1: Exact vocabulary (scorecard-specific)
# ═══════════════════════════════════════════════════════════════════════════

# {normalized_name: (primary_role, confidence)}
# Additional roles (segment_field, feature_field) are handled separately.
EXACT_VOCAB: dict[str, tuple[str, float]] = {
    # Underwriting scorecard columns
    "applicationid":          ("record_id",                0.95),
    "applicationtime":        ("event_time",               0.95),
    "creditscore":            ("feature_field",            0.90),  # bureau score, NOT prediction
    "annualincome":           ("feature_field",            0.90),
    "debttoincome":           ("feature_field",            0.90),
    "employmentlength":       ("feature_field",            0.90),
    "loanamount":             ("amount_field",             0.95),
    "loanpurpose":            ("segment_field",            0.90),
    "homeownership":          ("segment_field",            0.90),
    "numberofdelinquentaccounts": ("feature_field",        0.90),
    "delinquentmonths":       ("feature_field",            0.90),
    "monthssincelastdelinquent": ("feature_field",         0.90),
    "revolvingutilization":   ("feature_field",            0.90),
    "inquirieslast6m":        ("feature_field",            0.90),
    "modelscore":             ("prediction_score",         0.95),
    "probabilityofdefault":   ("prediction_probability",   0.95),
    "riskrating":             ("risk_band",                0.95),
    "applicationstatus":      ("decision",                 0.95),
    "actualdefault":          ("target",                   0.95),
    "pastduedays":            ("dpd_field",                0.95),
    "scoreband":              ("score_band",               0.95),
    "incomeband":             ("segment_field",            0.90),
}

# Columns that also get segment_field as a secondary role (Pass 1)
_ALSO_SEGMENT = {
    "loanpurpose", "homeownership", "riskrating", "scoreband", "incomeband",
}

# Columns that also get feature_field as a secondary role (Pass 1)
_ALSO_FEATURE = {
    "creditscore", "annualincome", "debttoincome", "employmentlength",
    "loanamount", "numberofdelinquentaccounts", "delinquentmonths",
    "monthssincelastdelinquent", "revolvingutilization", "inquirieslast6m",
    "loanpurpose", "homeownership",
}


# ═══════════════════════════════════════════════════════════════════════════
# PASS 2: Generic patterns (dataset-agnostic)
# ═══════════════════════════════════════════════════════════════════════════

# {role: [keyword_substrings]} — checked against normalized column name
ROLE_PATTERNS: dict[str, list[str]] = {
    "record_id": [
        "uuid", "ref",
        "applicationid", "customerid", "loanid", "accountid", "caseid",
        "txnid", "transactionid",
    ],
    "event_time": [
        "date", "time", "dt", "timestamp", "created", "applied",
        "originated", "booked", "opened", "period",
    ],
    "target": [
        "default", "bad", "chargeoff", "chargoff", "fraud", "target",
        "label", "outcome", "event", "indicator", "delinquent",
    ],
    "prediction_score": [
        "score",
    ],
    "prediction_probability": [
        "prob", "probability", "likelihood", "propensity",
        "expectedloss", "lossrate",
    ],
    "decision": [
        "status", "decision", "approve", "decline", "accept", "reject",
        "disposition", "verdict",
    ],
    "dpd_field": [
        "dpd", "daysdue", "daysoverdue", "pastdue", "daysdelinquent",
        "daysarrears", "ageing",
    ],
    "amount_field": [
        "amount", "balance", "principal", "exposure",
        "outstanding", "disbursed", "limit",
    ],
    "score_band": [
        "scoreband", "scoretier", "scorerange", "scoregroup",
        "scorebucket", "scorebin",
    ],
    "risk_band": [
        "riskrating", "riskband", "riskgrade", "risktier",
        "riskgroup", "riskclass", "riskbucket",
    ],
    "segment_field": [
        "purpose", "type", "category", "product", "channel",
        "region", "state", "city", "branch", "segment",
        "tier", "bucket", "group", "class", "ownership", "tenure",
        "employment", "industry", "sector", "merchant",
    ],
}

# Priority order for conflict resolution (most specific first)
_ROLE_PRIORITY = [
    "prediction_probability",
    "prediction_score",
    "target",
    "decision",
    "dpd_field",
    "amount_field",
    "event_time",
    "record_id",
    "score_band",
    "risk_band",
    "segment_field",
    "feature_field",
]

# Roles where only keyword "id" should match (special handling)
_ID_KEYWORD_ROLES = {"record_id"}


# ═══════════════════════════════════════════════════════════════════════════
# Confidence labeling
# ═══════════════════════════════════════════════════════════════════════════

def _conf_label(conf: float) -> str:
    if conf >= 0.80:
        return "high"
    if conf >= 0.50:
        return "medium"
    return "low"


# ═══════════════════════════════════════════════════════════════════════════
# Main entry: suggest_mapping
# ═══════════════════════════════════════════════════════════════════════════

def suggest_mapping(
    profile: DatasetProfile,
    df: pd.DataFrame,
) -> MappingSuggestion:
    """Run two-pass heuristics and return a MappingSuggestion."""
    suggestions: list[ColumnSuggestion] = []
    segment_cols: list[str] = []
    feature_cols: list[str] = []
    unmatched: list[str] = []

    col_profiles = {cp.name: cp for cp in profile.columns}

    for col_name in df.columns:
        cp = col_profiles.get(col_name)
        if cp is None:
            continue

        norm = normalize_col_name(col_name)
        series = df[col_name]

        role, conf, reason, alt_roles = _resolve_column(
            col_name, norm, series, cp, len(df)
        )

        # Track segment and feature fields
        if role == "segment_field":
            segment_cols.append(col_name)
        if role == "feature_field":
            feature_cols.append(col_name)
        # Exact-vocab secondary roles
        if norm in _ALSO_SEGMENT and col_name not in segment_cols:
            segment_cols.append(col_name)
        if norm in _ALSO_FEATURE and col_name not in feature_cols:
            feature_cols.append(col_name)

        if conf < 0.30:
            unmatched.append(col_name)

        suggestions.append(
            ColumnSuggestion(
                column_name=col_name,
                inferred_type=cp.inferred_type,
                suggested_role=role,
                confidence=round(conf, 3),
                confidence_label=_conf_label(conf),
                reasoning=reason,
                alternative_roles=alt_roles,
                sample_values=cp.sample_values[:5],
                null_pct=cp.null_percent,
                unique_count=cp.unique_count,
                is_auto_assignable=conf >= 0.75,
            )
        )

    auto_count = sum(1 for s in suggestions if s.is_auto_assignable)
    review_count = len(suggestions) - auto_count

    return MappingSuggestion(
        dataset_id=profile.dataset_id,
        total_columns=len(suggestions),
        auto_assignable_count=auto_count,
        needs_review_count=review_count,
        suggestions=suggestions,
        unmatched_columns=unmatched,
        suggested_segments=segment_cols,
        suggested_features=feature_cols,
        monitoring_readiness=profile.monitoring_readiness,
    )


def _resolve_column(
    col_name: str,
    norm: str,
    series: pd.Series,
    cp: ColumnProfile,
    nrows: int,
) -> tuple[str, float, str, list[str]]:
    """Resolve a single column to (role, confidence, reasoning, alt_roles)."""

    # ── Pass 1: exact vocab ──
    if norm in EXACT_VOCAB:
        role, conf = EXACT_VOCAB[norm]
        reason = f"Exact vocabulary match for '{col_name}'"
        return role, conf, reason, []

    # ── Pass 2a: keyword/substring matching ──
    candidates: list[tuple[str, float, str]] = []

    for role, patterns in ROLE_PATTERNS.items():
        for pattern in patterns:
            if pattern in norm:
                # "id" alone matches only at end or if column is short
                if pattern == "id" and role == "record_id":
                    # Only match if "id" is a suffix or the norm is very short
                    if not (norm.endswith("id") or len(norm) <= 4):
                        continue

                # "score" should not match score_band/risk_band patterns
                if pattern == "score" and role == "prediction_score":
                    if any(bp in norm for bp in ("band", "tier", "range", "group", "bucket", "bin", "rating")):
                        continue

                conf = 0.75
                reason = f"Keyword '{pattern}' matches role '{role}'"
                candidates.append((role, conf, reason))
                break  # one match per role is enough

    # Deduplicate and pick best by priority
    if candidates:
        # Sort by priority order (most specific first)
        candidates.sort(key=lambda c: _ROLE_PRIORITY.index(c[0]) if c[0] in _ROLE_PRIORITY else 99)
        best_role, best_conf, best_reason = candidates[0]
        alt_roles = [c[0] for c in candidates[1:] if c[0] != best_role]

        # ── Pass 2b: value-pattern boost ──
        best_conf, best_reason = _value_pattern_boost(
            series, cp, nrows, best_role, best_conf, best_reason
        )

        return best_role, best_conf, best_reason, alt_roles

    # ── Pass 2b: value-pattern inference only (no keyword match) ──
    vp_role, vp_conf, vp_reason = _value_pattern_only(series, cp, nrows)
    if vp_role:
        return vp_role, vp_conf, vp_reason, []

    # ── Pass 2c: fallback ──
    return _fallback(cp)


def _value_pattern_boost(
    series: pd.Series,
    cp: ColumnProfile,
    nrows: int,
    role: str,
    conf: float,
    reason: str,
) -> tuple[float, str]:
    """Boost confidence if value patterns align with the keyword-matched role."""
    non_null = series.dropna()
    if len(non_null) == 0:
        return conf, reason

    if role == "prediction_probability" and cp.inferred_type == "numeric":
        vals = non_null.astype(float)
        if vals.min() >= 0 and vals.max() <= 1:
            conf = min(conf + 0.15, 0.95)
            reason += "; values in [0,1] confirm probability"

    if role == "target":
        nunique = non_null.nunique()
        if nunique == 2:
            conf = min(conf + 0.15, 0.95)
            reason += "; binary values confirm target"

    if role == "record_id":
        ratio = cp.unique_count / nrows if nrows > 0 else 0
        if ratio > 0.9:
            conf = min(conf + 0.10, 0.95)
            reason += f"; uniqueness ratio {ratio:.2f} confirms ID"

    return conf, reason


def _value_pattern_only(
    series: pd.Series,
    cp: ColumnProfile,
    nrows: int,
) -> tuple[str | None, float, str]:
    """Infer role from value patterns alone when no keyword matched."""
    non_null = series.dropna()
    if len(non_null) == 0:
        return None, 0.0, ""

    # Numeric in [0,1] → probability candidate
    if cp.inferred_type == "numeric":
        vals = non_null.astype(float)
        if len(vals) > 10 and vals.min() >= 0 and vals.max() <= 1 and vals.max() > 0:
            return "prediction_probability", 0.55, "Numeric values in [0,1] suggest probability"

    # Binary → target candidate
    if cp.inferred_type in ("boolean", "numeric"):
        if non_null.nunique() == 2:
            unique_vals = set(non_null.unique())
            if unique_vals <= {0, 1, 0.0, 1.0, True, False}:
                return "target", 0.50, "Binary {0,1} values suggest target"

    # High-uniqueness string → record_id candidate
    if cp.inferred_type == "id":
        return "record_id", 0.60, f"High uniqueness ({cp.unique_count}/{nrows}) suggests ID"

    return None, 0.0, ""


def _fallback(cp: ColumnProfile) -> tuple[str, float, str, list[str]]:
    """Assign a fallback role for unmatched columns."""
    if cp.inferred_type in ("numeric", "boolean"):
        return "feature_field", 0.25, "Numeric column defaulting to feature", []
    if cp.inferred_type == "categorical" and cp.unique_count <= 20:
        return "segment_field", 0.20, "Low-cardinality categorical defaulting to segment", []
    return "feature_field", 0.15, "Unmatched column defaulting to feature", []
