import uuid
import time
import pandas as pd
from datetime import datetime, timezone
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

from app.core.exceptions import MonitorNotFoundError
from app.storage.run_store import MonitorRunStore
from app.storage.monitor_store import MonitorConfigStore
from app.storage.dataset_store import DatasetStore
from app.schemas.runs import RunMetadata
from app.metrics.engine import run_metrics
from app.metrics.segmentation import compute_segments
from app.alerts.engine import evaluate_alerts
from app.insights.engine import generate_deterministic_findings, build_insight_context
from app.health.scorer import compute_health_score
from app.baseline.builder import build_baseline_stats
from app.storage.base import save_json, load_json
import os

from app.core.config import settings

run_store = MonitorRunStore(settings.runs_dir)
monitor_store = MonitorConfigStore(settings.monitor_configs_dir)
dataset_store = DatasetStore(settings.uploads_dir)


def _get_or_compute_baseline(dataset_id: str, mapping) -> "BaselineStats":
    profile_path = Path(f"storage/profiles/{dataset_id}_baseline_stats.json")
    if profile_path.exists():
        data = load_json(profile_path)
        from app.schemas.baseline import BaselineStats
        return BaselineStats(**data)
        
    import pandas as pd
    df = pd.read_csv(settings.uploads_dir / f"{dataset_id}.csv")
    stats = build_baseline_stats(dataset_id, df, mapping)
    save_json(profile_path, stats.model_dump())
    return stats


def execute_run(monitor_id: str) -> RunMetadata:
    """Executes a monitor run synchronously."""
    
    # 1. Load config
    monitor = monitor_store.get(monitor_id)
    if not monitor:
        raise MonitorNotFoundError(f"Monitor {monitor_id} not found")
        
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    
    # Create PENDING run
    meta = RunMetadata(
        run_id=run_id,
        monitor_id=monitor_id,
        dataset_id=monitor.get("dataset_id"),
        baseline_dataset_id=monitor.get("baseline_dataset_id"),
        status="pending",
        created_at=datetime.now(timezone.utc)
    )
    run_store.create(meta.model_dump())
    
    # Update to RUNNING
    meta.status = "running"
    meta.started_at = datetime.now(timezone.utc)
    run_store.update(run_id, meta.model_dump())
    
    start_time = time.time()
    
    try:
        # Load dataset
        df = dataset_store.get_dataframe(monitor.get("dataset_id")) if hasattr(dataset_store, "get_dataframe") else None
        if not df is not None:
            import pandas as pd
            df = pd.read_csv(settings.uploads_dir / f"{monitor.get('dataset_id')}.csv")
            
        meta.row_count = len(df)
        
        # Load or compute baseline
        baseline_stats = None
        from app.schemas.mapping import ColumnMapping
        if monitor.get("baseline_dataset_id"):
            baseline_stats = _get_or_compute_baseline(monitor.get("baseline_dataset_id"), ColumnMapping(**monitor.get("column_mapping")))
            meta.baseline_row_count = baseline_stats.row_count
            
        # Metric Engine
        baseline_df = None
        if monitor.get("baseline_dataset_id"):
            baseline_df = pd.read_csv(settings.uploads_dir / f"{monitor.get('baseline_dataset_id')}.csv")
            
        # Metrics
        from app.metrics.registry import MetricRegistry
        metric_keys = monitor.get("selected_metrics") or [m.metric_key for m in MetricRegistry.get_all()]
        metric_results = run_metrics(
            df=df,
            mapping=ColumnMapping(**monitor.get("column_mapping")),
            metric_keys=metric_keys,
            baseline_df=baseline_df
        )
        
        # Update run tracking
        for r in metric_results:
            if r.status == "skipped":
                meta.metrics_skipped.append(r.metric_key)
            elif r.status == "error":
                meta.metrics_failed.append(r.metric_key)
            else:
                meta.metrics_computed.append(r.metric_key)
                
        # Segmentation
        segments = compute_segments(df, ColumnMapping(**monitor.get("column_mapping")), monitor.get("selected_segments") or [], baseline_stats)
        
        # Alerts
        alerts = evaluate_alerts(run_id, metric_results, monitor.get("thresholds") or {}, baseline_stats)
        
        # Insights
        findings = generate_deterministic_findings(metric_results, alerts, segments)
        context = build_insight_context(
            run_id=run_id,
            monitor_name=monitor.get("name"),
            template_type=monitor.get("template_type"),
            dataset_rows=len(df),
            has_baseline=baseline_stats is not None,
            results=metric_results,
            segments=segments,
            alerts=alerts,
            findings=findings
        )
        
        # Health Score
        health = compute_health_score(metric_results)
        
        # Charts
        from app.charts.builder import build_charts
        charts = build_charts(df, ColumnMapping(**monitor.get("column_mapping")), metric_results, baseline_stats)
        
        # Advanced Modules
        from app.metrics.implementations.statistical_tests import run_statistical_tests
        stat_tests = run_statistical_tests(df, ColumnMapping(**monitor.get("column_mapping")), baseline_stats)
        
        from app.metrics.implementations.vintage import run_vintage_analysis
        vintage_analysis = run_vintage_analysis(df, ColumnMapping(**monitor.get("column_mapping")))
        
        from app.metrics.implementations.override import run_override_analysis_all
        override_analysis = run_override_analysis_all(df, ColumnMapping(**monitor.get("column_mapping")))
        
        from app.metrics.implementations.fairness import run_fairness_analysis
        fairness_analysis = run_fairness_analysis(df, ColumnMapping(**monitor.get("column_mapping")), ["income_band", "home_ownership", "loan_purpose"])
        
        from app.services.timeseries_service import TimeSeriesService
        timeseries_analysis = TimeSeriesService().analyze(df, ColumnMapping(**monitor.get("column_mapping")))
        
        # Save artifacts
        run_store.save_artifact(run_id, "metrics.json", [r.model_dump() for r in metric_results])
        run_store.save_artifact(run_id, "segments.json", [s.model_dump() for s in segments])
        run_store.save_artifact(run_id, "alerts.json", [a.model_dump() for a in alerts])
        run_store.save_artifact(run_id, "insights.json", context.model_dump())
        run_store.save_artifact(run_id, "health.json", health.model_dump())
        run_store.save_artifact(run_id, "charts.json", [c.model_dump() for c in charts])
        run_store.save_artifact(run_id, "stat_tests.json", stat_tests.model_dump())
        run_store.save_artifact(run_id, "vintage.json", vintage_analysis.model_dump())
        run_store.save_artifact(run_id, "override.json", {k: v.model_dump() for k, v in override_analysis.items()})
        run_store.save_artifact(run_id, "fairness.json", fairness_analysis.model_dump())
        run_store.save_artifact(run_id, "timeseries.json", timeseries_analysis)
        
        # Complete
        meta.status = "completed"
        
    except Exception as e:
        import traceback; traceback.print_exc()
        meta.status = "failed"
        meta.error_message = str(e)
        
    meta.completed_at = datetime.now(timezone.utc)
    if meta.started_at:
        meta.duration_seconds = (meta.completed_at - meta.started_at).total_seconds()
        
    run_store.update(run_id, meta.model_dump())
    return meta
