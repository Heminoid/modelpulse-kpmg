"""Health check endpoint."""

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.common import APIResponse

router = APIRouter()


@router.get("/health", response_model=APIResponse)
async def health_check() -> APIResponse:
    """Return application health status with version info."""
    return APIResponse(
        success=True,
        data={
            "status": "ok",
            "app_name": settings.app_name,
            "version": settings.app_version,
            "storage_root": str(settings.storage_root),
            "storage_exists": settings.storage_root.exists(),
        },
        message="Service is healthy",
    )
