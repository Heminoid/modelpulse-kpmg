from pydantic import BaseModel, ConfigDict
from typing import Optional

class FairnessAnalysis(BaseModel):
    proxy_groups_analyzed: list[str]
    overall_approval_rate: float
    di_results: list[dict]
    adverse_impact_flags: list[dict]
    borderline_flags: list[dict]
    regulatory_note: str
    recommended_actions: list[str]
    ecoa_compliance_summary: str
