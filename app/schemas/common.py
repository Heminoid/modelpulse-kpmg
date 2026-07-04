"""Common response schemas used across all API endpoints."""

from datetime import datetime, timezone
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response envelope wrapping all endpoint responses."""

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response envelope."""

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    success: bool
    data: list[T]
    total: int
    page: int
    limit: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorDetail(BaseModel):
    """Structured error detail for validation errors."""

    field: Optional[str] = None
    message: str
    code: str
