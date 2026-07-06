from app.services.report_service import ReportService
from app.schemas.reports import ReportType, ReportFormat
from app.storage.run_store import MonitorRunStore
from pathlib import Path
import traceback

try:
    rs = ReportService()
    run_store = MonitorRunStore(Path("storage/runs"))
    out = rs.generate("run_f66c1afeefdd", ReportType.FULL_TECHNICAL, ReportFormat.PDF, run_store)
    print("Success:", out)
except Exception as e:
    traceback.print_exc()
