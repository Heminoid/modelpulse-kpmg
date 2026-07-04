"""Dataset API routes — upload, list, get, profile, preview, delete."""

from fastapi import APIRouter, File, Query, UploadFile

from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.dataset import DatasetProfile, DatasetSummary, DatasetUploadResponse
from app.services import dataset_service

router = APIRouter()


@router.post("/datasets/upload", response_model=APIResponse[DatasetUploadResponse])
async def upload_dataset(file: UploadFile = File(...)) -> APIResponse:
    """Upload a CSV file, profile it, and return metadata."""
    contents = await file.read()
    result = dataset_service.upload_dataset(
        filename=file.filename or "unknown.csv",
        file_bytes=contents,
    )
    return APIResponse(
        success=True,
        data=result,
        message=f"Dataset uploaded: {result.row_count} rows, {result.column_count} columns",
    )


@router.get("/datasets", response_model=PaginatedResponse[DatasetSummary])
async def list_datasets(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> PaginatedResponse:
    """List all uploaded datasets with pagination."""
    items, total = dataset_service.list_datasets(page=page, limit=limit)
    return PaginatedResponse(
        success=True,
        data=items,
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/datasets/{dataset_id}", response_model=APIResponse)
async def get_dataset(dataset_id: str) -> APIResponse:
    """Retrieve metadata for a single dataset."""
    data = dataset_service.get_dataset(dataset_id)
    return APIResponse(success=True, data=data)


@router.get("/datasets/{dataset_id}/profile", response_model=APIResponse[DatasetProfile])
async def get_dataset_profile(dataset_id: str) -> APIResponse:
    """Retrieve the full profile for a dataset."""
    profile = dataset_service.get_profile(dataset_id)
    return APIResponse(success=True, data=profile)


@router.get("/datasets/{dataset_id}/preview", response_model=APIResponse)
async def get_dataset_preview(
    dataset_id: str,
    rows: int = Query(10, ge=1, le=100),
) -> APIResponse:
    """Return the first N rows of a dataset."""
    preview = dataset_service.get_preview(dataset_id, rows=rows)
    return APIResponse(success=True, data=preview)


@router.delete("/datasets/{dataset_id}", response_model=APIResponse)
async def delete_dataset(dataset_id: str) -> APIResponse:
    """Delete a dataset and all associated files."""
    dataset_service.delete_dataset(dataset_id)
    return APIResponse(success=True, message=f"Dataset '{dataset_id}' deleted")
