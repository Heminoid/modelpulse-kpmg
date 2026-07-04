"""Metric execution engine."""

import pandas as pd
from loguru import logger

from app.metrics.base import build_skipped_result
from app.metrics.registry import MetricRegistry
from app.schemas.mapping import ColumnMapping
from app.schemas.metrics import MetricResult


def run_metrics(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    metric_keys: list[str],
    baseline_df: pd.DataFrame | None = None,
    baseline_stats: dict | None = None,
) -> list[MetricResult]:
    """Execute a list of metrics safely against a dataframe using the provided mapping.
    
    Any metric missing required roles is skipped. Exceptions within metrics
    are caught and result in an 'error' status.
    """
    results: list[MetricResult] = []

    # Reverse the mapping: role -> list of column names
    mapped_roles: dict[str, list[str]] = {}
    for col, role in mapping.mappings.items():
        mapped_roles.setdefault(role, []).append(col)

    available_roles = set(mapped_roles.keys())

    for key in metric_keys:
        definition = MetricRegistry.get(key)
        if not definition:
            logger.warning("Metric {} requested but not found in registry", key)
            continue

        # Check required roles
        missing_roles = [
            r for r in definition.required_roles if r not in available_roles
        ]
        if missing_roles:
            results.append(
                build_skipped_result(
                    metric_key=definition.metric_key,
                    display_name=definition.display_name,
                    category=definition.category,
                    reason=f"Missing required roles: {', '.join(missing_roles)}",
                )
            )
            continue

        # Execute metric
        try:
            result = definition.calculation_fn(
                df=df,
                mapped_roles=mapped_roles,
                mapping=mapping,
                baseline_df=baseline_df,
                baseline_stats=baseline_stats,
            )
            # Ensure the result carries the base metadata
            result.metric_key = definition.metric_key
            result.display_name = definition.display_name
            result.category = definition.category
            results.append(result)
        except Exception as e:
            logger.exception("Metric {} failed to execute", key)
            results.append(
                MetricResult(
                    metric_key=definition.metric_key,
                    display_name=definition.display_name,
                    category=definition.category,
                    status="error",
                    skipped_reason=f"Execution error: {str(e)}",
                )
            )

    return results
