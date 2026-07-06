from app.schemas.health import HealthScore
from app.schemas.metrics import MetricResult

HEALTH_WEIGHTS = {
    "perf_gini":           0.25,
    "perf_ks":             0.20,
    "psi_prediction_score":     0.20,
    "calib_ratio_overall": 0.20,
    "perf_auc":            0.15,
}

def compute_health_score(results: list[MetricResult]) -> HealthScore:
    """Computes composite health score using corrected lambdas."""
    
    # Need to map calib_summary to calib_ratio_overall 
    # since metric_key is calib_summary but weight is calib_ratio_overall
    
    scorers = {
        "perf_gini":           lambda v: min(100.0, max(0.0, v / 0.7 * 100)),
        "perf_ks":             lambda v: min(100.0, max(0.0, v / 0.5 * 100)),
        "psi_prediction_score":     lambda v: max(0.0, 100.0 - (v / 0.25) * 100),
        "calib_ratio_overall": lambda v: max(0.0, 100.0 - abs(1.0 - v) * 200),
        "perf_auc":            lambda v: min(100.0, max(0.0, (v - 0.5) / 0.3 * 100)),
    }
    
    components = {}
    total_weight = 0.0
    weighted_score_sum = 0.0
    
    for r in results:
        key = r.metric_key
        if key == "calib_summary":
            key = "calib_ratio_overall"
            
        if key in HEALTH_WEIGHTS and r.scalar_value is not None:
            scorer = scorers.get(key)
            if scorer:
                c_score = scorer(r.scalar_value)
                weight = HEALTH_WEIGHTS[key]
                total_weight += weight
                weighted_score_sum += c_score * weight
                
                c_status = "healthy"
                if c_score < 35: c_status = "critical"
                elif c_score < 55: c_status = "deteriorating"
                elif c_score < 75: c_status = "watch"
                
                components[key] = {
                    "score": float(c_score),
                    "weight": weight,
                    "status": c_status
                }
                
    if total_weight > 0:
        final_score = weighted_score_sum / total_weight
    else:
        final_score = 0.0
        
    status = "healthy"
    if final_score < 35: status = "critical"
    elif final_score < 55: status = "deteriorating"
    elif final_score < 75: status = "watch"
    
    return HealthScore(
        score=float(final_score),
        status=status,
        components=components,
        recommended_actions=[]
    )
