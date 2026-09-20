from pydantic import BaseModel, ConfigDict
from typing import Optional
from enum import Enum
from datetime import datetime

class ModelLifecycleStage(str, Enum):
    DEVELOPMENT  = "development"
    VALIDATION   = "validation"
    PRODUCTION   = "production"
    SHADOW       = "shadow"
    CHALLENGER   = "challenger"
    RETIRED      = "retired"

class RegisteredModelBase(BaseModel):
    name: str
    version: str
    model_type: str
    description: Optional[str] = None
    owner: str
    lifecycle_stage: ModelLifecycleStage = ModelLifecycleStage.DEVELOPMENT
    is_champion: bool = False
    
    dev_auc: Optional[float] = None
    dev_gini: Optional[float] = None
    dev_ks: Optional[float] = None
    dev_bad_rate: Optional[float] = None
    dev_approval_rate: Optional[float] = None
    dev_dataset_description: Optional[str] = None

class RegisteredModelCreate(RegisteredModelBase):
    pass

class RegisteredModelUpdate(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    model_type: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = None
    lifecycle_stage: Optional[ModelLifecycleStage] = None
    is_champion: Optional[bool] = None
    dev_auc: Optional[float] = None
    dev_gini: Optional[float] = None
    dev_ks: Optional[float] = None
    dev_bad_rate: Optional[float] = None
    dev_approval_rate: Optional[float] = None
    dev_dataset_description: Optional[str] = None

class RegisteredModel(RegisteredModelBase):
    model_id: str
    linked_monitor_ids: list[str] = []
    linked_run_ids: list[str] = []
    registered_at: datetime
    updated_at: datetime
    promoted_to_production_at: Optional[datetime] = None

class ChampionChallengerResult(BaseModel):
    champion_model_id: str
    challenger_model_id: str
    champion_latest_metrics: dict
    challenger_latest_metrics: dict
    metric_deltas: dict
    metric_winners: dict
    recommendation: str
    summary: str
    ai_narrative: dict | None = None
