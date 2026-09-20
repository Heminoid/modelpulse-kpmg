"""Dataset-related schemas for upload, profiling, and listing."""

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ColumnProfile(BaseModel):
    """Profile of a single column in an uploaded dataset."""

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    name: str
    original_name: str
    inferred_type: str  # "numeric", "categorical", "datetime", "boolean", "id", "unknown"
    null_count: int
    null_percent: float
    unique_count: int
    sample_values: list[Any] = Field(default_factory=list)
    # Numeric only
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    mean_val: Optional[float] = None
    std_val: Optional[float] = None
    median_val: Optional[float] = None
    # Categorical only
    top_categories: Optional[list[dict]] = None
    # Datetime only
    parse_success: Optional[bool] = None
    parse_warning: Optional[str] = None
    # ID-like
    is_likely_id: Optional[bool] = None
    # MRM Flags
    flags: list[str] = Field(default_factory=list)


class DatasetProfile(BaseModel):
    """Full profile of an uploaded dataset."""

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    dataset_id: str
    row_count: int
    column_count: int
    file_size_bytes: int
    duplicate_row_count: int
    columns: list[ColumnProfile]
    null_summary: dict[str, int]
    monitoring_readiness: list[str] = Field(default_factory=list)
    preview_rows: list[dict] = Field(default_factory=list)


class DatasetUploadResponse(BaseModel):
    """Response after a successful dataset upload."""

    id: str
    filename: str
    row_count: int
    column_count: int
    file_size_bytes: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "uploaded"


class DatasetSummary(BaseModel):
    """Lightweight dataset summary for list endpoints."""

    id: str
    filename: str
    row_count: int
    column_count: int
    file_size_bytes: int
    created_at: Optional[str] = None
    status: Optional[str] = None
    has_mapping: Optional[bool] = None
