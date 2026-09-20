from app.services.report_service import ReportService
from app.schemas.reports import ReportType, ReportFormat
from app.storage.run_store import MonitorRunStore
from app.core.config import settings

run_store = MonitorRunStore(settings.runs_dir)
runs, _ = run_store.list(limit=100)

svc = ReportService()
for r in runs:
    run_id = r['run_id'] if isinstance(r, dict) else r.run_id
    try:
        path = svc.generate(run_id, ReportType.FULL_TECHNICAL, ReportFormat.DOCX, run_store)
        print(f"SUCCESS: {run_id}")
    except Exception as e:
        print(f"FAILED: {run_id} - {e}")
        import traceback
        traceback.print_exc()
