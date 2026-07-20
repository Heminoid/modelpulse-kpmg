"""Base storage utilities for filesystem-based JSON persistence."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def generate_id(prefix: str = "") -> str:
    """Generate a unique identifier with optional prefix.

    Format: {prefix}_{YYYYMMDD}_{12-char-hex} or {YYYYMMDD}_{12-char-hex}
    """
    uid = str(uuid.uuid4()).replace("-", "")[:12]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{prefix}_{ts}_{uid}" if prefix else f"{ts}_{uid}"


def save_json(path: Path, payload: Any) -> None:
    """Persist a JSON-serializable object to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=str)


def load_json(path: Path) -> Any:
    """Load a JSON file from disk.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"Not found: {path}")
    with open(path, "r") as f:
        return json.load(f)


def list_json_objects(folder: Path) -> list[dict]:
    """List all JSON objects in a folder, sorted newest-first by filename."""
    if not folder.exists():
        return []
    return [load_json(p) for p in sorted(folder.glob("*.json"), reverse=True)]


def path_exists(path: Path) -> bool:
    """Check whether a path exists."""
    return path.exists()
