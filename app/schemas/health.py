from pydantic import BaseModel, ConfigDict


class HealthScore(BaseModel):
    model_config = ConfigDict(ser_json_timedelta="iso8601")

    score: float               # 0-100 (100 = perfect health)
    status: str                # "healthy", "watch", "deteriorating", "critical"
    components: dict           # {metric_key: {"score": 0-100, "weight": float, "status": str}}
    recommended_actions: list[str] = []
