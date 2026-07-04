from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class Finding(BaseModel):
    model_config = ConfigDict(ser_json_timedelta="iso8601")

    finding_id: str
    category: str   # "drift", "performance", "calibration", "strategy", "delinquency", "segment_risk", "data_quality", "portfolio_mix", "policy_shift"
    severity: str   # "info", "warning", "critical"
    title: str
    narrative: str
    evidence_metrics: list[str] = []
    evidence_segments: list[str] = []
    supporting_values: dict = {}
    possible_causes: list[str] = []
    recommended_actions: list[str] = []
    confidence: str = "high"
    generated_by: str = "rule_engine"


class InsightContext(BaseModel):
    model_config = ConfigDict(ser_json_timedelta="iso8601")

    run_id: str
    monitor_name: str
    template_type: str
    run_date: str
    dataset_rows: int
    has_baseline: bool

    # Dataset summary
    target_base_rate: float
    approval_rate: Optional[float] = None

    # Key metric status
    metric_status_table: list[dict] = []
    threshold_breaches: list[dict] = []
    top_worsening_metrics: list[str] = []

    # Drift summary
    top_drifting_features: list[dict] = []

    # Segment summary
    top_worsening_segments: list[dict] = []

    # Calibration highlights
    calibration_ratio_overall: Optional[float] = None
    calibration_worst_band: Optional[dict] = None

    # Delinquency highlights
    severe_dpd_rate: Optional[float] = None
    dpd_worst_segment: Optional[dict] = None

    # Findings already generated
    deterministic_findings: list[Finding] = []
    finding_count_by_severity: dict = {}

    # Recommended focus areas
    priority_review_areas: list[str] = []


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


class LLMConfig(BaseModel):
    model_config = ConfigDict(ser_json_timedelta="iso8601")

    provider: LLMProvider = LLMProvider.MOCK
    model: str = "gpt-4o"
    temperature: float = 0.3
    max_tokens: int = 2000
