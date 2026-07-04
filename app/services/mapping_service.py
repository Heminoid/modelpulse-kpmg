"""Mapping service — suggest, save, retrieve, validate column mappings."""

from __future__ import annotations

from datetime import datetime, timezone

from loguru import logger

from app.core.config import settings
from app.core.exceptions import DatasetNotFoundError, MappingNotFoundError
from app.mapping.heuristics import suggest_mapping as _run_heuristics
from app.mapping.validator import validate_mapping as _run_validation
from app.schemas.mapping import (
    ColumnMapping,
    MappingSuggestion,
    MappingValidationResult,
    SaveMappingRequest,
)
from app.services.dataset_service import get_profile, load_dataframe
from app.storage.base import generate_id, load_json, save_json


def suggest_mapping(dataset_id: str) -> MappingSuggestion:
    """Run two-pass heuristics and return mapping suggestions."""
    logger.info("Generating mapping suggestions for dataset {}", dataset_id)

    profile = get_profile(dataset_id)
    df = load_dataframe(dataset_id)

    suggestion = _run_heuristics(profile, df)
    return suggestion


def save_mapping(
    dataset_id: str, request: SaveMappingRequest
) -> ColumnMapping:
    """Convert SaveMappingRequest to ColumnMapping and persist.

    Per Amendment A: SaveMappingRequest (§28 body) → service converts to
    persisted ColumnMapping (§10 schema).
    """
    logger.info("Saving mapping for dataset {}", dataset_id)

    # If accept_all_auto, we could re-run heuristics here; but the frontend
    # should have already populated column_roles from the suggestion response.
    # Either way, we persist what the user sends.

    mapping_id = generate_id("map")
    mapping = ColumnMapping(
        id=mapping_id,
        dataset_id=dataset_id,
        mappings=request.column_roles,
        segment_fields=request.segment_fields,
        feature_fields=request.feature_fields,
        ignored_fields=request.ignored_fields,
        score_direction=request.score_direction,
        target_positive_label=request.target_positive_label,
        decision_positive_label=request.decision_positive_label,
        created_at=datetime.now(timezone.utc),
        version=1,
    )

    # Persist by dataset_id (one mapping per dataset)
    mapping_path = settings.mappings_dir / f"{dataset_id}.json"
    save_json(mapping_path, mapping.model_dump(mode="json"))

    logger.info("Saved mapping {} for dataset {}", mapping_id, dataset_id)
    return mapping


def get_mapping(dataset_id: str) -> ColumnMapping:
    """Retrieve the persisted mapping for a dataset."""
    mapping_path = settings.mappings_dir / f"{dataset_id}.json"
    if not mapping_path.exists():
        raise MappingNotFoundError(
            f"No mapping found for dataset '{dataset_id}'"
        )
    data = load_json(mapping_path)
    return ColumnMapping(**data)


def validate_mapping_for_dataset(dataset_id: str) -> MappingValidationResult:
    """Validate the current mapping against the dataset's actual data."""
    mapping = get_mapping(dataset_id)
    df = load_dataframe(dataset_id)
    return _run_validation(df, mapping)
