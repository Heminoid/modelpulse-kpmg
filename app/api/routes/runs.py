from fastapi import APIRouter, HTTPException, Response
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




@router.get("/{run_id}/charts")
def get_run_charts(run_id: str, format: Optional[str] = None):
    run = store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    charts = store.load_artifact(run_id, "charts.json")
    if charts is None:
        return APIResponse(success=True, data=[])
        
    if format == "png":
        import io
        import zipfile
        from app.charts.renderer import render_chart
        from app.schemas.charts import ChartPayload
        
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for c_data in charts:
                payload = ChartPayload(**c_data)
                img_bytes = render_chart(payload, fmt="png")
                zf.writestr(f"{payload.chart_id}.png", img_bytes)
        
        buf.seek(0)
        return Response(content=buf.read(), media_type="application/zip")
        
    # Standard JSON response, inject image_url
    for c in charts:
        c["image_url"] = f"/api/v1/runs/{run_id}/charts/{c['chart_id']}/image"
    return APIResponse(success=True, data=charts)

@router.get("/{run_id}/charts/{chart_id}/image")
def get_chart_image(run_id: str, chart_id: str, format: str = "png"):
    charts = store.load_artifact(run_id, "charts.json")
    if not charts:
        raise HTTPException(status_code=404, detail="Charts not found")
        
    chart_data = next((c for c in charts if c["chart_id"] == chart_id), None)
    if not chart_data:
        raise HTTPException(status_code=404, detail="Chart not found")
        
    from app.charts.renderer import render_chart
    from app.schemas.charts import ChartPayload
    payload = ChartPayload(**chart_data)
    
    img_bytes = render_chart(payload, fmt=format)
    media_type = "image/svg+xml" if format == "svg" else "image/png"
    return Response(content=img_bytes, media_type=media_type)

@router.get("/{run_id}", response_model=APIResponse[RunMetadata])
def get_run(run_id: str):
    run = store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return APIResponse(success=True, data=run)
