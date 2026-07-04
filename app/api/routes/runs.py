from fastapi import APIRouter, HTTPException
from typing import Optional

from app.storage.run_store import MonitorRunStore
from app.schemas.runs import RunMetadata
from app.schemas.common import APIResponse, PaginatedResponse
from app.core.config import settings

router = APIRouter(prefix="/runs", tags=["runs"])
store = MonitorRunStore(settings.runs_dir)


@router.get("", response_model=PaginatedResponse[RunMetadata])
def list_runs(monitor_id: Optional[str] = None, page: int = 1, limit: int = 20):
    items, total = store.list(monitor_id=monitor_id, page=page, limit=limit)
    return PaginatedResponse(success=True, data=items, total=total, page=page, limit=limit)


@router.get("/{run_id}", response_model=APIResponse[RunMetadata])
def get_run(run_id: str):
    run = store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return APIResponse(success=True, data=run)
