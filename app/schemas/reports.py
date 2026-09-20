from pydantic import BaseModel, ConfigDict
from enum import Enum
from datetime import datetime

class ReportType(str, Enum):
    EXECUTIVE_SUMMARY = "executive_summary"
    FULL_TECHNICAL    = "full_technical"
    DATA_QUALITY      = "data_quality"
    SR_11_7_CHECKLIST = "sr_11_7"
    IFRS9_MONITORING  = "ifrs9"

class ReportFormat(str, Enum):
    PDF  = "pdf"
    HTML = "html"
    DOCX = "docx"

from typing import Optional

class ReportRequest(BaseModel):
    report_type: ReportType
    format: ReportFormat
    sections: Optional[list[str]] = None

class ReportMeta(BaseModel):
    report_id: str
    report_type: str
    format: str
    file_path: str
    download_url: str
    size_bytes: int
    generated_at: datetime
