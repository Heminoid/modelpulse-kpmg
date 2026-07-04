"""Metric registry for tracking all available metrics."""

from __future__ import annotations

from typing import Iterable

from app.schemas.metrics import MetricDefinition


class MetricRegistry:
    """Singleton registry tracking all MetricDefinitions."""

    _registry: dict[str, MetricDefinition] = {}

    @classmethod
    def register(cls, definition: MetricDefinition) -> None:
        """Register a new metric definition."""
        cls._registry[definition.metric_key] = definition

    @classmethod
    def get(cls, key: str) -> MetricDefinition | None:
        """Retrieve a metric by key."""
        return cls._registry.get(key)

    @classmethod
    def get_all(cls) -> list[MetricDefinition]:
        """List all registered metrics."""
        return list(cls._registry.values())

    @classmethod
    def get_by_category(cls, category: str) -> list[MetricDefinition]:
        """List metrics belonging to a specific category."""
        return [m for m in cls._registry.values() if m.category == category]

    @classmethod
    def can_run(cls, key: str, available_roles: set[str]) -> bool:
        """Check if the necessary mapped roles are present for this metric."""
        metric = cls.get(key)
        if not metric:
            return False
        return all(r in available_roles for r in metric.required_roles)


def register_metric(definition: MetricDefinition) -> None:
    """Module-level helper to register a metric."""
    MetricRegistry.register(definition)
