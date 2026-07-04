"""Mapping validation — checks confirmed mappings against actual data."""

from __future__ import annotations

import pandas as pd
from loguru import logger

from app.schemas.mapping import (
    ColumnMapping,
    MappingValidationResult,
    MappingValidationWarning,
)


def validate_mapping(
    df: pd.DataFrame, mapping: ColumnMapping
) -> MappingValidationResult:
    """Validate a confirmed mapping against the dataset.

    Returns warnings but never blocks the save — user has final say.
    """
    warnings: list[MappingValidationWarning] = []

    # Build role → column(s) lookup
    role_cols: dict[str, list[str]] = {}
    for col, role in mapping.mappings.items():
        role_cols.setdefault(role, []).append(col)

    # 1. Target: must be binary, warn if < 30 positives
    for col in role_cols.get("target", []):
        if col not in df.columns:
            continue
        non_null = df[col].dropna()
        nunique = non_null.nunique()
        if nunique != 2:
            warnings.append(MappingValidationWarning(
                column=col, role="target",
                warning=f"Target column has {nunique} unique values (expected 2)",
                severity="warning",
            ))
        positives = (non_null == mapping.target_positive_label).sum()
        if 0 < positives < 30:
            warnings.append(MappingValidationWarning(
                column=col, role="target",
                warning=f"Only {positives} positive cases — metrics will have low statistical power",
                severity="warning",
            ))

    # 2. Prediction probability: numeric, [0,1]
    for col in role_cols.get("prediction_probability", []):
        if col not in df.columns:
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            warnings.append(MappingValidationWarning(
                column=col, role="prediction_probability",
                warning="Prediction probability column is not numeric",
                severity="error",
            ))
            continue
        non_null = df[col].dropna()
        above = (non_null > 1).sum()
        below = (non_null < 0).sum()
        if above > 0 or below > 0:
            warnings.append(MappingValidationWarning(
                column=col, role="prediction_probability",
                warning=f"Values out of [0,1] range: {above} above 1, {below} below 0",
                severity="warning",
            ))

    # 3. Prediction score: must be numeric
    for col in role_cols.get("prediction_score", []):
        if col not in df.columns:
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            warnings.append(MappingValidationWarning(
                column=col, role="prediction_score",
                warning="Prediction score column is not numeric",
                severity="error",
            ))

    # 4. DPD field: numeric, non-negative
    for col in role_cols.get("dpd_field", []):
        if col not in df.columns:
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            warnings.append(MappingValidationWarning(
                column=col, role="dpd_field",
                warning="DPD field is not numeric",
                severity="error",
            ))
            continue
        non_null = df[col].dropna()
        neg = (non_null < 0).sum()
        if neg > 0:
            warnings.append(MappingValidationWarning(
                column=col, role="dpd_field",
                warning=f"{neg} negative DPD values found",
                severity="warning",
            ))

    # 5. Event time: warn if parse fails
    for col in role_cols.get("event_time", []):
        if col not in df.columns:
            continue
        try:
            parsed = pd.to_datetime(df[col], errors="coerce")
            success = parsed.notna().sum()
            total = df[col].notna().sum()
            if total > 0 and success / total < 0.5:
                warnings.append(MappingValidationWarning(
                    column=col, role="event_time",
                    warning=f"Only {success}/{total} values parsed as datetime",
                    severity="warning",
                ))
        except Exception:
            warnings.append(MappingValidationWarning(
                column=col, role="event_time",
                warning="Could not parse column as datetime",
                severity="warning",
            ))

    # 6. Decision: warn if > 5 unique values
    for col in role_cols.get("decision", []):
        if col not in df.columns:
            continue
        nunique = df[col].dropna().nunique()
        if nunique > 5:
            warnings.append(MappingValidationWarning(
                column=col, role="decision",
                warning=f"Decision column has {nunique} unique values (expected 2–3)",
                severity="warning",
            ))
        elif nunique > 2:
            warnings.append(MappingValidationWarning(
                column=col, role="decision",
                warning=f"Decision column has {nunique} unique values (expected 2); check if this is intentional",
                severity="warning",
            ))

    is_valid = not any(w.severity == "error" for w in warnings)

    logger.info(
        "Mapping validation for dataset {}: {} warnings, valid={}",
        mapping.dataset_id, len(warnings), is_valid,
    )
    return MappingValidationResult(is_valid=is_valid, warnings=warnings)
