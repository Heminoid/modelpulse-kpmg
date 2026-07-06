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

@router.get("/{run_id}/metrics")
def get_run_metrics(run_id: str):
    run = store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    metrics = store.load_artifact(run_id, "metrics.json")
    if not metrics:
        raise HTTPException(status_code=404, detail="Metrics not found for this run")
        
    return APIResponse(success=True, data=metrics)

@router.get("/{run_id}/stat-tests")
def get_run_stat_tests(run_id: str):
    run = store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    stat_tests = store.load_artifact(run_id, "stat_tests.json")
    if not stat_tests:
        raise HTTPException(status_code=404, detail="Stat tests not found for this run")
        
    return APIResponse(success=True, data=stat_tests)

@router.get("/{run_id}/vintage")
def get_run_vintage(run_id: str):
    run = store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    vintage = store.load_artifact(run_id, "vintage.json")
    if not vintage:
        raise HTTPException(status_code=404, detail="Vintage analysis not found for this run")
        
    return APIResponse(success=True, data=vintage)

@router.get("/{run_id}/override-analysis")
def get_run_override_analysis(run_id: str, score_cutoff: float = 600.0):
    run = store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    override_data = store.load_artifact(run_id, "override.json")
    if not override_data:
        raise HTTPException(status_code=404, detail="Override analysis not found for this run")
        
    key = str(float(score_cutoff)) if score_cutoff.is_integer() else str(score_cutoff)
    if float(score_cutoff).is_integer():
        key = str(int(score_cutoff))
        
    # We generated string keys for floats/ints. Easiest is to check if it exists
    if key in override_data:
        return APIResponse(success=True, data=override_data[key])
    elif str(float(score_cutoff)) in override_data:
        return APIResponse(success=True, data=override_data[str(float(score_cutoff))])
    else:
        # If it doesn't match a precalculated one, we just return the first one as a fallback or 600
        if "600" in override_data:
            return APIResponse(success=True, data=override_data["600"])
        elif "600.0" in override_data:
            return APIResponse(success=True, data=override_data["600.0"])
        raise HTTPException(status_code=400, detail=f"Score cutoff {score_cutoff} not precomputed.")

@router.get("/{run_id}/fairness")
def get_run_fairness(run_id: str):
    run = store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    fairness = store.load_artifact(run_id, "fairness.json")
    if not fairness:
        raise HTTPException(status_code=404, detail="Fairness analysis not found for this run")
        
    return APIResponse(success=True, data=fairness)

@router.get("/{run_id}/time-series")
def get_run_time_series(run_id: str):
    run = store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    ts = store.load_artifact(run_id, "timeseries.json")
    if not ts:
        raise HTTPException(status_code=404, detail="Time-series analysis not found for this run")
        
    return APIResponse(success=True, data=ts)

@router.get("/{run_id}", response_model=APIResponse[RunMetadata])
def get_run(run_id: str):
    run = store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return APIResponse(success=True, data=run)

@router.delete("/{run_id}")
def delete_run(run_id: str):
    success = store.delete(run_id)
    if not success:
        raise HTTPException(status_code=404, detail="Run not found")
    return APIResponse(success=True, data=None)


@router.post("/{run_id}/narratives")
async def generate_narrative(run_id: str):
    run = store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    context_data = store.load_artifact(run_id, "insights.json")
    if not context_data:
        raise HTTPException(status_code=404, detail="InsightContext not found for this run")
        
    from app.schemas.insights import InsightContext
    from app.services.llm_service import LLMService
    
    context = InsightContext(**context_data)
    svc = LLMService()
    narrative = await svc.generate_narrative(context)
    
    store.save_artifact(run_id, "narratives.json", narrative)
    return APIResponse(success=True, data=narrative)


@router.get("/{run_id}/narratives")
def get_narratives(run_id: str):
    run = store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    narrative = store.load_artifact(run_id, "narratives.json")
    if not narrative:
        raise HTTPException(status_code=404, detail="Narratives not found")
    return APIResponse(success=True, data=narrative)
