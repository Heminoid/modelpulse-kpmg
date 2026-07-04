"""Column mapping schemas — suggestion, save request, persisted mapping."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ColumnRole(str, Enum):
    """All recognized column roles in ModelPulse."""

    RECORD_ID = "record_id"
    EVENT_TIME = "event_time"
    TARGET = "target"
    PREDICTION_SCORE = "prediction_score"
    PREDICTION_PROBABILITY = "prediction_probability"
    DECISION = "decision"
    DPD_FIELD = "dpd_field"
    AMOUNT_FIELD = "amount_field"
    SCORE_BAND = "score_band"
    RISK_BAND = "risk_band"
    SEGMENT_FIELD = "segment_field"
    FEATURE_FIELD = "feature_field"
    IGNORED = "ignored"


# ---------------------------------------------------------------------------
# Suggestion response (§28 winner per Amendment A)
# ---------------------------------------------------------------------------

class ColumnSuggestion(BaseModel):
    """Auto-detected role suggestion for a single column."""

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    column_name: str
    inferred_type: str
    suggested_role: str
    confidence: float  # 0.0–1.0
    confidence_label: str  # "high" (>0.8), "medium" (0.5-0.8), "low" (<0.5)
    reasoning: str
    alternative_roles: list[str] = Field(default_factory=list)
    sample_values: list[Any] = Field(default_factory=list)
    null_pct: float = 0.0
    unique_count: int = 0
    is_auto_assignable: bool = False  # True if confidence >= 0.75


class MappingSuggestion(BaseModel):
    """Full mapping suggestion for a dataset — one ColumnSuggestion per column."""

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    dataset_id: str
    total_columns: int
    auto_assignable_count: int
    needs_review_count: int
    suggestions: list[ColumnSuggestion]
    available_roles: list[str] = Field(
        default_factory=lambda: [r.value for r in ColumnRole]
    )
    unmatched_columns: list[str] = Field(default_factory=list)
    suggested_segments: list[str] = Field(default_factory=list)
    suggested_features: list[str] = Field(default_factory=list)
    monitoring_readiness: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Save mapping request (§28 body → service converts to ColumnMapping)
# ---------------------------------------------------------------------------

class SaveMappingRequest(BaseModel):
    """User-confirmed mapping submitted after reviewing suggestions."""

    column_roles: dict[str, str]  # {column_name: role_key}
    segment_fields: list[str] = Field(default_factory=list)
    feature_fields: list[str] = Field(default_factory=list)
    ignored_fields: list[str] = Field(default_factory=list)
    score_direction: str = "higher_is_better"
    target_positive_label: Any = 1
    decision_positive_label: str = "APPROVED"
    accept_all_auto: bool = False


# ---------------------------------------------------------------------------
# Persisted mapping (§10 schema)
# ---------------------------------------------------------------------------

class ColumnMapping(BaseModel):
    """Persisted column mapping — the confirmed, canonical form."""

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    id: Optional[str] = None
    dataset_id: str
    mappings: dict[str, str]  # {column_name: role_key}
    segment_fields: list[str] = Field(default_factory=list)
    feature_fields: list[str] = Field(default_factory=list)
    ignored_fields: list[str] = Field(default_factory=list)
    score_direction: str = "higher_is_better"
    target_positive_label: Any = 1
    decision_positive_label: str = "APPROVED"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------

class MappingValidationWarning(BaseModel):
    """A single validation warning for a mapped column."""

    column: str
    role: str
    warning: str
    severity: str = "warning"  # "warning" or "error"


class MappingValidationResult(BaseModel):
    """Result of validating a confirmed mapping against actual data."""

    is_valid: bool
    warnings: list[MappingValidationWarning] = Field(default_factory=list)
