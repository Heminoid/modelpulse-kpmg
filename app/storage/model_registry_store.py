import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from app.schemas.registry import RegisteredModel, ModelLifecycleStage

class ModelRegistryStore:
    def __init__(self, storage_dir: str = "storage"):
        self.registry_file = os.path.join(storage_dir, "models.json")
        os.makedirs(storage_dir, exist_ok=True)
        self._init_file()
        
    def _init_file(self):
        if not os.path.exists(self.registry_file):
            with open(self.registry_file, "w") as f:
                json.dump([], f)
                
    def _read(self) -> list[dict]:
        try:
            with open(self.registry_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
            
    def _write(self, data: list[dict]):
        with open(self.registry_file, "w") as f:
            json.dump(data, f, indent=2)
            
    def create(self, model_data: dict) -> RegisteredModel:
        models = self._read()
        model_id = f"model_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        
        # Enforce single champion
        is_champion = model_data.get("is_champion", False)
        if is_champion:
            for m in models:
                if m.get("is_champion"):
                    m["is_champion"] = False
                    
        new_model = {
            **model_data,
            "model_id": model_id,
            "linked_monitor_ids": [],
            "linked_run_ids": [],
            "registered_at": now,
            "updated_at": now,
            "promoted_to_production_at": now if model_data.get("lifecycle_stage") == ModelLifecycleStage.PRODUCTION.value else None
        }
        models.append(new_model)
        self._write(models)
        return RegisteredModel(**new_model)
        
    def get(self, model_id: str) -> Optional[RegisteredModel]:
        models = self._read()
        for m in models:
            if m["model_id"] == model_id:
                return RegisteredModel(**m)
        return None
        
    def list(self, skip: int = 0, limit: int = 20, stage: Optional[str] = None) -> tuple[list[RegisteredModel], int]:
        models = self._read()
        if stage:
            models = [m for m in models if m.get("lifecycle_stage") == stage]
            
        total = len(models)
        page = models[skip:skip+limit]
        return [RegisteredModel(**m) for m in page], total
        
    def update(self, model_id: str, update_data: dict) -> Optional[RegisteredModel]:
        models = self._read()
        target = None
        for i, m in enumerate(models):
            if m["model_id"] == model_id:
                target = m
                break
                
        if not target:
            return None
            
        is_champion = update_data.get("is_champion", target.get("is_champion"))
        if is_champion and not target.get("is_champion"):
            for m in models:
                m["is_champion"] = False
                
        # Handle promotion to production
        if update_data.get("lifecycle_stage") == ModelLifecycleStage.PRODUCTION.value and target.get("lifecycle_stage") != ModelLifecycleStage.PRODUCTION.value:
            update_data["promoted_to_production_at"] = datetime.now(timezone.utc).isoformat()
            
        target.update({k: v for k, v in update_data.items() if v is not None})
        target["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        self._write(models)
        return RegisteredModel(**target)
        
    def delete(self, model_id: str) -> bool:
        models = self._read()
        initial_len = len(models)
        models = [m for m in models if m["model_id"] != model_id]
        if len(models) < initial_len:
            self._write(models)
            return True
        return False
        
    def link_run(self, model_id: str, run_id: str) -> Optional[RegisteredModel]:
        models = self._read()
        target = None
        for m in models:
            if m["model_id"] == model_id:
                target = m
                break
                
        if not target:
            return None
            
        if "linked_run_ids" not in target:
            target["linked_run_ids"] = []
            
        if run_id not in target["linked_run_ids"]:
            target["linked_run_ids"].append(run_id)
            target["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write(models)
            
        return RegisteredModel(**target)
        
    def get_champion(self) -> Optional[RegisteredModel]:
        models = self._read()
        for m in models:
            if m.get("is_champion"):
                return RegisteredModel(**m)
        return None
