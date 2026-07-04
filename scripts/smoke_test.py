#!/usr/bin/env python3
"""
smoke_test.py — end-to-end acceptance tests against a running ModelPulse server.

Usage:
    python scripts/smoke_test.py [--phase N] [--base-url URL]

Requires the server to be running (uvicorn main:app --port 8000).
Grows with each build phase. Exit non-zero on any failure.
"""

from __future__ import annotations

import argparse
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Ensure the project root is on sys.path so we can import app.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import httpx

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
PASS = 0
FAIL = 0
BASE_URL = "http://localhost:8000"


def check(label: str, condition: bool, detail: str = "") -> None:
    """Record a pass/fail check."""
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        msg = f"  ❌ {label}"
        if detail:
            msg += f"  — {detail}"
        print(msg)


def heading(text: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Phase 1: Foundation
# ---------------------------------------------------------------------------
def phase_1(client: httpx.Client) -> None:
    heading("Phase 1 — Foundation")

    # --- Health endpoint ---
    print("\n[Health endpoint]")
    r = client.get(f"{BASE_URL}/api/v1/health")
    check("GET /api/v1/health returns 200", r.status_code == 200)

    body = r.json()
    check("Response has success=True", body.get("success") is True)
    check("Response has timestamp", "timestamp" in body)
    check("Data contains status=ok", body.get("data", {}).get("status") == "ok")
    check(
        "Data contains app_name",
        body.get("data", {}).get("app_name") == "ModelPulse API",
    )
    check("Data contains version", "version" in body.get("data", {}))

    # --- Store round-trip (via direct Python import, not HTTP) ---
    print("\n[Store round-trip]")
    try:
        # Use a temp directory so we don't pollute real storage
        tmpdir = Path(tempfile.mkdtemp(prefix="mp_smoke_"))
        try:
            from app.storage.dataset_store import DatasetStore

            store = DatasetStore(tmpdir / "datasets")

            # Create
            created = store.create({"name": "test_dataset", "rows": 42})
            ds_id = created["id"]
            check("Store create returns id", ds_id is not None)

            # Get
            fetched = store.get(ds_id)
            check(
                "Store get returns same record",
                fetched is not None and fetched["name"] == "test_dataset",
            )

            # List
            items, total = store.list()
            check("Store list returns items", len(items) == 1 and total == 1)

            # Update
            updated = store.update(ds_id, {"rows": 99})
            check(
                "Store update modifies field",
                updated is not None and updated["rows"] == 99,
            )

            # Exists
            check("Store exists returns True", store.exists(ds_id))

            # Delete
            deleted = store.delete(ds_id)
            check("Store delete returns True", deleted is True)
            check("Store exists returns False after delete", not store.exists(ds_id))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    except Exception as e:
        check(f"Store round-trip (exception: {e})", False)

    # --- CORS header check ---
    print("\n[CORS middleware]")
    r = client.options(
        f"{BASE_URL}/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    cors_header = r.headers.get("access-control-allow-origin", "")
    check("CORS allows origin", cors_header == "*" or cors_header == "http://localhost:3000")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    global PASS, FAIL

    parser = argparse.ArgumentParser(description="ModelPulse smoke tests")
    parser.add_argument(
        "--phase", type=int, default=99, help="Run checks up to this phase"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8000",
        help="Server base URL",
    )
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = args.base_url

    client = httpx.Client(timeout=30.0)

    # Verify server is reachable
    try:
        client.get(f"{BASE_URL}/api/v1/health")
    except httpx.ConnectError:
        print(f"❌ Cannot connect to {BASE_URL} — is the server running?")
        sys.exit(1)

    if args.phase >= 1:
        phase_1(client)

    # Summary
    total = PASS + FAIL
    heading(f"Results: {PASS}/{total} passed, {FAIL} failed")
    sys.exit(1 if FAIL > 0 else 0)


if __name__ == "__main__":
    main()
