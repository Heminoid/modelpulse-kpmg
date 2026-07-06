from pydantic import BaseModel, ConfigDict
from typing import Optional

class OverrideAnalysis(BaseModel):
    score_cutoff_used: float
    total_model_declines: int
    total_model_approves: int

    positive_override_count: int
    positive_override_rate: float
    positive_override_bad_rate: float
    positive_override_avg_score: float

    normal_approved_count: int
    normal_approved_bad_rate: float
    normal_approved_avg_score: float

    negative_override_count: int
    negative_override_rate: float

    override_performing_better: bool
    insight_narrative: str

    override_by_segment: list[dict] = []
