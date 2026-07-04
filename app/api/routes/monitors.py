import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from typing import Optional

from app.schemas.monitors import MonitorConfig
from app.storage.monitor_store import MonitorConfigStore
from app.services.run_service import execute_run
from app.schemas.common import APIResponse, PaginatedResponse
from app.core.config import settings

router = APIRouter(prefix="/monitors", tags=["monitors"])
store = MonitorConfigStore(settings.monitor_configs_dir)

@router.post("", response_model=APIResponse[MonitorConfig])
def create_monitor(config: MonitorConfig):
    if not config.monitor_id:
        config.monitor_id = f"mon_{uuid.uuid4().hex[:12]}"
    config.created_at = datetime.now(timezone.utc)
    config.updated_at = datetime.now(timezone.utc)
    
    created = store.create(config.model_dump())
    return APIResponse(success=True, data=created)

@router.get("", response_model=PaginatedResponse[MonitorConfig])
def list_monitors(page: int = 1, limit: int = 20):
    items, total = store.list(page=page, limit=limit)
    return PaginatedResponse(success=True, data=items, total=total, page=page, limit=limit)

@router.get("/{monitor_id}", response_model=APIResponse[MonitorConfig])
def get_monitor(monitor_id: str):
    monitor = store.get(monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return APIResponse(success=True, data=monitor)

@router.post("/{monitor_id}/run", response_model=APIResponse[dict])
def trigger_run(monitor_id: str):
    meta = execute_run(monitor_id)
    return APIResponse(success=True, data=meta.model_dump())
