"""Filesystem-backed store for monitor run metadata and artifacts."""

import shutil
from pathlib import Path
from typing import Optional

from loguru import logger

from app.storage.base import generate_id, load_json, save_json


class MonitorRunStore:
    """CRUD operations for monitor run metadata.

    Each run gets its own directory under runs_dir/{run_id}/ containing
    run_metadata.json and various artifact JSON files.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _run_dir(self, run_id: str) -> Path:
        return self.root / run_id

    def _metadata_path(self, run_id: str) -> Path:
        return self._run_dir(run_id) / "run_metadata.json"

    def create(self, run: dict) -> dict:
        """Create a new run record."""
        run_id = run.get("run_id") or run.get("id") or generate_id("run")
        run["run_id"] = run_id
        if "id" in run:
            run["id"] = run_id
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        save_json(self._metadata_path(run_id), run)
        logger.info("Created run {}", run_id)
        return run

    def get(self, run_id: str) -> Optional[dict]:
        """Retrieve run metadata by ID, or None if not found."""
        path = self._metadata_path(run_id)
        if not path.exists():
            return None
        return load_json(path)

    def list(
        self, page: int = 1, limit: int = 20, monitor_id: Optional[str] = None
    ) -> tuple[list[dict], int]:
        """List runs with pagination and optional monitor_id filter.

        The monitor_id filter applies before pagination (Amendment B8).
        Returns (page_items, total_count).
        """
        all_items = []
        if self.root.exists():
            for run_dir in self.root.iterdir():
                meta_path = run_dir / "run_metadata.json"
                if run_dir.is_dir() and meta_path.exists():
                    item = load_json(meta_path)
                    if monitor_id is None or item.get("monitor_id") == monitor_id:
                        all_items.append(item)
        # Sort by actual creation time, newest first — run_id is a random
        # hex string, so sorting by directory name (as this used to do) put
        # runs in an order unrelated to recency, making new runs appear to
        # "disappear" off page 1 as soon as there were more than `limit` runs.
        all_items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        total = len(all_items)
        start = (page - 1) * limit
        end = start + limit
        return all_items[start:end], total

    def update(self, run_id: str, updates: dict) -> Optional[dict]:
        """Update run metadata."""
        existing = self.get(run_id)
        if existing is None:
            return None
        existing.update(updates)
        existing["run_id"] = run_id
        save_json(self._metadata_path(run_id), existing)
        logger.info("Updated run {}", run_id)
        return existing

    def exists(self, run_id: str) -> bool:
        """Check whether a run exists."""
        return self._metadata_path(run_id).exists()

    def delete(self, run_id: str) -> bool:
        """Delete a run and all its artifacts."""
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            return False
        shutil.rmtree(run_dir)
        logger.info("Deleted run {} and all artifacts", run_id)
        return True

    def save_artifact(self, run_id: str, artifact_name: str, data: dict) -> None:
        """Save a run artifact JSON file (e.g. metrics.json, charts.json)."""
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        save_json(run_dir / artifact_name, data)

    def load_artifact(self, run_id: str, artifact_name: str) -> Optional[dict]:
        """Load a run artifact JSON file."""
        path = self._run_dir(run_id) / artifact_name
        if not path.exists():
            return None
        return load_json(path)
