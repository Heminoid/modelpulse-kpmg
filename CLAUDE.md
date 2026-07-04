# ModelPulse — FastAPI POC backend for credit risk model monitoring

Filesystem-persisted (JSON) monitoring platform: upload CSV → profile → map column
roles → create monitor → run → metrics/segments/alerts/charts/findings/reports.

## Source of truth
- `docs/SPEC.md` — full functional spec (v3). Read the relevant section before
  implementing a module; do NOT hold the whole file in context.
- `docs/SPEC_AMENDMENTS.md` — **overrides SPEC.md wherever they conflict.**
  Read it in full before starting any phase. It resolves duplicated/contradictory
  sections and fixes known formula bugs in the spec's sample code.
- `docs/BUILD_PLAN.md` — phase order and exit criteria. Build one phase at a
  time; never start a phase before the previous phase's verification passes.

## Commands
- Setup: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Run: `uvicorn main:app --reload --port 8000`
- Verify: `python scripts/smoke_test.py` (server must be running)
- Generate test data: `python scripts/generate_demo_data.py` (seeded)
- Validation contract: `docs/VALIDATION_MATRIX.md` — 5 controls (negative /
  positive / drift / agnostic / adversarial) with pinned numbers in
  `scripts/expected_values*.py`. Red on the positive control = platform bug.

## Hard rules (non-negotiable)
1. **Dataset-agnostic.** No literal column name (e.g. `"model_score"`) anywhere
   except `app/mapping/heuristics.py` vocab lists and demo/test scripts. All
   data access goes through the resolved `ColumnMapping` roles.
2. **Metrics gate on roles, not columns.** If a required role isn't mapped, the
   metric returns `status="skipped"` with a reason — never raises.
3. **Charts: JSON first.** Metric code produces `ChartPayload` only. matplotlib
   appears ONLY in `app/charts/renderer.py`, with `matplotlib.use("Agg")` as the
   first matplotlib line in the module. The renderer consumes `ChartPayload`
   exclusively — never DataFrames, never storage. `plt.close(fig)` after every render.
4. **Pydantic v2 only.** `model_config = ConfigDict(...)`. Every `Optional[X]`
   field MUST have an explicit `= None` default. Import `Field` where used.
5. **Timestamps:** `datetime.now(timezone.utc)` — never `datetime.utcnow()`.
6. **Every endpooint** returns the `APIResponse`/`PaginatedResponse` envelope,
   except binary image/file endpoints (raw bytes + correct Content-Type).
7. **No** database, Docker, Celery/Redis, auth, CI, or async DB libs. All
   computation synchronous. Persistence = JSON files under `storage/` via the
   store classes in `app/storage/`.
8. **Graceful data handling.** Bad input → 4xx with clear message, never a 500.
   Known sample-data quirks (malformed `application_time`, truncated `VERY_HIG`
   / `MORTGAG`, 50 DPD, 11 bads) produce warnings/findings, never crashes.
9. **Imports:** absolute (`from app.services...`), grouped stdlib → third-party
   → internal. Logging via loguru at service entry/exit and metric skip/fail.
10. Keep files focused; if a module exceeds ~400 lines, split it.

## Verification discipline
After completing each phase: start the server, run `scripts/smoke_test.py`
through the highest phase implemented, and fix failures before moving on.
When you change a schema, grep for its usages and update all callers in the
same turn.
