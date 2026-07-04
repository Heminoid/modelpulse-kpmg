"""Dataset service — upload, profile, list, retrieve, delete."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from loguru import logger

from app.core.config import settings
from app.core.exceptions import (
    DatasetNotFoundError,
    FileTooLargeError,
    InvalidFileTypeError,
)
from app.profiling.profiler import profile_dataset
from app.schemas.dataset import DatasetProfile, DatasetSummary, DatasetUploadResponse
from app.storage.base import generate_id, load_json, save_json
from app.storage.dataset_store import DatasetStore


_dataset_store = DatasetStore(settings.uploads_dir)


def get_store() -> DatasetStore:
    """Return the singleton dataset store."""
    return _dataset_store


def upload_dataset(
    filename: str,
    file_bytes: bytes,
) -> DatasetUploadResponse:
    """Validate, save, and profile an uploaded CSV file."""
    # Validate extension
    ext = Path(filename).suffix.lower()
    if ext not in settings.allowed_extensions:
        raise InvalidFileTypeError(
            f"File type '{ext}' not allowed. Accepted: {settings.allowed_extensions}"
        )

    # Validate size
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > settings.max_upload_size_mb:
        raise FileTooLargeError(
            f"File size {size_mb:.1f}MB exceeds limit of {settings.max_upload_size_mb}MB"
        )

    dataset_id = generate_id("ds")
    logger.info("Uploading dataset {} ({})", dataset_id, filename)

    # Save raw CSV
    csv_path = settings.uploads_dir / f"{dataset_id}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_bytes(file_bytes)

    # Load and profile
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        csv_path.unlink(missing_ok=True)
        raise InvalidFileTypeError(f"Could not parse CSV: {e}") from e

    file_size = len(file_bytes)
    profile = profile_dataset(df, dataset_id, file_size)

    # Persist profile
    profile_path = settings.profiles_dir / f"{dataset_id}.json"
    save_json(profile_path, profile.model_dump(mode="json"))

    # Persist dataset metadata
    now = datetime.now(timezone.utc).isoformat()
    meta = {
        "id": dataset_id,
        "filename": filename,
        "row_count": len(df),
        "column_count": len(df.columns),
        "file_size_bytes": file_size,
        "csv_path": str(csv_path),
        "created_at": now,
        "status": "uploaded",
    }
    _dataset_store.create(meta)

    return DatasetUploadResponse(
        id=dataset_id,
        filename=filename,
        row_count=len(df),
        column_count=len(df.columns),
        file_size_bytes=file_size,
    )


def get_dataset(dataset_id: str) -> dict:
    """Retrieve dataset metadata or raise DatasetNotFoundError."""
    data = _dataset_store.get(dataset_id)
    if data is None:
        raise DatasetNotFoundError(f"Dataset '{dataset_id}' not found")
    return data


def list_datasets(page: int = 1, limit: int = 20) -> tuple[list[dict], int]:
    """List datasets with pagination."""
    return _dataset_store.list(page=page, limit=limit)


def get_profile(dataset_id: str) -> DatasetProfile:
    """Load the profile for a dataset."""
    # Ensure dataset exists
    get_dataset(dataset_id)

    profile_path = settings.profiles_dir / f"{dataset_id}.json"
    if not profile_path.exists():
        raise DatasetNotFoundError(f"Profile for dataset '{dataset_id}' not found")

    data = load_json(profile_path)
    return DatasetProfile(**data)


def get_preview(dataset_id: str, rows: int = 10) -> list[dict]:
    """Return the first N rows of a dataset as dicts."""
    meta = get_dataset(dataset_id)
    csv_path = Path(meta["csv_path"])
    if not csv_path.exists():
        raise DatasetNotFoundError(f"CSV file for dataset '{dataset_id}' not found")

    df = pd.read_csv(csv_path, nrows=rows)
    import numpy as np
    return df.replace({np.nan: None}).to_dict(orient="records")


def load_dataframe(dataset_id: str) -> pd.DataFrame:
    """Load the raw DataFrame for a dataset (used by mapping/run services)."""
    meta = get_dataset(dataset_id)
    csv_path = Path(meta["csv_path"])
    if not csv_path.exists():
        raise DatasetNotFoundError(f"CSV file for dataset '{dataset_id}' not found")
    return pd.read_csv(csv_path)


def delete_dataset(dataset_id: str) -> bool:
    """Delete a dataset and its associated files."""
    meta = _dataset_store.get(dataset_id)
    if meta is None:
        raise DatasetNotFoundError(f"Dataset '{dataset_id}' not found")

    # Delete CSV
    csv_path = Path(meta.get("csv_path", ""))
    if csv_path.exists():
        csv_path.unlink()

    # Delete profile
    profile_path = settings.profiles_dir / f"{dataset_id}.json"
    if profile_path.exists():
        profile_path.unlink()

    # Delete mapping
    mapping_path = settings.mappings_dir / f"{dataset_id}.json"
    if mapping_path.exists():
        mapping_path.unlink()

    # Delete metadata
    _dataset_store.delete(dataset_id)
    logger.info("Deleted dataset {} and all associated files", dataset_id)
    return True
