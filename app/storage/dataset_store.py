"""Filesystem-backed store for dataset metadata."""

from pathlib import Path
from typing import Optional

from loguru import logger

from app.storage.base import generate_id, load_json, list_json_objects, save_json


class DatasetStore:
    """CRUD operations for dataset metadata JSON files."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, dataset_id: str) -> Path:
        return self.root / f"{dataset_id}.json"

    def create(self, dataset: dict) -> dict:
        """Create a new dataset record."""
        dataset_id = dataset.get("id") or generate_id("ds")
        dataset["id"] = dataset_id
        path = self._path(dataset_id)
        save_json(path, dataset)
        logger.info("Created dataset {}", dataset_id)
        return dataset

    def get(self, dataset_id: str) -> Optional[dict]:
        """Retrieve a dataset by ID, or None if not found."""
        path = self._path(dataset_id)
        if not path.exists():
            return None
        return load_json(path)

    def list(self, page: int = 1, limit: int = 20) -> tuple[list[dict], int]:
        """List datasets with pagination. Returns (page_items, total_count)."""
        all_items = list_json_objects(self.root)
        total = len(all_items)
        start = (page - 1) * limit
        end = start + limit
        return all_items[start:end], total

    def update(self, dataset_id: str, updates: dict) -> Optional[dict]:
        """Update an existing dataset record. Returns updated record or None."""
        existing = self.get(dataset_id)
        if existing is None:
            return None
        existing.update(updates)
        existing["id"] = dataset_id  # Prevent ID overwrite
        save_json(self._path(dataset_id), existing)
        logger.info("Updated dataset {}", dataset_id)
        return existing

    def exists(self, dataset_id: str) -> bool:
        """Check whether a dataset exists."""
        return self._path(dataset_id).exists()

    def delete(self, dataset_id: str) -> bool:
        """Delete a dataset. Returns True if deleted, False if not found."""
        path = self._path(dataset_id)
        if not path.exists():
            return False
        path.unlink()
        logger.info("Deleted dataset {}", dataset_id)
        return True
