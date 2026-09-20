from app.services.report_service import ReportService
from app.schemas.reports import ReportType, ReportFormat
from app.storage.run_store import MonitorRunStore
from app.core.config import settings

run_store = MonitorRunStore(settings.runs_dir)
runs, _ = run_store.list(limit=1)
if not runs:
    print("No runs found")
    exit(1)

run_id = runs[0]['run_id'] if isinstance(runs[0], dict) else runs[0].run_id
try:
    svc = ReportService()
    path = svc.generate(run_id, ReportType.FULL_TECHNICAL, ReportFormat.DOCX, run_store)
    print("SUCCESS: ", path)
except Exception as e:
    import traceback
    traceback.print_exc()
