"""Filesystem-backed store for monitor configurations."""

from pathlib import Path
from typing import Optional

from loguru import logger

from app.storage.base import generate_id, load_json, list_json_objects, save_json


class MonitorConfigStore:
    """CRUD operations for monitor configuration JSON files."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, monitor_id: str) -> Path:
        return self.root / f"{monitor_id}.json"

    def create(self, monitor: dict) -> dict:
        """Create a new monitor configuration."""
        monitor_id = monitor.get("id") or monitor.get("monitor_id") or generate_id("mon")
        monitor["id"] = monitor_id
        monitor["monitor_id"] = monitor_id
        save_json(self._path(monitor_id), monitor)
        logger.info("Created monitor {}", monitor_id)
        return monitor

    def get(self, monitor_id: str) -> Optional[dict]:
        """Retrieve a monitor by ID, or None if not found."""
        path = self._path(monitor_id)
        if not path.exists():
            return None
        return load_json(path)

    def list(self, page: int = 1, limit: int = 20) -> tuple[list[dict], int]:
        """List monitors with pagination. Returns (page_items, total_count)."""
        all_items = list_json_objects(self.root)
        total = len(all_items)
        start = (page - 1) * limit
        end = start + limit
        return all_items[start:end], total

    def update(self, monitor_id: str, updates: dict) -> Optional[dict]:
        """Update an existing monitor configuration."""
        existing = self.get(monitor_id)
        if existing is None:
            return None
        existing.update(updates)
        existing["id"] = monitor_id
        existing["monitor_id"] = monitor_id
        save_json(self._path(monitor_id), existing)
        logger.info("Updated monitor {}", monitor_id)
        return existing

    def exists(self, monitor_id: str) -> bool:
        """Check whether a monitor exists."""
        return self._path(monitor_id).exists()

    def delete(self, monitor_id: str) -> bool:
        """Delete a monitor. Returns True if deleted, False if not found."""
        path = self._path(monitor_id)
        if not path.exists():
            return False
        path.unlink()
        logger.info("Deleted monitor {}", monitor_id)
        return True
