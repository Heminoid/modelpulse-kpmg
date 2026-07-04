"""Column mapping API routes — suggest, save, get, validate."""

from fastapi import APIRouter

from app.schemas.common import APIResponse
from app.schemas.mapping import (
    ColumnMapping,
    MappingSuggestion,
    MappingValidationResult,
    SaveMappingRequest,
)
from app.services import mapping_service

router = APIRouter()


@router.post(
    "/datasets/{dataset_id}/suggest-mapping",
    response_model=APIResponse[MappingSuggestion],
)
async def suggest_mapping(dataset_id: str) -> APIResponse:
    """Auto-detect column roles and return suggestions with confidence scores."""
    suggestion = mapping_service.suggest_mapping(dataset_id)
    return APIResponse(
        success=True,
        data=suggestion,
        message=f"{suggestion.auto_assignable_count}/{suggestion.total_columns} columns auto-assignable",
    )


@router.post(
    "/datasets/{dataset_id}/save-mapping",
    response_model=APIResponse[ColumnMapping],
)
async def save_mapping(
    dataset_id: str, request: SaveMappingRequest
) -> APIResponse:
    """Save a user-confirmed column mapping."""
    mapping = mapping_service.save_mapping(dataset_id, request)
    return APIResponse(
        success=True,
        data=mapping,
        message="Mapping saved successfully",
    )


@router.get(
    "/datasets/{dataset_id}/mapping",
    response_model=APIResponse[ColumnMapping],
)
async def get_mapping(dataset_id: str) -> APIResponse:
    """Retrieve the persisted mapping for a dataset."""
    mapping = mapping_service.get_mapping(dataset_id)
    return APIResponse(success=True, data=mapping)


@router.get(
    "/datasets/{dataset_id}/mapping/validate",
    response_model=APIResponse[MappingValidationResult],
)
async def validate_mapping(dataset_id: str) -> APIResponse:
    """Validate the current mapping against the dataset's data."""
    result = mapping_service.validate_mapping_for_dataset(dataset_id)
    return APIResponse(success=True, data=result)
