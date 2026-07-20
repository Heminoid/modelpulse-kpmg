"""Filesystem-backed store for column mapping configurations."""

from pathlib import Path
from typing import Optional

from loguru import logger

from app.storage.base import generate_id, load_json, list_json_objects, save_json


class MappingStore:
    """CRUD operations for column mapping JSON files."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, mapping_id: str) -> Path:
        return self.root / f"{mapping_id}.json"

    def create(self, mapping: dict) -> dict:
        """Create a new mapping record."""
        mapping_id = mapping.get("id") or generate_id("map")
        mapping["id"] = mapping_id
        save_json(self._path(mapping_id), mapping)
        logger.info("Created mapping {}", mapping_id)
        return mapping

    def get(self, mapping_id: str) -> Optional[dict]:
        """Retrieve a mapping by ID, or None if not found."""
        path = self._path(mapping_id)
        if not path.exists():
            return None
        return load_json(path)

    def get_by_dataset(self, dataset_id: str) -> Optional[dict]:
        """Retrieve a mapping by its associated dataset ID."""
        all_items = list_json_objects(self.root)
        for item in all_items:
            if item.get("dataset_id") == dataset_id:
                return item
        return None

    def list(self, page: int = 1, limit: int = 20) -> tuple[list[dict], int]:
        """List mappings with pagination. Returns (page_items, total_count)."""
        all_items = list_json_objects(self.root)
        total = len(all_items)
        start = (page - 1) * limit
        end = start + limit
        return all_items[start:end], total

    def update(self, mapping_id: str, updates: dict) -> Optional[dict]:
        """Update an existing mapping record."""
        existing = self.get(mapping_id)
        if existing is None:
            return None
        existing.update(updates)
        existing["id"] = mapping_id
        save_json(self._path(mapping_id), existing)
        logger.info("Updated mapping {}", mapping_id)
        return existing

    def exists(self, mapping_id: str) -> bool:
        """Check whether a mapping exists."""
        return self._path(mapping_id).exists()

    def delete(self, mapping_id: str) -> bool:
        """Delete a mapping. Returns True if deleted, False if not found."""
        path = self._path(mapping_id)
        if not path.exists():
            return False
        path.unlink()
        logger.info("Deleted mapping {}", mapping_id)
        return True
