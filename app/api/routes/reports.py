import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Optional

from app.schemas.reports import ReportRequest, ReportMeta, ReportType, ReportFormat
from app.schemas.common import APIResponse
from app.services.report_service import ReportService, WeasyPrintUnavailableError
from app.storage.run_store import MonitorRunStore
from app.core.config import settings

router = APIRouter(prefix="/runs/{run_id}/reports", tags=["Reports"])
report_service = ReportService()
run_store = MonitorRunStore(settings.runs_dir)

@router.post("/generate", response_model=APIResponse[ReportMeta])
def generate_report(run_id: str, req: ReportRequest):
    run = run_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    try:
        out_path = report_service.generate(run_id, req.report_type, req.format, run_store, sections=req.sections)
    except WeasyPrintUnavailableError as e:
        # Gracefully fallback to HTML if system doesn't have PDF native dependencies installed (like pango)
        out_path = report_service.generate(run_id, req.report_type, ReportFormat.HTML, run_store, sections=req.sections)
        
    reports_meta = run_store.load_artifact(run_id, "reports.json") or []
    # Find the most recently added report which is the one just generated
    latest_meta = reports_meta[-1]
    
    return APIResponse(success=True, data=ReportMeta(**latest_meta))

@router.get("", response_model=APIResponse[list[ReportMeta]])
def list_reports(run_id: str):
    run = run_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    reports_meta = run_store.load_artifact(run_id, "reports.json") or []
    return APIResponse(success=True, data=[ReportMeta(**m) for m in reports_meta])

@router.get("/{report_id}/download")
def download_report(run_id: str, report_id: str):
    run = run_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    reports_meta = run_store.load_artifact(run_id, "reports.json") or []
    target_meta = next((m for m in reports_meta if m["report_id"] == report_id), None)
    
    if not target_meta:
        raise HTTPException(status_code=404, detail="Report not found")
        
    file_path = target_meta["file_path"]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report file missing")
        
    fmt = target_meta.get("format", "html")
    if fmt == 'pdf':
        media_type = 'application/pdf'
    elif fmt == 'docx':
        media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    else:
        media_type = 'text/html'
    filename = f"report_{run_id}_{target_meta.get('report_type')}.{fmt}"
    
    return FileResponse(path=file_path, media_type=media_type, filename=filename)

@router.get("/qa/{report_type}")
def get_report_qa(run_id: str, report_type: str):
    run = run_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    from app.services.report_qa import run_qa_check
    result = run_qa_check(report_type, run_store, run_id)
    return APIResponse(success=True, data=result)
