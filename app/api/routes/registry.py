from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.registry import (
    RegisteredModel, RegisteredModelCreate, RegisteredModelUpdate, ChampionChallengerResult
)
from app.storage.model_registry_store import ModelRegistryStore
from app.storage.run_store import MonitorRunStore
from app.core.config import settings

router = APIRouter(prefix="/registry", tags=["Model Registry"])
store = ModelRegistryStore()
run_store = MonitorRunStore(settings.runs_dir)

@router.post("/models", response_model=APIResponse[RegisteredModel])
def create_model(model_in: RegisteredModelCreate):
    model = store.create(model_in.model_dump())
    return APIResponse(success=True, data=model)

@router.get("/models", response_model=PaginatedResponse[RegisteredModel])
def list_models(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    stage: Optional[str] = None
):
    skip = (page - 1) * limit
    models, total = store.list(skip=skip, limit=limit, stage=stage)
    return PaginatedResponse(
        success=True,
        data=models,
        page=page,
        limit=limit,
        total=total
    )

@router.get("/champion", response_model=APIResponse[RegisteredModel])
def get_champion():
    model = store.get_champion()
    if not model:
        raise HTTPException(status_code=404, detail="No champion model found")
    return APIResponse(success=True, data=model)

@router.get("/models/{model_id}", response_model=APIResponse[RegisteredModel])
def get_model(model_id: str):
    model = store.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return APIResponse(success=True, data=model)

@router.put("/models/{model_id}", response_model=APIResponse[RegisteredModel])
def update_model(model_id: str, model_in: RegisteredModelUpdate):
    model = store.update(model_id, model_in.model_dump(exclude_unset=True))
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return APIResponse(success=True, data=model)

@router.post("/models/{model_id}/link-run/{run_id}", response_model=APIResponse[RegisteredModel])
def link_run(model_id: str, run_id: str):
    run = run_store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    model = store.link_run(model_id, run_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return APIResponse(success=True, data=model)

@router.get("/champion-challenger", response_model=APIResponse[ChampionChallengerResult])
async def compare_champion_challenger(champion_id: str, challenger_id: str, include_narrative: bool = False):
    champ = store.get(champion_id)
    chall = store.get(challenger_id)
    if not champ or not chall:
        raise HTTPException(status_code=404, detail="Champion or Challenger model not found")
        
    def _get_latest_metrics(model: RegisteredModel) -> dict:
        if not model.linked_run_ids:
            return {}
        latest_run_id = model.linked_run_ids[-1]
        metrics = run_store.load_artifact(latest_run_id, "metrics.json")
        if not metrics:
            return {}
        return {m["metric_key"]: m.get("scalar_value") for m in metrics if m.get("scalar_value") is not None}
        
    champ_metrics = _get_latest_metrics(champ)
    chall_metrics = _get_latest_metrics(chall)
    
    keys = set(champ_metrics.keys()) | set(chall_metrics.keys())
    deltas = {}
    winners = {}
    
    for k in keys:
        cv = champ_metrics.get(k)
        chv = chall_metrics.get(k)
        if cv is not None and chv is not None:
            delta = chv - cv
            deltas[k] = delta
            # Simple assumption: for perf metrics higher is better except for psi
            if k.startswith("psi_"):
                winners[k] = "challenger" if delta < 0 else ("champion" if delta > 0 else "tie")
            else:
                winners[k] = "challenger" if delta > 0 else ("champion" if delta < 0 else "tie")
                
    chall_wins = list(winners.values()).count("challenger")
    champ_wins = list(winners.values()).count("champion")
    
    if chall_wins > champ_wins:
        rec = "Challenger outperforms champion on key metrics — consider promotion"
    else:
        rec = "Champion remains dominant — do not promote challenger"
        
    res = ChampionChallengerResult(
        champion_model_id=champion_id,
        challenger_model_id=challenger_id,
        champion_latest_metrics=champ_metrics,
        challenger_latest_metrics=chall_metrics,
        metric_deltas=deltas,
        metric_winners=winners,
        recommendation=rec,
        summary=f"Challenger won {chall_wins} metrics, Champion won {champ_wins} metrics."
    )
    
    if include_narrative:
        from app.services.llm_service import LLMService
        svc = LLMService()
        ai_narrative = await svc.generate_comparison_narrative(
            champ_metrics, chall_metrics, deltas, winners
        )
        res.ai_narrative = ai_narrative
    
    return APIResponse(success=True, data=res)
