from app.schemas.reports import ReportRequest, ReportType, ReportFormat
from app.api.routes.reports import generate_report

req = ReportRequest(report_type=ReportType.FULL_TECHNICAL, format=ReportFormat.DOCX)
generate_report("run_f66c1afeefdd", req)
