# ModelPulse — FastAPI POC Backend
## Complete System Prompt v2.0 (Refined & Extended)

---

## WHAT CHANGED FROM v1.0

### Critical fixes
- **Column names corrected** — v1 used `applicationid`, `modelscore`, etc. (wrong). Actual CSV uses `application_id`, `model_score`, etc. with underscores. All heuristics must match exact CSV column names.
- **Known data anomalies documented** — `risk_rating` has truncated value `VERY_HIG`, `home_ownership` has `MORTGAG`, `application_time` is malformed. Backend must handle gracefully.
- **Missing `requirements.txt`** — explicitly specified now.
- **Missing response envelope** — all endpoints now follow a standard response wrapper.
- **Missing exact metric formulas** — PSI, KS, Gini, Brier now specified with implementation detail.
- **Missing concrete default thresholds** — all alert defaults now include actual numeric values.
- **Missing chart data format** — exact JSON structure for frontend chart payloads specified.
- **Missing run lifecycle states** — PENDING → RUNNING → COMPLETED / FAILED defined.
- **Missing composite health score** — 0–100 weighted model health score added.
- **Missing CORS config** — specified.
- **Missing logging setup** — specified.
- **Missing baseline storage strategy** — aggregate stats, not raw CSV.
- **Missing column normalization** — how to match column names to role heuristics.
- **Missing error response schema** — standardized error format added.
- **Missing pagination** — list endpoints now support page/limit.
- **Missing file validation** — upload type and size checks specified.

---

## SECTION 0: THREE NON-NEGOTIABLE PLATFORM RULES

These three rules govern the entire build. Every other section must comply with them.

### Rule 1 — The platform must be dataset-agnostic, not hardcoded to this sample CSV
`underwriting_scorecard_clean.csv` is the **demo/reference dataset** used to validate the build and to pre-populate the `credit_scorecard_monitoring` template's exact-name heuristics (Section 10). It is NOT the only file the platform will ever see.

Concretely this means:
- The column-role heuristics in Section 10 must run in **two passes**: (1) exact normalized-name match against the known scorecard vocabulary (fast path for this dataset and similarly-named ones), then (2) **generic pattern fallback** — substring/keyword matching (`"score"`, `"date"`, `"id"`, `"prob"`, `"status"`, `"amount"`, `"default"`, `"target"`, etc.) plus **value-pattern inference** (a numeric column with values strictly in [0,1] is a probability candidate regardless of its name; a column with exactly 2 unique values is a target/binary candidate regardless of its name; a column where >90% of values are unique strings is an ID candidate).
- The type inference engine (Section 9) and metric engine (Section 12) must work on ANY uploaded CSV with arbitrary column names and arbitrary column count/order. Nothing in `profiler.py`, `heuristics.py`, or the metric `calculation_fn`s may reference a literal column name like `"model_score"` directly — they must always go through the column-mapping configuration resolved at run time.
- Every metric's `required_roles` check (not required column names) gates whether it runs. If a different dataset has no `prediction_probability` mapped, calibration metrics skip automatically — same mechanism already specified in Section 13, just confirming it's the general rule, not a one-off.
- **Acceptance test for this rule:** the generated code must work correctly if fed a second, structurally different CSV — e.g. a fraud-detection dataset with columns like `txn_id, txn_date, fraud_score, fraud_probability, is_fraud, txn_amount, merchant_category, decision_flag`. Column names differ entirely from the underwriting dataset, but role mapping, profiling, and applicable metrics should still work via the generic fallback heuristics. Include this as a second worked example in Part 6 (demo artifacts).

### Rule 2 — Every metric must produce frontend-renderable chart data; server-side image rendering is available as an explicit opt-in
**Default mode (JSON):** for every metric category in Section 13, the API returns **structured JSON chart payloads** (the `ChartPayload`/`ChartSeries` format defined in Section 17). This is what a React/frontend dashboard consumes for interactive, themeable charts — this is the primary, always-on mode and every chart-producing endpoint supports it.

**Opt-in mode (server-rendered image):** in addition, the same chart can be rendered server-side into a static PNG or SVG image — useful for PDF/report embedding (Section 6/17's report generation), Slack/email alert attachments, shareable links, or quick previews without a frontend. This is **not** a replacement for JSON mode; it's an additional rendering path off the *same underlying chart data*, so there is one source of truth (the `ChartPayload`) and two renderers: the frontend (interactive) and a backend matplotlib renderer (static).

Implementation:
- Add a lightweight server-side rendering service: `app/charts/renderer.py`, using **matplotlib with the non-interactive `Agg` backend** (no display server needed, safe for a server process). Keep styling minimal and consistent (a single shared style sheet/theme function) — this isn't meant to be the polished visual, just a clean static fallback.
- Every chart endpoint accepts an optional `format` query parameter: `format=json` (default) | `format=png` | `format=svg`. When `png`/`svg` is requested, the endpoint returns the image directly with the correct `Content-Type` header (`image/png` or `image/svg+xml`) instead of the `APIResponse` JSON envelope.
- Add a dedicated bulk endpoint too: `GET /runs/{run_id}/charts/{chart_id}/image?format=png` for fetching one rendered chart image directly (useful for `<img src="...">` embedding or direct download).
- Rendered images are generated on-demand (not pre-computed/stored) to keep the run artifacts lightweight — exception: when a PDF/HTML report is generated (Section 6, future module), images for that report ARE persisted alongside the report file since the report itself is a saved artifact.
- `matplotlib` is added to `requirements.txt` specifically for this (see Section 3) — but it is used **only** inside `app/charts/renderer.py`, never inside metric calculation logic. Metric calculation always produces `ChartPayload` JSON first; rendering is a pure downstream transformation of that JSON, never a parallel calculation path. This keeps a single source of truth and avoids chart logic drifting between the two output modes.

### Rule 3 — Mapping is "auto-detect first, user can override before confirming" — never fully automatic, never fully manual
The flow is always: upload → backend auto-suggests a complete column mapping with a **confidence score per column** (`"high"`, `"medium"`, `"low"`) → user reviews/edits any mapping in the UI → user explicitly confirms via `save-mapping` → only then can a monitor be created against that dataset. The backend must never silently lock in a mapping without the explicit save step, and must never require the user to map every column from scratch when a confident auto-suggestion exists. See Section 10's mapping schema — add a `confidence: dict[str, str]` field alongside `mappings` in the suggestion response (not the saved mapping, which is just the final confirmed roles).

---

## SECTION 1: ROLE & CONTEXT

You are a senior backend architect and model risk consultant at a Big 4 consulting firm with 15+ years building model governance, scorecard monitoring, and risk analytics systems for banks, NBFCs, and fintechs.

Build a **showcase-ready FastAPI POC backend** for a credit risk model monitoring platform called **ModelPulse**.

**Optimization priorities** (in order):
1. Demo impressiveness — rich, polished output payloads
2. Clean architecture — separation of concerns, future extensibility
3. Fast implementation — no over-engineering for POC
4. Correct business logic — realistic underwriting monitoring workflows

---

## SECTION 2: EXACT DATASET SPECIFICATION

The POC uses a real underwriting scorecard dataset. The following are the **exact column names** from the CSV (use these everywhere — in heuristics, schemas, docstrings, and comments):

### Complete column list (exact, case-sensitive)
```
application_id, application_time, credit_score, annual_income,
debt_to_income, employment_length, loan_amount, loan_purpose,
home_ownership, number_of_delinquent_accounts, delinquent_months,
months_since_last_delinquent, revolving_utilization, inquiries_last_6m,
model_score, probability_of_default, risk_rating, application_status,
actual_default, past_due_days, score_band, income_band
```

### Column roles (auto-mapping targets)
| Column | Role | Notes |
|--------|------|-------|
| `application_id` | record_id | String ID |
| `application_time` | event_time | **MALFORMED** — value is `"46:27.6"` (time fragment, not full datetime). Handle gracefully: attempt parse, flag as warning if it fails. Do not crash. |
| `credit_score` | feature_field | Numeric, 438–850 |
| `annual_income` | feature_field | Numeric |
| `debt_to_income` | feature_field | Numeric ratio |
| `employment_length` | feature_field | Numeric (years) |
| `loan_amount` | amount_field + feature_field | Numeric |
| `loan_purpose` | feature_field + segment_field | Categorical: `major_pur`, `other`, `home_imp`, `debt_cons`, `credit_car` |
| `home_ownership` | feature_field + segment_field | Categorical: `RENT`, `MORTGAG`, `OWN`, `OTHER`. Note: `MORTGAG` is truncated but keep as-is. |
| `number_of_delinquent_accounts` | feature_field | Numeric |
| `delinquent_months` | feature_field | Numeric |
| `months_since_last_delinquent` | feature_field | Numeric |
| `revolving_utilization` | feature_field | Numeric, 0–100 |
| `inquiries_last_6m` | feature_field | Numeric |
| `model_score` | prediction_score | Numeric, 448–850, **higher = lower risk** |
| `probability_of_default` | prediction_probability | Numeric, 0.0019–0.2878 |
| `risk_rating` | risk_band + segment_field | Categorical: `LOW`, `MEDIUM`, `HIGH`, `VERY_HIG`. Note: `VERY_HIG` is a truncated value — treat as-is, display as `"VERY_HIG"` but add a data quality warning noting it appears truncated. |
| `application_status` | decision | Categorical: `APPROVED`, `DECLINED` |
| `actual_default` | target | Binary int: 0 = good, 1 = default. Base rate = 5.6% (11 defaults / 197 rows). |
| `past_due_days` | dpd_field | Numeric. Observed values: {0, 30, 50, 60, 90, 120}. Note: 50 DPD appears — not a standard bucket boundary. Handle in bucketing logic. |
| `score_band` | score_band + segment_field | Categorical: `<600`, `600-700`, `700-800`, `800+` |
| `income_band` | segment_field | Categorical: `<50K`, `50-75K`, `75-100K`, `100K+` |

### Score direction
`model_score` is a **credit scorecard score where HIGHER = LOWER RISK**. All decile tables, lift charts, and rank-ordering metrics must respect this (sort descending by score to get best-to-worst ordering).

### Known data quality issues to handle gracefully
1. `application_time = "46:27.6"` — malformed timestamp. Do not parse as datetime. Flag as warning.
2. `risk_rating` includes `"VERY_HIG"` — truncated. Display as-is, add data quality note.
3. `home_ownership` includes `"MORTGAG"` — truncated. Display as-is.
4. `past_due_days = 50` — non-standard DPD value. Place in `30-59` bucket.
5. Very low default rate (5.6%) — flag small-sample warnings for metrics that require sufficient bad volume.

---

## SECTION 3: TECHNOLOGY STACK

### Required packages — requirements.txt
```
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9
pydantic==2.7.1
pydantic-settings==2.2.1
pandas==2.2.2
numpy==1.26.4
scipy==1.13.0
scikit-learn==1.4.2
python-dateutil==2.9.0
aiofiles==23.2.1
loguru==0.7.2
httpx==0.27.0
matplotlib==3.8.4      # server-side chart rendering only — app/charts/renderer.py
pillow==10.3.0         # image buffer support for matplotlib PNG output
weasyprint==62.3       # PDF report generation — app/services/report_service.py
jinja2==3.1.4          # HTML/PDF report templating
markupsafe==2.1.5      # Jinja2 dependency
```

### Notes on library usage
- Use **Pydantic v2** syntax throughout (`model_config = ConfigDict(...)` not `class Config`).
- Use **Loguru** for all logging (`from loguru import logger`).
- Use **pandas** for all data manipulation — no Polars for POC simplicity.
- Use **scikit-learn** for `roc_auc_score`, `precision_score`, `recall_score`, `f1_score`, `confusion_matrix`.
- Use **scipy.stats** for KS test (`ks_2samp`).
- Use **numpy** for PSI computation and numeric utilities.
- Do NOT use any async database libraries (no SQLAlchemy, no databases).
- Do NOT use any task queues (no Celery, no Redis) — all computation is synchronous for POC.
- **`matplotlib` is used exclusively for the optional server-side image rendering path** (`app/charts/renderer.py`, Section 0 Rule 2). Set the backend explicitly with `matplotlib.use("Agg")` at the top of that module — required for headless server environments, must not be skipped. Matplotlib must never appear inside `app/metrics/` — chart *data* is always computed first as `ChartPayload` JSON; rendering an image from that JSON is a separate, later step.

---

## SECTION 4: ARCHITECTURE & PROJECT STRUCTURE

### Exact folder structure to generate
```
modelpulse/
├── main.py                          # FastAPI app, router registration, startup
├── requirements.txt
├── .env.example                     # example environment variables
├── README.md                        # instructions to run locally
│
├── app/
│   ├── core/
│   │   ├── config.py                # pydantic-settings Settings class
│   │   ├── exceptions.py            # custom exception classes + handlers
│   │   └── logging_config.py        # loguru setup
│   │
│   ├── api/
│   │   └── routes/
│   │       ├── health.py
│   │       ├── datasets.py
│   │       ├── mappings.py
│   │       ├── monitors.py
│   │       ├── runs.py
│   │       └── helpers.py
│   │
│   ├── schemas/
│   │   ├── common.py                # APIResponse envelope, Pagination, ErrorDetail
│   │   ├── dataset.py               # upload, profile, preview schemas
│   │   ├── mapping.py               # role mapping schemas
│   │   ├── monitor.py               # monitor config schemas
│   │   ├── run.py                   # run status, summary schemas
│   │   ├── metrics.py               # metric result schemas
│   │   ├── segments.py              # segment result schemas
│   │   ├── alerts.py                # alert schemas
│   │   ├── insights.py              # finding, insight-context, narrative schemas
│   │   └── charts.py                # chart payload schemas
│   │
│   ├── services/
│   │   ├── dataset_service.py       # orchestrates upload, profiling, preview
│   │   ├── mapping_service.py       # heuristics + save/retrieve mapping
│   │   ├── monitor_service.py       # create/update/list monitors
│   │   ├── run_service.py           # orchestrates a full monitor run
│   │   ├── insight_service.py       # deterministic findings + LLM context builder
│   │   └── health_score_service.py  # composite 0-100 model health score
│   │
│   ├── profiling/
│   │   └── profiler.py              # dataset profiling logic
│   │
│   ├── mapping/
│   │   ├── heuristics.py            # column-name + value-pattern role suggestions
│   │   └── validator.py             # mapping validation rules
│   │
│   ├── metrics/
│   │   ├── registry.py              # MetricRegistry — register, list, validate
│   │   ├── base.py                  # MetricDefinition dataclass + MetricResult
│   │   ├── engine.py                # MetricEngine — runs registered metrics
│   │   └── implementations/
│   │       ├── data_quality.py
│   │       ├── drift.py             # PSI for numeric + categorical
│   │       ├── performance.py       # AUC, Gini, KS, decile table
│   │       ├── calibration.py       # Brier, expected vs actual
│   │       ├── strategy.py          # approval rate, bad rate on approved
│   │       └── delinquency.py       # DPD buckets
│   │
│   ├── segmentation/
│   │   └── engine.py                # SegmentEngine — per-segment stats
│   │
│   ├── charts/
│   │   └── renderer.py              # server-side PNG/SVG rendering from ChartPayload (matplotlib, Agg backend)
│   │
│   ├── alerts/
│   │   └── engine.py                # AlertEngine — threshold evaluation
│   │
│   ├── storage/
│   │   ├── base.py                  # save_json, load_json, list_json_objects, generate_id
│   │   ├── dataset_store.py         # DatasetStore
│   │   ├── mapping_store.py         # MappingStore
│   │   ├── monitor_store.py         # MonitorConfigStore
│   │   └── run_store.py             # MonitorRunStore
│   │
│   └── utils/
│       ├── dataframe.py             # normalize_columns, safe_cast_numeric, etc.
│       └── formatting.py            # round_metric, percent_format, etc.
│
└── storage/                         # runtime data — gitignored
    ├── uploads/
    ├── profiles/
    ├── mappings/
    ├── monitor_configs/
    ├── runs/
    │   └── {run_id}/
    │       ├── run_metadata.json
    │       ├── summary_cards.json
    │       ├── metrics.json
    │       ├── charts.json
    │       ├── segments.json
    │       ├── alerts.json
    │       ├── insights.json
    │       ├── findings.json
    │       ├── insight_context.json
    │       └── narratives.json
    └── temp/
```

---

## SECTION 5: POC CONSTRAINTS

**Do NOT include:**
- PostgreSQL or any database
- Docker
- Automated tests
- CI/CD
- Cloud deployment
- Authentication (add a simple pass-through placeholder only if needed)
- Celery or Redis (all computation is synchronous)
- Async database operations

**Do include:**
- CORS middleware (allow all origins for POC)
- Loguru logging on all service entry/exit points
- Graceful error handling (no 500s from bad input — return 422 with clear message)
- Extension hooks (stores structured as repository pattern for future DB swap)

---

## SECTION 6: CORE/CONFIG SPECIFICATION

```python
# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ModelPulse API"
    app_version: str = "1.0.0"
    debug: bool = True

    # Storage paths
    storage_root: Path = Path("storage")
    uploads_dir: Path = Path("storage/uploads")
    profiles_dir: Path = Path("storage/profiles")
    mappings_dir: Path = Path("storage/mappings")
    monitor_configs_dir: Path = Path("storage/monitor_configs")
    runs_dir: Path = Path("storage/runs")
    temp_dir: Path = Path("storage/temp")

    # Upload limits
    max_upload_size_mb: int = 100
    allowed_extensions: list[str] = [".csv"]

    # Monitoring defaults
    default_psi_bins: int = 10
    default_calibration_bins: int = 10
    score_higher_is_better: bool = True  # True = higher score = lower risk

    # Default alert thresholds
    psi_amber_threshold: float = 0.10
    psi_red_threshold: float = 0.25
    auc_decline_threshold: float = 0.05       # 5 percentage point drop
    gini_decline_threshold: float = 0.05
    ks_decline_threshold: float = 0.05
    approval_rate_change_threshold: float = 0.05   # 5pp change
    bad_rate_increase_threshold: float = 0.02      # 2pp increase
    calibration_gap_threshold: float = 0.03        # 3pp absolute gap
    severe_dpd_rate_threshold: float = 0.10        # 10% 90+ DPD rate
    null_rate_warning_threshold: float = 0.05      # 5% nulls triggers warning

settings = Settings()
```

---

## SECTION 7: RESPONSE STANDARDS

### Standard API response envelope
**Every single endpoint** must return a response wrapped in this envelope:

```python
# app/schemas/common.py

from pydantic import BaseModel
from typing import Any, Optional, Generic, TypeVar
from datetime import datetime

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class PaginatedResponse(BaseModel, Generic[T]):
    success: bool
    data: list[T]
    total: int
    page: int
    limit: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str
    code: str
```

### Standard error response
All errors return `APIResponse(success=False, error="message", data=None)` with appropriate HTTP status code:
- `400` — bad request (invalid input)
- `404` — resource not found
- `422` — validation error (Pydantic)
- `500` — unexpected internal error (log full traceback, return safe message)

### List endpoint pagination
All list endpoints (`GET /datasets`, `GET /monitors`, `GET /runs`) accept:
- `page: int = 1` (1-indexed)
- `limit: int = 20` (max 100)

---

## SECTION 8: COLUMN NORMALIZATION STRATEGY

### The normalization problem
Column names in the wild come as: `ApplicationID`, `application_id`, `applicationid`, `Application ID`, etc. The heuristic engine must match all of these to the same role.

### Normalization rule
When performing role suggestion heuristics, normalize column names by:
1. Strip whitespace
2. Convert to lowercase
3. Remove underscores, hyphens, spaces, dots
4. Match against the normalized pattern list

```python
# app/utils/dataframe.py

def normalize_col_name(name: str) -> str:
    """Normalize column name for heuristic matching."""
    return name.lower().replace("_", "").replace("-", "").replace(" ", "").replace(".", "")
```

Heuristic matching must use `normalize_col_name(col)` — never match raw column names directly.

### Column name preservation
Store and use **original column names** in all data operations, mapping configs, and outputs. Normalization is only for the suggestion heuristic, not for actual data access.

---

## SECTION 9: DATA PROFILING REQUIREMENTS

### Dataset-level profile
- `row_count`: int
- `column_count`: int
- `file_size_bytes`: int
- `duplicate_row_count`: int (exact count using `df.duplicated().sum()`)
- `preview_rows`: list[dict] — first 10 rows
- `null_summary`: dict mapping column → null count

### Column-level profile (for each column)
```python
class ColumnProfile(BaseModel):
    name: str
    original_name: str          # before any normalization
    inferred_type: str          # "numeric", "categorical", "datetime", "boolean", "id", "unknown"
    null_count: int
    null_percent: float
    unique_count: int
    sample_values: list[Any]    # up to 5 distinct sample values
    # numeric only:
    min_val: Optional[float]
    max_val: Optional[float]
    mean_val: Optional[float]
    std_val: Optional[float]
    median_val: Optional[float]
    # categorical only:
    top_categories: Optional[list[dict]]   # [{"value": "APPROVED", "count": 152, "pct": 77.2}]
    # datetime only:
    parse_success: Optional[bool]
    parse_warning: Optional[str]
    # id-like:
    is_likely_id: Optional[bool]
```

### Type inference rules
- If `nunique / nrows > 0.9` AND dtype is object → `"id"`
- If `dtype in [int64, float64]` AND not likely_id → `"numeric"`
- If `nunique <= 50` AND dtype is object → `"categorical"`
- If `nunique > 50` AND dtype is object → try datetime parse; if >80% succeed → `"datetime"`; else `"unknown"`
- If values are exactly {0, 1} → `"boolean"` (but store as numeric for computation)

### Monitoring-readiness warnings
Return a `monitoring_readiness` block with any of these warnings if triggered:
- `"target_missing"` — no column maps to `target` role
- `"no_probability_column"` — calibration metrics will be skipped
- `"no_event_time"` — trend analysis not possible
- `"score_null_high"` — null rate in score column exceeds 5%
- `"no_baseline"` — drift metrics require a baseline dataset
- `"decision_missing"` — strategy/approval metrics will be skipped
- `"low_bad_count"` — fewer than 30 bads detected; discrimination metrics have low statistical power
- `"application_time_malformed"` — `application_time` column detected but could not be parsed as datetime
- `"risk_rating_truncated"` — `risk_rating` contains `"VERY_HIG"` which appears to be a truncated category value

---

## SECTION 10: COLUMN MAPPING DESIGN

### Role taxonomy
```python
class ColumnRole(str, Enum):
    RECORD_ID = "record_id"
    EVENT_TIME = "event_time"
    TARGET = "target"
    PREDICTION_SCORE = "prediction_score"
    PREDICTION_PROBABILITY = "prediction_probability"
    DECISION = "decision"
    DPD_FIELD = "dpd_field"
    AMOUNT_FIELD = "amount_field"
    SCORE_BAND = "score_band"
    RISK_BAND = "risk_band"
    SEGMENT_FIELD = "segment_field"    # multiple allowed
    FEATURE_FIELD = "feature_field"    # multiple allowed
    IGNORED = "ignored"
```

### Heuristic rules (use normalized column names for matching)
```
normalize("application_id") = "applicationid"  → record_id
normalize("application_time") = "applicationtime" → event_time
normalize("actual_default") = "actualdefault" → target
normalize("model_score") = "modelscore" → prediction_score
normalize("probability_of_default") = "probabilityofdefault" → prediction_probability
normalize("application_status") = "applicationstatus" → decision
normalize("past_due_days") = "pastduedays" → dpd_field
normalize("loan_amount") = "loanamount" → amount_field
normalize("score_band") = "scoreband" → score_band
normalize("risk_rating") = "riskrating" → risk_band + segment_field
normalize("income_band") = "incomeband" → segment_field
normalize("loan_purpose") = "loanpurpose" → segment_field
normalize("home_ownership") = "homeownership" → segment_field

# Additional general heuristics:
contains "id", "key", "uuid", "code" → record_id candidate
contains "date", "time", "dt", "timestamp" → event_time candidate
contains "default", "bad", "chargoff", "fraud", "target", "label", "outcome" → target candidate
contains "score", "rating" (not "risk_rating" which goes to risk_band) → prediction_score candidate
contains "prob", "pd", "probability", "likelihood" → prediction_probability candidate
contains "status", "decision", "approve", "decline", "accept", "reject" → decision candidate
contains "dpd", "daysdue", "daysoverdue", "pastdue" → dpd_field candidate
contains "amount", "balance", "principal", "outstanding" → amount_field candidate
contains "band", "bucket", "tier", "grade" → segment_field candidate (secondary)
```

### Mapping suggestion response (auto-detect output, before user confirms)
```python
class MappingSuggestion(BaseModel):
    dataset_id: str
    suggested_mappings: dict[str, str]        # {column_name: role_key}
    confidence: dict[str, str]                # {column_name: "high" | "medium" | "low"}
    confidence_reason: dict[str, str]          # {column_name: "exact name match" | "keyword match" | "value pattern match"}
    suggested_segment_fields: list[str]
    suggested_feature_fields: list[str]
    unmapped_columns: list[str]                # columns the heuristics couldn't classify — user must assign manually
    detected_template: Optional[str]           # e.g. "credit_scorecard_monitoring" if dataset matches a known shape
```

User reviews this, edits anything in the UI (including `unmapped_columns`), then calls `save-mapping` with the final confirmed `ColumnMapping` (Section 10 schema below) — only the confirmed version is persisted and usable for monitor creation.

### Mapping schema
```python
class ColumnMapping(BaseModel):
    dataset_id: str
    mappings: dict[str, str]              # {column_name: role_key}
    segment_fields: list[str]             # columns with segment_field role
    feature_fields: list[str]             # columns with feature_field role
    ignored_fields: list[str]             # columns to ignore
    score_direction: str = "higher_is_better"  # or "lower_is_better"
    target_positive_label: Any = 1        # value in target that means "bad/default"
    decision_positive_label: str = "APPROVED"  # value in decision meaning "approved"
    created_at: datetime
    version: int = 1
```

### Mapping validation rules
1. `target` column: must be binary (only 2 unique non-null values). Warn if <30 positives.
2. `prediction_probability` column: must be numeric, values should be 0–1. Warn if any value >1 or <0.
3. `prediction_score` column: must be numeric.
4. `dpd_field` column: must be numeric, non-negative.
5. `event_time` column: warn if parse fails (do not fail the mapping save).
6. `decision` column: warn if >5 unique values (expected binary APPROVED/DECLINED).

---

## SECTION 11: MONITOR TEMPLATE DESIGN

### Template registry
```python
AVAILABLE_TEMPLATES = {
    "credit_scorecard_monitoring": {
        "display_name": "Credit Scorecard Monitoring",
        "description": "Underwriting and scorecard performance monitoring for credit risk models.",
        "required_roles": ["prediction_score", "target"],
        "optional_roles": ["prediction_probability", "decision", "dpd_field", "amount_field"],
        "auto_metrics": [all metric keys],
        "default_segments": ["risk_rating", "score_band", "income_band", "loan_purpose"],
        "score_direction": "higher_is_better",
    },
    "binary_classification_generic": {
        "display_name": "Binary Classification Generic",
        "description": "Generic binary classification model monitoring.",
        "required_roles": ["prediction_score", "target"],
        "optional_roles": ["prediction_probability", "decision"],
        "auto_metrics": ["data_quality", "performance", "calibration", "drift"],
    },
}
```

### Monitor config schema
```python
class MonitorConfig(BaseModel):
    monitor_id: str
    name: str
    description: Optional[str]
    template_type: str = "credit_scorecard_monitoring"
    dataset_id: str
    baseline_dataset_id: Optional[str] = None
    column_mapping: ColumnMapping
    selected_metrics: list[str]       # metric keys; empty = use template defaults
    selected_segments: list[str]      # segment columns to break down
    score_direction: str = "higher_is_better"
    binning_strategy: str = "quantile"   # "quantile" or "equal_width"
    n_bins: int = 10
    thresholds: dict[str, float]      # override default thresholds per metric
    status: str = "active"
    created_at: datetime
    updated_at: datetime
```

---

## SECTION 12: METRIC ENGINE DESIGN

### Plugin / registry pattern
```python
# app/metrics/registry.py

class MetricRegistry:
    _registry: dict[str, MetricDefinition] = {}

    @classmethod
    def register(cls, metric: MetricDefinition):
        cls._registry[metric.metric_key] = metric

    @classmethod
    def get(cls, key: str) -> Optional[MetricDefinition]:
        return cls._registry.get(key)

    @classmethod
    def list_all(cls) -> list[MetricDefinition]:
        return list(cls._registry.values())

    @classmethod
    def can_run(cls, key: str, available_roles: set[str]) -> bool:
        metric = cls._registry.get(key)
        if not metric:
            return False
        return all(r in available_roles for r in metric.required_roles)
```

### MetricDefinition dataclass
```python
@dataclass
class MetricDefinition:
    metric_key: str
    display_name: str
    category: str           # "data_quality", "drift", "performance", "calibration", "strategy", "delinquency"
    description: str
    required_roles: list[str]   # roles that must be mapped for this metric to run
    optional_roles: list[str]   # roles that enhance results if available
    template_compatibility: list[str]  # which templates this metric applies to
    output_type: str        # "scalar", "table", "chart_data", "mixed"
    chart_recommendation: str   # "bar", "line", "scatter", "histogram", "heatmap", "none"
    threshold_support: bool
    calculation_fn: Callable
```

### MetricResult schema
```python
class MetricResult(BaseModel):
    metric_key: str
    display_name: str
    category: str
    status: str            # "ok", "warning", "critical", "skipped", "error"
    skipped_reason: Optional[str]     # if status == "skipped"
    scalar_value: Optional[float]
    scalar_label: Optional[str]       # e.g., "72.3%" or "0.84"
    table_data: Optional[list[dict]]
    chart_data: Optional[dict]        # see chart data format spec below
    metadata: Optional[dict]          # extra metric-specific info
    threshold_breached: bool = False
    threshold_value: Optional[float]
    computed_at: datetime
```

---

## SECTION 13: METRIC IMPLEMENTATIONS — EXACT SPECIFICATIONS

### A. DATA QUALITY METRICS

**`data_quality_row_count`**
- `scalar_value` = total row count

**`data_quality_duplicate_count`**
- `scalar_value` = `df.duplicated().sum()`

**`data_quality_null_rates`**
- `table_data` = [{column, null_count, null_pct, role, status}]
- status = "warning" if null_pct > 5%, else "ok"

**`data_quality_invalid_probability`**
- Count rows where `probability_of_default < 0` or `probability_of_default > 1`
- `scalar_value` = count

**`data_quality_invalid_target`**
- Count rows where `actual_default` is not in {0, 1}
- `scalar_value` = count

**`data_quality_readiness_summary`**
- Returns a table of role availability status
- {role, mapped_column, available: bool, warning: str}

---

### B. DRIFT / PSI METRICS

**PSI Formula (exact implementation)**

```python
def compute_psi(baseline_vals: np.ndarray, current_vals: np.ndarray, n_bins: int = 10, eps: float = 1e-4) -> float:
    """
    Population Stability Index.
    Bins are computed from baseline data (quantile-based) and applied to current.
    eps=1e-4 added to avoid log(0).
    PSI < 0.10: stable
    PSI 0.10-0.25: minor shift (monitor)
    PSI > 0.25: major shift (action required)
    """
    # Compute quantile bin edges from baseline
    quantiles = np.linspace(0, 100, n_bins + 1)
    bin_edges = np.percentile(baseline_vals, quantiles)
    bin_edges = np.unique(bin_edges)  # remove duplicate edges
    bin_edges[0] = -np.inf
    bin_edges[-1] = np.inf

    baseline_counts = np.histogram(baseline_vals, bins=bin_edges)[0]
    current_counts = np.histogram(current_vals, bins=bin_edges)[0]

    baseline_pct = (baseline_counts / len(baseline_vals)) + eps
    current_pct = (current_counts / len(current_vals)) + eps

    psi = np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct))
    return float(psi)
```

Return per-bin breakdown:
```python
bin_results = [
    {"bin": i+1, "range": f"{bin_edges[i]:.2f}–{bin_edges[i+1]:.2f}",
     "baseline_pct": baseline_pct[i]*100, "current_pct": current_pct[i]*100,
     "psi_contribution": (current_pct[i]-baseline_pct[i])*np.log(current_pct[i]/baseline_pct[i])}
    for i in range(len(baseline_counts))
]
```

**Score PSI** — `metric_key: "psi_model_score"` — applies to `model_score`
**PD PSI** — `metric_key: "psi_probability_of_default"` — applies to `probability_of_default`
**Feature CSI** — one metric per numeric feature column — `metric_key: "csi_{column_name}"`

**Categorical distribution shift** — for categorical columns and segment fields:
```python
def compute_categorical_psi(baseline_series: pd.Series, current_series: pd.Series, eps: float = 1e-4) -> float:
    """PSI for categorical columns using category frequencies as bins."""
    all_cats = set(baseline_series.unique()) | set(current_series.unique())
    baseline_pct = {c: (baseline_series == c).mean() + eps for c in all_cats}
    current_pct = {c: (current_series == c).mean() + eps for c in all_cats}
    psi = sum((current_pct[c] - baseline_pct[c]) * np.log(current_pct[c] / baseline_pct[c]) for c in all_cats)
    return float(psi)
```

---

### C. MODEL PERFORMANCE METRICS

**`perf_auc`**
```python
from sklearn.metrics import roc_auc_score
auc = roc_auc_score(y_true, y_score)
```
- Requires: `target`, `prediction_score` or `prediction_probability`
- Warn if fewer than 30 positives (low power)

**`perf_gini`**
```python
gini = 2 * auc - 1
```

**`perf_ks`**
```python
from scipy.stats import ks_2samp
# Get scores for goods and bads
good_scores = df.loc[df[target_col] == 0, score_col].values
bad_scores = df.loc[df[target_col] == 1, score_col].values
ks_stat, ks_pval = ks_2samp(good_scores, bad_scores)
```
- Return `ks_stat` (the maximum absolute difference between CDFs)

**`perf_decile_table`**
- Sort by `model_score` descending (higher score = lower risk, so best scores first)
- Create 10 equal-count bins (deciles)
- For each decile: {decile, n, n_bads, n_goods, bad_rate, cumulative_bad_pct, cumulative_good_pct, lift}
- Return as `table_data`

**`perf_confusion_matrix`**
- Default threshold: 0.5 on `probability_of_default` (or top-40% by score if no probability)
- Return: {tp, fp, tn, fn, precision, recall, f1, accuracy}

**`perf_bad_rate_by_score_band`**
- Use existing `score_band` column if available, else derive from `model_score` quantiles
- Return: [{score_band, n, bad_rate, approval_rate}] ordered: `<600`, `600-700`, `700-800`, `800+`

---

### D. CALIBRATION METRICS

**`calib_brier_score`**
```python
brier = np.mean((df[pd_col] - df[target_col]) ** 2)
brier_null = df[target_col].mean() * (1 - df[target_col].mean())
brier_skill_score = 1 - (brier / brier_null)
```

**`calib_observed_vs_predicted`**
- Bin `probability_of_default` into 10 equal-frequency bins
- For each bin: {bin, n, mean_predicted_pd, actual_default_rate, absolute_gap, relative_gap, status}
- `status` = "warning" if `abs(mean_predicted_pd - actual_default_rate) > calibration_gap_threshold`
- Return as `table_data`

**`calib_summary`**
- Overall: average predicted PD, overall realized default rate, overall calibration ratio
- `calibration_ratio = realized_dr / avg_predicted_pd`
- Status: "ok" if ratio in [0.8, 1.25], "warning" if [0.6-0.8 or 1.25-1.5], "critical" otherwise

---

### E. STRATEGY / BUSINESS METRICS

**`strategy_approval_rate`**
```python
approval_rate = (df[decision_col] == "APPROVED").mean()
```

**`strategy_decline_rate`**
```python
decline_rate = (df[decision_col] == "DECLINED").mean()
```

**`strategy_bad_rate_approved`**
- Only use rows where `application_status == "APPROVED"`
- `bad_rate = df.loc[df[decision_col]=="APPROVED", target_col].mean()`

**`strategy_decision_by_risk_band`**
- Cross-tab: `risk_rating` × `application_status`
- Return: [{risk_rating, approved_count, declined_count, approval_rate, bad_rate}]
- Order: LOW → MEDIUM → HIGH → VERY_HIG

**`strategy_avg_score_by_decision`**
- Mean `model_score` for APPROVED vs DECLINED

**`strategy_avg_loan_by_decision`**
- Mean `loan_amount` for APPROVED vs DECLINED (if `amount_field` mapped)

---

### F. DELINQUENCY METRICS

**DPD bucketing rules** (handle the non-standard 50 DPD in dataset):
```python
def classify_dpd(days: int) -> str:
    if days == 0: return "Current"
    elif days <= 29: return "1-29 DPD"
    elif days <= 59: return "30-59 DPD"
    elif days <= 89: return "60-89 DPD"
    else: return "90+ DPD"
```

**`delinq_bucket_distribution`**
- Count and percentage in each DPD bucket
- Return: [{bucket, count, pct}] in order: Current, 1-29, 30-59, 60-89, 90+

**`delinq_severe_rate`**
- `severe_rate = (df[dpd_col] >= 90).mean()`
- Threshold: warning if > 10%

**`delinq_by_score_band`**
- Mean `past_due_days` and 90+ rate per `score_band`

**`delinq_by_loan_purpose`**
- 90+ rate per `loan_purpose` — highlight concentration in `debt_cons`

---

## SECTION 14: DEFAULT ALERT THRESHOLDS (Concrete Values)

```python
DEFAULT_ALERT_THRESHOLDS = {
    # PSI thresholds
    "psi_model_score":                {"warning": 0.10, "critical": 0.25},
    "psi_probability_of_default":     {"warning": 0.10, "critical": 0.25},
    "csi_credit_score":               {"warning": 0.10, "critical": 0.25},
    "csi_debt_to_income":             {"warning": 0.10, "critical": 0.25},
    "csi_revolving_utilization":      {"warning": 0.10, "critical": 0.25},
    "csi_annual_income":              {"warning": 0.10, "critical": 0.25},

    # Performance thresholds (decline from baseline)
    "perf_auc":                       {"warning_decline": 0.03, "critical_decline": 0.05},
    "perf_gini":                      {"warning_decline": 0.05, "critical_decline": 0.08},
    "perf_ks":                        {"warning_decline": 0.03, "critical_decline": 0.05},

    # Calibration thresholds
    "calib_brier_score":              {"warning_increase": 0.005, "critical_increase": 0.01},
    "calib_ratio_overall":            {"warning_low": 0.80, "warning_high": 1.25, "critical_low": 0.60, "critical_high": 1.50},
    "calib_gap_per_bin":              {"warning": 0.03, "critical": 0.05},

    # Strategy thresholds (change from baseline)
    "strategy_approval_rate":         {"warning_change": 0.05, "critical_change": 0.10},
    "strategy_bad_rate_approved":     {"warning_increase": 0.02, "critical_increase": 0.05},
    "strategy_decline_rate":          {"warning_change": 0.05, "critical_change": 0.10},

    # Delinquency thresholds
    "delinq_severe_rate":             {"warning": 0.10, "critical": 0.20},
    "delinq_30plus_rate":             {"warning": 0.15, "critical": 0.25},

    # Data quality thresholds
    "data_quality_null_rate":         {"warning": 0.05, "critical": 0.20},
}
```

### Alert schema
```python
class Alert(BaseModel):
    alert_id: str
    run_id: str
    metric_key: str
    metric_display_name: str
    category: str   # "drift", "performance", "calibration", "strategy", "delinquency", "data_quality"
    severity: str   # "info", "warning", "critical"
    observed_value: float
    threshold_value: float
    message: str    # human-readable: "Score PSI = 0.31, exceeds critical threshold of 0.25"
    triggered_at: datetime
```

---

## SECTION 15: SEGMENTATION ENGINE

### Segment computation (for each selected segment column)
For each unique value in the segment column, compute:
```python
class SegmentResult(BaseModel):
    segment_column: str
    segment_value: str
    count: int
    share_pct: float            # share of total portfolio
    bad_rate: Optional[float]
    approval_rate: Optional[float]
    avg_model_score: Optional[float]
    avg_probability_of_default: Optional[float]
    avg_loan_amount: Optional[float]
    severe_dpd_rate: Optional[float]    # 90+ DPD rate
    # Baseline comparison (if baseline exists):
    baseline_count: Optional[int]
    baseline_share_pct: Optional[float]
    share_drift: Optional[float]        # current_share - baseline_share
    bad_rate_drift: Optional[float]     # current_bad_rate - baseline_bad_rate
    drift_status: Optional[str]         # "stable", "watch", "alert"
```

### Default segments to compute (in priority order)
1. `risk_rating` — LOW, MEDIUM, HIGH, VERY_HIG (ordered by risk)
2. `score_band` — <600, 600-700, 700-800, 800+
3. `income_band` — <50K, 50-75K, 75-100K, 100K+
4. `loan_purpose` — all 5 categories
5. `home_ownership` — RENT, MORTGAG, OWN, OTHER

### Top worsening segments
Return `top_worsening_segments: list[SegmentResult]` — top 3 segments with highest `bad_rate_drift` vs baseline.

---

## SECTION 16: RUN LIFECYCLE

### Run status states
```
PENDING → RUNNING → COMPLETED
                  → FAILED
```

### Run metadata schema
```python
class RunMetadata(BaseModel):
    run_id: str
    monitor_id: str
    dataset_id: str
    baseline_dataset_id: Optional[str]
    status: str     # "pending", "running", "completed", "failed"
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    metrics_computed: list[str]       # list of metric keys that ran successfully
    metrics_skipped: list[str]        # list of metric keys skipped + reason
    metrics_failed: list[str]         # list of metric keys that errored
    row_count: int
    baseline_row_count: Optional[int]
    created_at: datetime
```

### Run execution flow (in `run_service.py`)
```
1. Create RunMetadata with status="pending", save to storage
2. Update status to "running"
3. Load dataset from storage
4. Apply column mapping
5. If baseline_dataset_id exists: load baseline dataset
6. Validate required fields
7. Determine which metrics can run (MetricRegistry.can_run per available roles)
8. For each runnable metric: compute metric, catch individual errors, log & continue
9. Run segmentation engine for all selected segments
10. Run alert engine against all metric results
11. Run insight service (deterministic findings + LLM context builder)
12. Compute composite health score
13. Serialize all outputs to storage/{run_id}/
14. Update status to "completed" (or "failed" if critical error)
15. Return run_id and summary
```

---

## SECTION 17: OUTPUT DESIGN FOR FRONTEND

### Summary cards payload
```python
class SummaryCards(BaseModel):
    total_records: int
    total_bad: int
    bad_rate: float                  # as decimal, e.g. 0.056
    approval_rate: Optional[float]
    decline_rate: Optional[float]
    bad_rate_on_approved: Optional[float]
    avg_model_score: Optional[float]
    avg_probability_of_default: Optional[float]
    # Performance
    auc: Optional[float]
    gini: Optional[float]
    ks: Optional[float]
    # Drift
    psi_model_score: Optional[float]
    psi_status: Optional[str]        # "stable", "monitor", "unstable"
    # Health
    model_health_score: Optional[float]   # 0-100
    model_health_status: Optional[str]    # "healthy", "watch", "deteriorating", "critical"
    # Alerts
    alert_count_critical: int
    alert_count_warning: int
    # Baseline
    has_baseline: bool
```

### Chart data format (standard across all charts)
```python
# All chart payloads use this structure:
class ChartPayload(BaseModel):
    chart_id: str
    chart_type: str      # "bar", "line", "scatter", "histogram", "pie", "heatmap"
    title: str
    subtitle: Optional[str]
    x_label: Optional[str]
    y_label: Optional[str]
    series: list[ChartSeries]
    annotations: Optional[list[dict]]    # threshold lines, reference points

class ChartSeries(BaseModel):
    name: str            # series label, e.g. "Current", "Baseline"
    data: list[dict]     # [{"x": "600-700", "y": 0.08}, ...]
    color: Optional[str] # hex color hint for frontend
```

### Required chart payloads
Generate these charts in every credit scorecard monitoring run:

1. **`chart_score_distribution`** — histogram of `model_score`, bars by score band
2. **`chart_pd_distribution`** — histogram of `probability_of_default`
3. **`chart_bad_rate_by_score_band`** — bar chart: {score_band → bad_rate}
4. **`chart_approval_by_risk_band`** — bar chart: {risk_rating → approval_rate}
5. **`chart_calibration`** — line chart: x=predicted_pd_bin, y=[predicted_line, observed_line]
6. **`chart_dpd_distribution`** — bar chart: DPD bucket → count/pct
7. **`chart_psi_breakdown`** — bar chart: features → PSI value (if baseline exists)
8. **`chart_segment_bad_rate`** — grouped bar: segment columns × bad_rate
9. **`chart_decile_lift`** — bar chart: decile → lift value
10. **`chart_roc_curve`** — line chart: FPR vs TPR (if target + score available)

### Server-side chart rendering (`app/charts/renderer.py`)

Pure function, takes a `ChartPayload` and returns image bytes — never reaches into raw data or recomputes anything:

```python
import matplotlib
matplotlib.use("Agg")   # headless backend — required, must be set before importing pyplot
import matplotlib.pyplot as plt
import io

CHART_TYPE_RENDERERS = {
    "bar": render_bar,
    "line": render_line,
    "histogram": render_histogram,
    "scatter": render_scatter,
    "heatmap": render_heatmap,
}

def render_chart(payload: ChartPayload, fmt: str = "png", dpi: int = 100) -> bytes:
    """Render a ChartPayload to PNG or SVG bytes using matplotlib."""
    fig, ax = plt.subplots(figsize=(7, 4.2))
    renderer_fn = CHART_TYPE_RENDERERS.get(payload.chart_type, render_bar)
    renderer_fn(ax, payload)
    ax.set_title(payload.title, fontsize=12)
    if payload.x_label: ax.set_xlabel(payload.x_label)
    if payload.y_label: ax.set_ylabel(payload.y_label)
    ax.legend(loc="best", fontsize=8) if len(payload.series) > 1 else None
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, dpi=dpi)
    plt.close(fig)   # critical — prevents memory leak across requests
    buf.seek(0)
    return buf.read()

def render_bar(ax, payload: ChartPayload):
    for series in payload.series:
        xs = [d["x"] for d in series.data]
        ys = [d["y"] for d in series.data]
        ax.bar(xs, ys, label=series.name, color=series.color, alpha=0.85)

def render_line(ax, payload: ChartPayload):
    for series in payload.series:
        xs = [d["x"] for d in series.data]
        ys = [d["y"] for d in series.data]
        ax.plot(xs, ys, label=series.name, color=series.color, marker="o", markersize=3)

# render_histogram, render_scatter, render_heatmap follow the same pattern —
# implement all of them, no "similar for others" shortcuts.
```

**Critical implementation rules for the renderer:**
- `plt.close(fig)` after every render — without this, repeated requests leak memory in a long-running server process.
- `matplotlib.use("Agg")` must be the first matplotlib-related line executed, before `pyplot` is imported anywhere in the process — set it once in `renderer.py`'s module-level code.
- The renderer never touches `pandas`, the dataset, or storage — it only consumes the already-computed `ChartPayload`. This guarantees the PNG and the JSON are always visually consistent (same numbers, two output formats) and keeps rendering fast (no recomputation).
- Threshold/reference lines from `payload.annotations` (e.g. a red dashed line at PSI=0.25) should render as `ax.axhline()` calls — include this so static images carry the same context as the interactive JSON version.

### Deterministic insight examples (exact strings)
```python
INSIGHT_TEMPLATES = {
    "psi_high": "Score distribution shows {severity} population drift (PSI = {value:.3f}). "
                "Model may be scoring a different population than training.",
    "auc_decline": "Model discrimination declined by {delta:.1%} vs baseline "
                   "(AUC: {baseline:.3f} → {current:.3f}). Rank-ordering may be weakening.",
    "approval_rate_drop": "Approval rate decreased by {delta:.1%} vs baseline "
                          "({baseline:.1%} → {current:.1%}). Review policy cut-off changes.",
    "strategy_deterioration": "Approval rate fell while approved bad rate rose — "
                               "portfolio quality of booked accounts is deteriorating.",
    "calibration_gap": "PD over/under-estimation detected in {n_bands} score bands. "
                       "Provisioning accuracy may be affected.",
    "delinq_concentration": "Severe delinquency (90+ DPD) is concentrated in "
                             "{segment_col}={segment_val} ({rate:.1%} of segment).",
    "segment_risk": "Highest bad rate increase vs baseline detected in "
                    "{segment_col}={segment_val} (+{delta:.1%}).",
    "low_bad_count": "Only {n_bads} defaults in dataset. Discrimination metrics "
                     "have limited statistical power. Interpret with caution.",
}
```

---

## SECTION 18: COMPOSITE MODEL HEALTH SCORE

### Health score computation
```python
class HealthScore(BaseModel):
    score: float               # 0-100 (100 = perfect health)
    status: str                # "healthy", "watch", "deteriorating", "critical"
    components: dict           # {metric_key: {"score": 0-100, "weight": float, "status": str}}
    recommended_actions: list[str]
```

### Scoring logic
```python
HEALTH_WEIGHTS = {
    "perf_gini":           0.25,
    "perf_ks":             0.20,
    "psi_model_score":     0.20,
    "calib_ratio_overall": 0.20,
    "perf_auc":            0.15,
}

def metric_to_component_score(metric_key: str, value: float) -> float:
    """Convert raw metric value to 0-100 component score."""
    scorers = {
        "perf_gini":       lambda v: min(100, max(0, v * 100 / 0.7 * 100)),   # 0.7 Gini = 100
        "perf_ks":         lambda v: min(100, max(0, v * 100 / 0.5 * 100)),   # 0.5 KS = 100
        "psi_model_score": lambda v: max(0, 100 - (v / 0.25) * 100),          # 0 PSI = 100, 0.25+ = 0
        "calib_ratio":     lambda v: max(0, 100 - abs(1 - v) * 200),           # ratio=1.0 = 100
        "perf_auc":        lambda v: min(100, max(0, (v - 0.5) / 0.3 * 100)), # 0.8 AUC = 100
    }

# Status mapping:
# score >= 75: healthy
# score 55-74: watch
# score 35-54: deteriorating
# score < 35:  critical
```

---

## SECTION 19: BASELINE STORAGE STRATEGY

### Important design decision
Do NOT store the full baseline CSV in memory or re-read it on every run. Instead, when a dataset is first designated as baseline, pre-compute and persist:

```python
class BaselineStats(BaseModel):
    dataset_id: str
    computed_at: datetime
    row_count: int
    # Per-column statistics
    numeric_stats: dict   # {col: {"mean", "std", "min", "max", "percentiles": [p10,..,p90]}}
    categorical_stats: dict   # {col: {"value_counts": {cat: pct}, "total": n}}
    score_decile_edges: list[float]   # 11 edges for 10 decile bins
    pd_decile_edges: list[float]
    # Computed metric values (for comparison)
    baseline_metrics: dict    # {metric_key: scalar_value}
```

Save as `storage/profiles/{dataset_id}_baseline_stats.json`. This enables PSI computation without reloading the full baseline CSV.

---

## SECTION 20: AI INSIGHT LAYER

### Layer 1: Deterministic finding engine

```python
class Finding(BaseModel):
    finding_id: str
    category: str   # "drift", "performance", "calibration", "strategy", "delinquency", "segment_risk", "data_quality", "portfolio_mix"
    severity: str   # "info", "warning", "critical"
    title: str
    narrative: str
    evidence_metrics: list[str]   # metric_keys that triggered this finding
    evidence_segments: list[str]  # segment values if applicable
    supporting_values: dict       # {"psi": 0.31, "threshold": 0.25}
    possible_causes: list[str]
    recommended_actions: list[str]
    confidence: str   # "high", "medium", "low"
    generated_by: str = "rule_engine"
```

### Deterministic finding rules (implement all of these)
```python
FINDING_RULES = [
    # Drift findings
    Rule("psi_model_score > critical",    category="drift",        severity="critical"),
    Rule("psi_model_score > warning",     category="drift",        severity="warning"),
    Rule("any_feature_csi > critical",    category="drift",        severity="warning"),
    Rule("approval_rate_drift > critical",category="policy_shift",  severity="critical"),

    # Performance findings
    Rule("auc_decline > critical",         category="performance",  severity="critical"),
    Rule("gini_decline > warning",         category="performance",  severity="warning"),
    Rule("ks_decline > warning",           category="performance",  severity="warning"),

    # Calibration findings
    Rule("brier_increase > critical",      category="calibration",  severity="warning"),
    Rule("calib_ratio outside [0.8,1.25]", category="calibration", severity="warning"),
    Rule("calib_gap_in_low_bands",         category="calibration",  severity="warning"),

    # Strategy findings
    Rule("approval_down + bad_rate_up",    category="strategy",     severity="critical",
         narrative="Strategy deterioration: approval fell while portfolio quality worsened."),
    Rule("decline_rate_up_significantly",  category="policy_shift", severity="warning"),

    # Delinquency findings
    Rule("severe_dpd_rate > critical",     category="delinquency",  severity="critical"),
    Rule("dpd_concentrated_in_segment",    category="segment_risk", severity="warning"),

    # Segment findings
    Rule("segment_bad_rate_worst",         category="segment_risk", severity="warning"),
    Rule("segment_share_drift_large",      category="portfolio_mix",severity="info"),

    # Data quality findings
    Rule("target_low_bad_count",           category="data_quality", severity="info",
         narrative="Only {n_bads} defaults detected. Statistical power is limited."),
    Rule("application_time_malformed",     category="data_quality", severity="info"),
    Rule("risk_rating_truncated",          category="data_quality", severity="info"),
]
```

### Layer 2: LLM-ready insight context builder

```python
class InsightContext(BaseModel):
    """Compact evidence package for future LLM narrative generation."""
    run_id: str
    monitor_name: str
    template_type: str
    run_date: str
    dataset_rows: int
    has_baseline: bool

    # Dataset summary
    target_base_rate: float
    approval_rate: Optional[float]

    # Key metric status
    metric_status_table: list[dict]   # [{metric_key, value, status, vs_baseline_delta}]
    threshold_breaches: list[dict]    # [{metric_key, value, threshold, severity}]
    top_worsening_metrics: list[str]

    # Drift summary
    top_drifting_features: list[dict]   # [{feature, csi_value, status}]

    # Segment summary
    top_worsening_segments: list[dict]  # [{col, value, bad_rate, bad_rate_drift}]

    # Calibration highlights
    calibration_ratio_overall: Optional[float]
    calibration_worst_band: Optional[dict]

    # Delinquency highlights
    severe_dpd_rate: Optional[float]
    dpd_worst_segment: Optional[dict]

    # Findings already generated
    deterministic_findings: list[Finding]
    finding_count_by_severity: dict     # {"critical": 2, "warning": 5, "info": 1}

    # Recommended focus areas
    priority_review_areas: list[str]
```

### Layer 3: LLM interface placeholder

```python
# app/services/llm_service.py

class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"

class LLMConfig(BaseModel):
    provider: LLMProvider = LLMProvider.MOCK
    model: str = "gpt-4o"
    temperature: float = 0.3
    max_tokens: int = 2000

class LLMService:
    """Placeholder for future LLM integration. Currently uses mock responses."""

    async def generate_narrative(
        self,
        context: InsightContext,
        mode: str = "executive",   # "executive", "analyst", "root_cause", "action_plan"
        config: LLMConfig = LLMConfig()
    ) -> dict:
        if config.provider == LLMProvider.MOCK:
            return self._mock_narrative(context, mode)
        # Future: call OpenAI or Anthropic API
        raise NotImplementedError("Live LLM integration not yet implemented. Use mock provider.")

    def _mock_narrative(self, context: InsightContext, mode: str) -> dict:
        """Generate a deterministic mock narrative from findings."""
        # Build from findings and metric status — no hallucination
        return {
            "executive_summary": self._build_executive_summary(context),
            "technical_summary": self._build_technical_summary(context),
            "root_causes": self._extract_possible_causes(context),
            "key_segments": [s["value"] for s in context.top_worsening_segments[:3]],
            "recommended_actions": self._extract_actions(context),
            "confidence_notes": ["Generated deterministically from computed metrics. No LLM used."],
            "generated_by": "mock_deterministic",
        }
```

---

## SECTION 21: API ENDPOINTS (Complete Contract)

### Base URL: `/api/v1`

### A. Health
```
GET  /health
Response: {"status": "ok", "version": "1.0.0", "timestamp": "..."}
```

### B. Datasets
```
POST /datasets/upload
  Body: multipart/form-data {file: CSV, name?: str, description?: str}
  Validation: only .csv files, max 100MB
  Response: APIResponse[DatasetSummary]

GET  /datasets?page=1&limit=20
  Response: PaginatedResponse[DatasetSummary]

GET  /datasets/{dataset_id}
  Response: APIResponse[DatasetDetail]

GET  /datasets/{dataset_id}/profile
  Response: APIResponse[DatasetProfile]

GET  /datasets/{dataset_id}/preview?n=20
  Response: APIResponse[DatasetPreview]
```

### C. Mapping
```
POST /datasets/{dataset_id}/suggest-mapping
  Response: APIResponse[MappingSuggestion]  # auto-suggested + confidence scores

POST /datasets/{dataset_id}/save-mapping
  Body: ColumnMapping
  Response: APIResponse[ColumnMapping]

GET  /datasets/{dataset_id}/mapping
  Response: APIResponse[ColumnMapping]

GET  /datasets/{dataset_id}/mapping/validate
  Response: APIResponse[MappingValidationResult]
```

### D. Monitor Config
```
POST /monitors/create
  Body: MonitorCreateRequest
  Response: APIResponse[MonitorConfig]

GET  /monitors?page=1&limit=20
  Response: PaginatedResponse[MonitorSummary]

GET  /monitors/{monitor_id}
  Response: APIResponse[MonitorConfig]

PUT  /monitors/{monitor_id}
  Body: MonitorUpdateRequest (partial)
  Response: APIResponse[MonitorConfig]

DELETE /monitors/{monitor_id}
  Response: APIResponse[{"deleted": true}]
```

### E. Monitor Runs
```
POST /monitors/{monitor_id}/run
  Body: RunRequest {baseline_dataset_id?: str, override_thresholds?: dict}
  Response: APIResponse[RunSummary]   # returns immediately with run_id + summary

GET  /runs?page=1&limit=20&monitor_id=?
  Response: PaginatedResponse[RunMetadata]

GET  /runs/{run_id}/summary
  Response: APIResponse[RunSummary]   # summary_cards + health_score + alert counts

GET  /runs/{run_id}/metrics
  Response: APIResponse[list[MetricResult]]

GET  /runs/{run_id}/segments
  Response: APIResponse[list[SegmentResult]]

GET  /runs/{run_id}/alerts
  Response: APIResponse[list[Alert]]

GET  /runs/{run_id}/charts?format=json
  format=json (default): Response: APIResponse[list[ChartPayload]]
  format=png|svg: not valid on this list endpoint — use the per-chart endpoint below for image output

GET  /runs/{run_id}/charts/{chart_id}?format=json
  Response: APIResponse[ChartPayload]   # single chart, JSON mode (default)

GET  /runs/{run_id}/charts/{chart_id}/image?format=png
  format=png (default) | format=svg
  Response: raw image bytes, Content-Type: image/png or image/svg+xml
  Renders the same underlying ChartPayload server-side via matplotlib (Agg backend).
  Use for: <img> embedding, direct download, email/Slack alert attachments, quick previews without a frontend.

GET  /runs/{run_id}/findings
  Response: APIResponse[list[Finding]]

GET  /runs/{run_id}/insight-context
  Response: APIResponse[InsightContext]

POST /runs/{run_id}/generate-narrative-placeholder
  Body: {mode: "executive|analyst|root_cause|action_plan"}
  Response: APIResponse[dict]   # mock narrative from deterministic logic

GET  /runs/{run_id}/narratives
  Response: APIResponse[dict]   # stored narrative (if generated)

GET  /runs/{run_id}/results
  Response: APIResponse[CompleteRunResult]  # all of the above combined
```

### F. Helpers
```
GET  /metric-library
  Response: APIResponse[list[MetricDefinition]]   # full registry, metadata only (no fns)

GET  /templates
  Response: APIResponse[list[TemplateInfo]]

GET  /segments/recommendations/{dataset_id}
  Response: APIResponse[list[SegmentRecommendation]]

GET  /health-score/{run_id}
  Response: APIResponse[HealthScore]
```

---

## SECTION 22: FILESYSTEM PERSISTENCE CONTRACT

### Base storage helpers
```python
# app/storage/base.py

import json, uuid
from pathlib import Path
from datetime import datetime
from typing import Any

def generate_id(prefix: str = "") -> str:
    uid = str(uuid.uuid4()).replace("-", "")[:12]
    ts = datetime.utcnow().strftime("%Y%m%d")
    return f"{prefix}_{ts}_{uid}" if prefix else f"{ts}_{uid}"

def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=str)

def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Not found: {path}")
    with open(path, "r") as f:
        return json.load(f)

def list_json_objects(folder: Path) -> list[dict]:
    if not folder.exists():
        return []
    return [load_json(p) for p in sorted(folder.glob("*.json"), reverse=True)]

def exists(path: Path) -> bool:
    return path.exists()
```

### Repository classes
Each store must implement: `create`, `get`, `list`, `update`, `exists`, `delete`.

```python
# app/storage/dataset_store.py
class DatasetStore:
    def __init__(self, root: Path): self.root = root
    def create(self, dataset: dict) -> dict: ...
    def get(self, dataset_id: str) -> dict: ...
    def list(self, page: int = 1, limit: int = 20) -> list[dict]: ...
    def update(self, dataset_id: str, updates: dict) -> dict: ...
    def exists(self, dataset_id: str) -> bool: ...
    def delete(self, dataset_id: str) -> bool: ...

# Same pattern for: MappingStore, MonitorConfigStore, MonitorRunStore
```

---

## SECTION 23: RESULT SERIALIZATION

### Files saved per run to `storage/runs/{run_id}/`
```
run_metadata.json        # RunMetadata
summary_cards.json       # SummaryCards
metrics.json             # list[MetricResult]
charts.json              # list[ChartPayload]
segments.json            # list[SegmentResult]
alerts.json              # list[Alert]
findings.json            # list[Finding]
insight_context.json     # InsightContext
narratives.json          # LLM narrative (if generated)
health_score.json        # HealthScore
```

### Complete run result (for `GET /runs/{run_id}/results`)
```python
class CompleteRunResult(BaseModel):
    metadata: RunMetadata
    summary_cards: SummaryCards
    health_score: HealthScore
    metrics: list[MetricResult]
    charts: list[ChartPayload]
    segments: list[SegmentResult]
    alerts: list[Alert]
    findings: list[Finding]
    insight_context: InsightContext
    narratives: Optional[dict]
```

---

## SECTION 24: CODE QUALITY STANDARDS

### Logging (use Loguru throughout)
```python
from loguru import logger

# In service entry points:
logger.info(f"Starting monitor run: run_id={run_id}, monitor_id={monitor_id}")

# On metric computation:
logger.debug(f"Computing metric: {metric_key}")

# On skip:
logger.warning(f"Skipping metric {metric_key}: required role '{role}' not mapped")

# On individual metric error:
logger.error(f"Metric {metric_key} failed: {e}")

# On run completion:
logger.info(f"Run {run_id} completed in {duration:.2f}s. "
            f"Metrics: {len(computed)} ok, {len(skipped)} skipped, {len(failed)} failed.")
```

### Exception handling
```python
# app/core/exceptions.py

class ModelPulseError(Exception): pass
class DatasetNotFoundError(ModelPulseError): pass
class MappingNotFoundError(ModelPulseError): pass
class MonitorNotFoundError(ModelPulseError): pass
class RunNotFoundError(ModelPulseError): pass
class InvalidFileTypeError(ModelPulseError): pass
class FileTooLargeError(ModelPulseError): pass
class InsufficientDataError(ModelPulseError): pass

# Register handlers in main.py — return APIResponse(success=False, error=str(e))
```

### Import organization
- Always use absolute imports: `from app.services.run_service import RunService`
- Group imports: stdlib → third-party → internal
- No wildcard imports

### Pydantic v2 conventions
```python
class MyModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, use_enum_values=True)
    field: str
    optional_field: Optional[str] = None
```

### CORS configuration
```python
# in main.py
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # POC: allow all. Restrict in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## SECTION 25: IMPLEMENTATION STRATEGY — OUTPUT ORDER

Generate the backend in exactly this order. For each file:
1. Print the file path as a header
2. Print the complete file content (no pseudo-code, no TODOs for core logic)
3. Keep imports consistent with all previously generated files

### Part 1: Architecture + contracts (generate first, no code)
- Architecture summary
- Complete folder structure
- Persistence design decisions
- API contract list
- Core Pydantic schemas overview

### Part 2: Foundation
- `requirements.txt`
- `main.py`
- `app/core/config.py`
- `app/core/exceptions.py`
- `app/core/logging_config.py`
- `app/storage/base.py`
- `app/storage/dataset_store.py`
- `app/storage/mapping_store.py`
- `app/storage/monitor_store.py`
- `app/storage/run_store.py`
- `app/schemas/common.py`
- `app/utils/dataframe.py`
- `app/utils/formatting.py`

### Part 3: Dataset ingestion + profiling + mapping
- `app/schemas/dataset.py`
- `app/schemas/mapping.py`
- `app/profiling/profiler.py`
- `app/mapping/heuristics.py`
- `app/mapping/validator.py`
- `app/services/dataset_service.py`
- `app/services/mapping_service.py`
- `app/api/routes/datasets.py`
- `app/api/routes/mappings.py`

### Part 4: Monitor config + metric engine
- `app/schemas/monitor.py`
- `app/schemas/metrics.py`
- `app/schemas/charts.py`
- `app/schemas/segments.py`
- `app/schemas/alerts.py`
- `app/metrics/base.py`
- `app/metrics/registry.py`
- `app/metrics/engine.py`
- `app/metrics/implementations/data_quality.py`
- `app/metrics/implementations/drift.py`
- `app/metrics/implementations/performance.py`
- `app/metrics/implementations/calibration.py`
- `app/metrics/implementations/strategy.py`
- `app/metrics/implementations/delinquency.py`
- `app/services/monitor_service.py`
- `app/api/routes/monitors.py`

### Part 5: Run orchestration + outputs
- `app/schemas/run.py`
- `app/schemas/insights.py`
- `app/segmentation/engine.py`
- `app/alerts/engine.py`
- `app/services/insight_service.py`
- `app/services/health_score_service.py`
- `app/services/run_service.py`
- `app/api/routes/runs.py`
- `app/api/routes/helpers.py`
- `app/api/routes/health.py`

### Part 6: Final wiring + demo artifacts
- `README.md` — step-by-step run instructions
- `.env.example`
- Sample request/response JSON payloads (5 complete examples)
- How to demo the platform in 10 minutes

---

## SECTION 26: DEMO PRIORITY (THE 10-MINUTE DEMO SCRIPT)

The backend must support this exact demo flow impressively:

1. **Upload** `underwriting_scorecard_clean.csv` via `POST /datasets/upload`
   → Returns `dataset_id`, row count, column count

2. **Profile** via `GET /datasets/{dataset_id}/profile`
   → Shows all 22 columns, types, null rates, monitoring-readiness warnings (including malformed `application_time` and truncated `VERY_HIG`)

3. **Suggest mapping** via `POST /datasets/{dataset_id}/suggest-mapping`
   → Returns confident auto-mapping for all 22 columns with role labels

4. **Save mapping** via `POST /datasets/{dataset_id}/save-mapping`
   → Confirms saved

5. **Create monitor** via `POST /monitors/create`
   → Returns `monitor_id` with `credit_scorecard_monitoring` template

6. **Run monitor** via `POST /monitors/{monitor_id}/run`
   → Executes all metrics, returns polished result within seconds

7. **Show summary cards** via `GET /runs/{run_id}/summary`
   → Shows AUC=0.82, Gini=0.64, KS=0.43, bad_rate=5.6%, approval_rate=77.2%, health_score=78

8. **Show segment drilldown** via `GET /runs/{run_id}/segments`
   → Shows bad rate by risk_rating, score_band, income_band, loan_purpose

9. **Show alerts** via `GET /runs/{run_id}/alerts`
   → Shows data quality notes about truncated values, low bad count warning

10. **Show findings** via `GET /runs/{run_id}/findings`
    → Shows: "Only 11 defaults — statistical power limited", "VERY_HIG appears truncated in risk_rating", deterministic strategy and delinquency insights

The experience should feel like a professional internal model monitoring platform, not a toy demo.

---

## KNOWN DATA ISSUES — HANDLE GRACEFULLY, DO NOT CRASH

| Issue | Where | Handling |
|-------|-------|----------|
| `application_time = "46:27.6"` | profiler, event_time mapping | Log warning, mark as malformed, continue |
| `risk_rating = "VERY_HIG"` | everywhere risk_rating is used | Treat as valid category, add data quality note |
| `home_ownership = "MORTGAG"` | everywhere | Treat as valid category, no error |
| `past_due_days = 50` | DPD bucketing | Place in `30-59 DPD` bucket |
| `actual_default` base rate = 5.6% | performance metrics | Warn: low bad count, limited statistical power |
| 197 rows total | calibration bins | Use 5 bins instead of 10 if n < 200 to avoid empty bins |

---

*End of system prompt v2.0*

---

# ADDENDUM — v2.1 (Additions Based on Review)

---

## SECTION 27: DYNAMIC DATASET HANDLING

### The platform is fully dataset-agnostic

The sample CSV (`underwriting_scorecard_clean.csv`) is for POC demo only. The backend must handle ANY uploaded CSV file correctly.

### How to achieve this

**Role heuristics must use patterns, not exact column names.**

```python
# app/mapping/heuristics.py
# These patterns match ANY column name that looks like that role.

ROLE_PATTERNS = {
    "record_id": [
        "id", "key", "uuid", "code", "ref", "no", "num",
        "applicationid", "customerid", "loanid", "accountid", "caseid",
    ],
    "event_time": [
        "date", "time", "dt", "timestamp", "created", "applied",
        "originated", "booked", "opened", "period",
    ],
    "target": [
        "default", "bad", "chargoff", "fraud", "target", "label",
        "outcome", "event", "flag", "indicator", "def", "delinquent",
    ],
    "prediction_score": [
        "score", "modelscore", "decisionscore", "applicationscore",
        "riskscore", "creditscore",
        # BUT NOT: riskrating, riskband, scoreband (those go to risk_band/score_band)
    ],
    "prediction_probability": [
        "prob", "pd", "probability", "likelihood", "propensity",
        "expectedloss", "el", "lossrate",
    ],
    "decision": [
        "status", "decision", "approve", "decline", "accept", "reject",
        "disposition", "outcome", "result", "verdict",
    ],
    "dpd_field": [
        "dpd", "daysdue", "daysoverdue", "pastdue", "daysdelinquent",
        "daysarrears", "ageing", "bucket",
    ],
    "amount_field": [
        "amount", "balance", "principal", "loan", "exposure",
        "outstanding", "disbursed", "limit", "credit",
    ],
    "score_band": [
        "scoreband", "scoretier", "scorerange", "scoregroup",
        "scorebucket", "scorebin",
    ],
    "risk_band": [
        "riskrating", "riskband", "riskgrade", "risktier",
        "riskgroup", "riskclass", "riskbucket",
    ],
    "segment_field": [
        "purpose", "type", "category", "product", "channel",
        "region", "state", "city", "branch", "segment", "band",
        "tier", "bucket", "group", "class", "ownership", "tenure",
        "employment", "industry", "sector",
    ],
}

# Confidence scoring
CONFIDENCE_HIGH = 0.90    # strong pattern match, correct value type
CONFIDENCE_MEDIUM = 0.65  # partial pattern match or ambiguous name
CONFIDENCE_LOW = 0.35     # weak match, needs user confirmation
```

### Graceful degradation for unfamiliar CSVs

When columns cannot be confidently mapped:
- Assign them `"feature_field"` as the default fallback role
- Set confidence = `CONFIDENCE_LOW`
- Flag them in `unmatched_columns` list in the suggestion response
- Metrics that require unmapped roles are silently skipped (not errored)

### Required handling for completely unknown CSVs
```python
# If NO column maps to "target" with confidence > 0.5:
#   - Run data quality and drift metrics only
#   - Skip all performance, calibration metrics
#   - Add warning: "Target column not identified — discrimination metrics unavailable"

# If NO column maps to "prediction_score":
#   - Run data quality metrics only
#   - Add warning: "Score column not identified — most monitoring metrics unavailable"
#   - Still run segment analysis on whatever segments are found

# If NO column maps to "decision":
#   - Skip all strategy/approval metrics gracefully
```

---

## SECTION 28: ENHANCED COLUMN MAPPING UX — AUTO + MANUAL

### Mapping UX philosophy
- **Auto-first, human-confirmed**: always show the auto-suggestion, let the user accept or override
- **Never force**: if auto-detection fails, user must be able to select from a dropdown of all available roles
- **Per-column**: every column gets its own suggestion + override option
- **One-click accept**: user can accept all suggestions at once if confident

### Enhanced `MappingSuggestion` response schema
```python
class ColumnSuggestion(BaseModel):
    column_name: str
    inferred_type: str              # "numeric", "categorical", "datetime", "id", "unknown"
    suggested_role: str             # top suggested role key (e.g. "target")
    confidence: float               # 0.0–1.0
    confidence_label: str           # "high" (>0.8), "medium" (0.5-0.8), "low" (<0.5)
    reasoning: str                  # human-readable explanation
    # Example: "Column name 'actual_default' matches target pattern; values are {0,1} (binary)"
    alternative_roles: list[str]    # other roles the column could be assigned to
    sample_values: list[Any]        # up to 5 distinct values from the column
    null_pct: float
    unique_count: int
    is_auto_assignable: bool        # True if confidence >= 0.75

class MappingSuggestion(BaseModel):
    dataset_id: str
    total_columns: int
    auto_assignable_count: int      # columns with confidence >= 0.75
    needs_review_count: int         # columns with confidence < 0.75
    suggestions: list[ColumnSuggestion]  # one per column, all columns
    available_roles: list[str]      # all role keys user can choose from
    unmatched_columns: list[str]    # columns that got no confident match
    suggested_segments: list[str]   # columns recommended as segment_fields
    suggested_features: list[str]   # columns recommended as feature_fields
    monitoring_readiness: list[str] # warnings (same as profiler warnings)
```

### `SaveMapping` request schema — supports both auto-accepted and manually edited
```python
class SaveMappingRequest(BaseModel):
    # User sends back the full mapping (auto-suggested or manually changed)
    # Each column must appear exactly once
    column_roles: dict[str, str]     # {column_name: role_key}
    # Lists for multi-valued roles
    segment_fields: list[str]        # columns assigned "segment_field"
    feature_fields: list[str]        # columns assigned "feature_field"
    ignored_fields: list[str]        # columns to ignore entirely
    # Score settings
    score_direction: str = "higher_is_better"
    target_positive_label: Any = 1
    decision_positive_label: str = "APPROVED"
    # Accept all auto-suggestions shortcut (no manual changes)
    accept_all_auto: bool = False
```

### Frontend behavior contract (document in README)
The frontend should render:
1. A table with one row per column
2. Each row shows: column name | sample values | auto-suggested role (dropdown) | confidence badge
3. Columns with `confidence >= 0.75` → pre-filled dropdown, green badge "Auto-detected"
4. Columns with `confidence < 0.75` → pre-filled but yellow badge "Review suggested"
5. Columns in `unmatched_columns` → empty dropdown, red badge "Select manually"
6. "Accept All" button to accept all auto-suggestions
7. "Save Mapping" button to submit `SaveMappingRequest`

---

## SECTION 29: BACKEND CHART RENDERING

### Core decision
The backend renders all charts as **PNG images using matplotlib**, saves them to disk, and serves them via FastAPI `StaticFiles`. Every API response that includes chart data also includes the image URL.

This means:
- Charts are viewable **without any frontend** (just open the URL)
- Charts can be embedded in **PDF/HTML reports** directly
- Swagger UI (`/docs`) becomes a complete monitoring dashboard for demos
- Frontend can use EITHER the image URL OR the JSON data for interactive rendering

### Add to requirements.txt
```
matplotlib==3.8.4
seaborn==0.13.2
```

### Chart renderer module
```python
# app/charts/renderer.py

import matplotlib
matplotlib.use('Agg')   # NON-INTERACTIVE backend — MUST be before pyplot import
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import numpy as np
import pandas as pd
from pathlib import Path
from loguru import logger

# Consistent color palette across all charts
PALETTE = {
    "primary":   "#4F46E5",   # indigo — bars, main series
    "secondary": "#06B6D4",   # cyan — secondary series
    "success":   "#10B981",   # green — good/approved
    "warning":   "#F59E0B",   # amber — watch
    "danger":    "#EF4444",   # red — critical/bad/declined
    "neutral":   "#6B7280",   # gray — baseline, neutral series
    "baseline":  "#94A3B8",   # light gray — baseline comparison series
    "bg":        "#FFFFFF",   # white background
    "grid":      "#F3F4F6",   # light gray grid
    "text":      "#111827",   # near-black text
    "text_muted":"#6B7280",   # muted label text
}

# Score band ordered categories (for consistent axis ordering)
SCORE_BAND_ORDER = ["<600", "600-700", "700-800", "800+"]
RISK_RATING_ORDER = ["LOW", "MEDIUM", "HIGH", "VERY_HIG"]
DPD_BUCKET_ORDER = ["Current", "1-29 DPD", "30-59 DPD", "60-89 DPD", "90+ DPD"]

def apply_style(ax, title: str, x_label: str = "", y_label: str = "",
                title_size: int = 13):
    """Apply consistent styling to a matplotlib axes object."""
    ax.set_title(title, fontsize=title_size, fontweight='bold',
                 color=PALETTE["text"], pad=12)
    if x_label:
        ax.set_xlabel(x_label, fontsize=10, color=PALETTE["text_muted"])
    if y_label:
        ax.set_ylabel(y_label, fontsize=10, color=PALETTE["text_muted"])
    ax.set_facecolor(PALETTE["bg"])
    ax.grid(axis='y', color=PALETTE["grid"], linewidth=0.8, zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(PALETTE["grid"])
    ax.spines['bottom'].set_color(PALETTE["grid"])
    ax.tick_params(colors=PALETTE["text_muted"], labelsize=9)

class ChartRenderer:
    def __init__(self, charts_dir: Path):
        self.dir = charts_dir
        self.dir.mkdir(parents=True, exist_ok=True)

    def _save(self, fig, chart_id: str) -> str:
        path = self.dir / f"{chart_id}.png"
        fig.savefig(path, dpi=150, bbox_inches='tight',
                    facecolor=PALETTE["bg"], edgecolor='none')
        plt.close(fig)
        logger.debug(f"Chart saved: {path}")
        return str(path)

    # ── 1. Score Distribution ──────────────────────────────────────────────────
    def render_score_distribution(self, scores: pd.Series, chart_id: str = "score_distribution") -> str:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(scores.dropna(), bins=30, color=PALETTE["primary"],
                edgecolor='white', linewidth=0.5, alpha=0.85, zorder=3)
        # Add KDE line
        scores_clean = scores.dropna()
        if len(scores_clean) > 5:
            from scipy.stats import gaussian_kde
            kde_x = np.linspace(scores_clean.min(), scores_clean.max(), 200)
            kde = gaussian_kde(scores_clean, bw_method=0.3)
            ax2 = ax.twinx()
            ax2.plot(kde_x, kde(kde_x), color=PALETTE["secondary"], linewidth=2)
            ax2.set_ylabel("Density", fontsize=9, color=PALETTE["text_muted"])
            ax2.set_yticks([])
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
        apply_style(ax, "Model Score Distribution", "Model Score", "Count")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
        return self._save(fig, chart_id)

    # ── 2. Bad Rate by Score Band ──────────────────────────────────────────────
    def render_bad_rate_by_score_band(self, band_data: list[dict],
                                       chart_id: str = "bad_rate_by_score_band") -> str:
        # band_data: [{"score_band": "<600", "bad_rate": 0.12, "n": 45}, ...]
        df = pd.DataFrame(band_data)
        # Ensure correct order
        df['score_band'] = pd.Categorical(df['score_band'],
                                           categories=SCORE_BAND_ORDER, ordered=True)
        df = df.sort_values('score_band')

        fig, ax = plt.subplots(figsize=(7, 4))
        colors = [PALETTE["danger"] if r > 0.10 else
                  PALETTE["warning"] if r > 0.05 else
                  PALETTE["success"] for r in df['bad_rate']]
        bars = ax.bar(df['score_band'], df['bad_rate'] * 100, color=colors,
                      edgecolor='white', linewidth=0.5, zorder=3, width=0.55)

        # Add value labels on bars
        for bar, row in zip(bars, df.itertuples()):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                    f"{row.bad_rate*100:.1f}%", ha='center', va='bottom',
                    fontsize=9, color=PALETTE["text"], fontweight='bold')
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height()/2,
                    f"n={row.n}", ha='center', va='center',
                    fontsize=8, color='white', fontweight='bold')

        apply_style(ax, "Bad Rate by Score Band", "Score Band", "Bad Rate (%)")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
        return self._save(fig, chart_id)

    # ── 3. Approval Rate by Risk Band ─────────────────────────────────────────
    def render_approval_by_risk_band(self, data: list[dict],
                                      chart_id: str = "approval_by_risk_band") -> str:
        df = pd.DataFrame(data)
        df['risk_rating'] = pd.Categorical(df['risk_rating'],
                                            categories=RISK_RATING_ORDER, ordered=True)
        df = df.sort_values('risk_rating')

        fig, ax = plt.subplots(figsize=(7, 4))
        x = np.arange(len(df))
        width = 0.35
        ax.bar(x - width/2, df['approval_rate'] * 100, width, label='Approval Rate',
               color=PALETTE["success"], edgecolor='white', zorder=3)
        if 'bad_rate' in df.columns:
            ax.bar(x + width/2, df['bad_rate'] * 100, width, label='Bad Rate',
                   color=PALETTE["danger"], edgecolor='white', zorder=3)
        ax.set_xticks(x)
        ax.set_xticklabels(df['risk_rating'])
        ax.legend(fontsize=9)
        apply_style(ax, "Approval & Bad Rate by Risk Rating",
                    "Risk Rating", "Rate (%)")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
        return self._save(fig, chart_id)

    # ── 4. ROC Curve ──────────────────────────────────────────────────────────
    def render_roc_curve(self, fpr: list, tpr: list, auc: float,
                          chart_id: str = "roc_curve") -> str:
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.plot(fpr, tpr, color=PALETTE["primary"], linewidth=2.5,
                label=f"Model (AUC = {auc:.3f})")
        ax.plot([0, 1], [0, 1], color=PALETTE["neutral"], linewidth=1.5,
                linestyle='--', label="Random (AUC = 0.500)")
        ax.fill_between(fpr, tpr, alpha=0.08, color=PALETTE["primary"])
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1.02])
        ax.legend(loc='lower right', fontsize=10)
        apply_style(ax, "ROC Curve", "False Positive Rate", "True Positive Rate")
        return self._save(fig, chart_id)

    # ── 5. Calibration Plot ────────────────────────────────────────────────────
    def render_calibration_plot(self, calib_data: list[dict],
                                  chart_id: str = "calibration") -> str:
        # calib_data: [{"mean_predicted_pd": 0.04, "actual_default_rate": 0.05}, ...]
        df = pd.DataFrame(calib_data)
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.scatter(df['mean_predicted_pd'] * 100, df['actual_default_rate'] * 100,
                   color=PALETTE["primary"], s=80, zorder=5, label="Score Bands")
        # Perfect calibration line
        max_val = max(df['mean_predicted_pd'].max(), df['actual_default_rate'].max()) * 100
        ax.plot([0, max_val], [0, max_val], color=PALETTE["neutral"],
                linewidth=1.5, linestyle='--', label="Perfect Calibration")
        # Connect dots
        ax.plot(df['mean_predicted_pd'] * 100, df['actual_default_rate'] * 100,
                color=PALETTE["primary"], linewidth=1, alpha=0.4)
        ax.legend(fontsize=9)
        apply_style(ax, "Calibration: Predicted PD vs Observed Default Rate",
                    "Mean Predicted PD (%)", "Observed Default Rate (%)")
        return self._save(fig, chart_id)

    # ── 6. DPD Distribution ────────────────────────────────────────────────────
    def render_dpd_distribution(self, dpd_data: list[dict],
                                  chart_id: str = "dpd_distribution") -> str:
        df = pd.DataFrame(dpd_data)
        df['bucket'] = pd.Categorical(df['bucket'],
                                       categories=DPD_BUCKET_ORDER, ordered=True)
        df = df.sort_values('bucket')

        colors = [PALETTE["success"], PALETTE["warning"],
                  PALETTE["warning"], PALETTE["danger"], PALETTE["danger"]]
        fig, ax = plt.subplots(figsize=(7, 4))
        bars = ax.bar(df['bucket'], df['pct'], color=colors[:len(df)],
                      edgecolor='white', linewidth=0.5, zorder=3, width=0.55)
        for bar, row in zip(bars, df.itertuples()):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                    f"{row.pct:.1f}%", ha='center', va='bottom',
                    fontsize=9, fontweight='bold', color=PALETTE["text"])
        apply_style(ax, "DPD Bucket Distribution", "DPD Bucket", "Share of Portfolio (%)")
        return self._save(fig, chart_id)

    # ── 7. PSI Bar Chart (feature drift) ──────────────────────────────────────
    def render_psi_chart(self, psi_data: list[dict],
                          chart_id: str = "psi_features") -> str:
        # psi_data: [{"feature": "model_score", "psi": 0.08, "status": "stable"}, ...]
        df = pd.DataFrame(psi_data).sort_values('psi', ascending=True)
        colors = [PALETTE["danger"] if r == "unstable" else
                  PALETTE["warning"] if r == "monitor" else
                  PALETTE["success"] for r in df['status']]

        fig, ax = plt.subplots(figsize=(8, max(4, len(df) * 0.45)))
        bars = ax.barh(df['feature'], df['psi'], color=colors,
                       edgecolor='white', linewidth=0.5, zorder=3)

        # Threshold lines
        ax.axvline(0.10, color=PALETTE["warning"], linewidth=1.5,
                   linestyle='--', label='Monitor (0.10)', zorder=5)
        ax.axvline(0.25, color=PALETTE["danger"], linewidth=1.5,
                   linestyle='--', label='Unstable (0.25)', zorder=5)

        for bar, row in zip(bars, df.itertuples()):
            ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height()/2,
                    f"{row.psi:.3f}", va='center', fontsize=8.5, color=PALETTE["text"])

        ax.legend(fontsize=9, loc='lower right')
        apply_style(ax, "Population / Feature Drift (PSI / CSI)",
                    "PSI Value", "Feature")
        return self._save(fig, chart_id)

    # ── 8. KS Plot ────────────────────────────────────────────────────────────
    def render_ks_plot(self, df: pd.DataFrame, score_col: str, target_col: str,
                        ks_stat: float, chart_id: str = "ks_plot") -> str:
        goods = df.loc[df[target_col] == 0, score_col].sort_values()
        bads = df.loc[df[target_col] == 1, score_col].sort_values()
        all_scores = np.sort(df[score_col].dropna().unique())

        cum_goods = np.array([(goods <= s).mean() for s in all_scores])
        cum_bads = np.array([(bads <= s).mean() for s in all_scores])

        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.plot(all_scores, cum_goods, color=PALETTE["success"],
                linewidth=2, label='Cumulative Good %')
        ax.plot(all_scores, cum_bads, color=PALETTE["danger"],
                linewidth=2, label='Cumulative Bad %')

        # Mark KS point
        ks_idx = np.argmax(np.abs(cum_goods - cum_bads))
        ax.axvline(all_scores[ks_idx], color=PALETTE["neutral"],
                   linewidth=1.5, linestyle='--', alpha=0.7)
        ax.annotate(f"KS = {ks_stat:.3f}", xy=(all_scores[ks_idx], 0.5),
                    xytext=(all_scores[ks_idx] + 20, 0.4), fontsize=9,
                    arrowprops=dict(arrowstyle='->', color=PALETTE["text_muted"]))

        ax.fill_between(all_scores, cum_goods, cum_bads, alpha=0.08, color=PALETTE["primary"])
        ax.legend(fontsize=9)
        apply_style(ax, "KS Plot — Good vs Bad Score Separation",
                    "Model Score", "Cumulative %")
        return self._save(fig, chart_id)

    # ── 9. Decile Lift Chart ───────────────────────────────────────────────────
    def render_decile_lift(self, decile_data: list[dict],
                            chart_id: str = "decile_lift") -> str:
        df = pd.DataFrame(decile_data)
        fig, ax = plt.subplots(figsize=(8, 4))
        colors = [PALETTE["danger"] if l > 2 else
                  PALETTE["warning"] if l > 1 else
                  PALETTE["success"] for l in df['lift']]
        bars = ax.bar(df['decile'].astype(str), df['lift'], color=colors,
                      edgecolor='white', linewidth=0.5, zorder=3, width=0.65)
        ax.axhline(1.0, color=PALETTE["neutral"], linewidth=1.5,
                   linestyle='--', label='No lift (1.0x)')
        for bar, row in zip(bars, df.itertuples()):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                    f"{row.lift:.2f}x", ha='center', va='bottom',
                    fontsize=8.5, fontweight='bold', color=PALETTE["text"])
        ax.legend(fontsize=9)
        apply_style(ax, "Lift by Score Decile (Decile 1 = Highest Score)",
                    "Score Decile", "Lift")
        return self._save(fig, chart_id)

    # ── 10. Segment Comparison (bad rate per segment) ─────────────────────────
    def render_segment_bad_rate(self, segment_data: list[dict], segment_col: str,
                                  chart_id: str = None) -> str:
        if chart_id is None:
            chart_id = f"segment_{segment_col}_bad_rate"
        df = pd.DataFrame(segment_data)

        fig, ax = plt.subplots(figsize=(max(6, len(df) * 1.2), 4))
        colors = [PALETTE["danger"] if r > 0.10 else
                  PALETTE["warning"] if r > 0.05 else
                  PALETTE["success"] for r in df['bad_rate']]
        bars = ax.bar(df['segment_value'], df['bad_rate'] * 100, color=colors,
                      edgecolor='white', linewidth=0.5, zorder=3, width=0.6)
        for bar, row in zip(bars, df.itertuples()):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                    f"{row.bad_rate*100:.1f}%\nn={row.count}",
                    ha='center', va='bottom', fontsize=8, color=PALETTE["text"])
        apply_style(ax, f"Bad Rate by {segment_col.replace('_', ' ').title()}",
                    segment_col.replace('_', ' ').title(), "Bad Rate (%)")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
        plt.xticks(rotation=15, ha='right')
        return self._save(fig, chart_id)

    # ── 11. PD Distribution Histogram ─────────────────────────────────────────
    def render_pd_distribution(self, pd_vals: pd.Series,
                                  chart_id: str = "pd_distribution") -> str:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(pd_vals.dropna() * 100, bins=30, color=PALETTE["secondary"],
                edgecolor='white', linewidth=0.5, alpha=0.85, zorder=3)
        apply_style(ax, "Predicted PD Distribution",
                    "Probability of Default (%)", "Count")
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}%"))
        return self._save(fig, chart_id)

    # ── 12. Feature Distribution Grid (with vs without baseline) ──────────────
    def render_feature_grid(self, df_current: pd.DataFrame, feature_cols: list[str],
                              df_baseline: pd.DataFrame = None,
                              chart_id: str = "feature_distributions") -> str:
        n = len(feature_cols)
        ncols = min(3, n)
        nrows = (n + ncols - 1) // ncols
        fig, axes = plt.subplots(nrows, ncols, figsize=(ncols * 4, nrows * 3))
        axes = axes.flatten() if n > 1 else [axes]

        for i, col in enumerate(feature_cols):
            ax = axes[i]
            data = df_current[col].dropna()
            ax.hist(data, bins=20, alpha=0.7, color=PALETTE["primary"],
                    label="Current", density=True, zorder=3)
            if df_baseline is not None and col in df_baseline.columns:
                base_data = df_baseline[col].dropna()
                ax.hist(base_data, bins=20, alpha=0.5, color=PALETTE["baseline"],
                        label="Baseline", density=True, zorder=2)
            ax.set_title(col.replace('_', ' ').title(), fontsize=9, fontweight='bold',
                          color=PALETTE["text"])
            ax.tick_params(labelsize=7)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            if i == 0 and df_baseline is not None:
                ax.legend(fontsize=7)

        # Hide unused axes
        for j in range(n, len(axes)):
            axes[j].set_visible(False)

        plt.suptitle("Feature Distributions (Current" +
                     (" vs Baseline)" if df_baseline is not None else ")"),
                     fontsize=11, fontweight='bold', color=PALETTE["text"], y=1.01)
        plt.tight_layout()
        return self._save(fig, chart_id)
```

### Updated `ChartPayload` schema — includes image URL
```python
class ChartPayload(BaseModel):
    chart_id: str
    chart_type: str       # "bar", "line", "scatter", "histogram", "roc", "ks"
    title: str
    subtitle: Optional[str]
    # JSON data for frontend interactive rendering
    series: list[dict]
    x_label: Optional[str]
    y_label: Optional[str]
    # Image URL for direct viewing / reports
    image_url: Optional[str]     # e.g. "/static/runs/{run_id}/charts/roc_curve.png"
    image_path: Optional[str]    # absolute filesystem path
    # Optional base64 for embedding in responses without static serving
    image_base64: Optional[str]  # only populated if explicitly requested
```

### Static file serving — add to main.py
```python
# main.py — add after app creation
from fastapi.staticfiles import StaticFiles

# Serve all files in storage/ directory as static
# Charts accessible at: GET /static/runs/{run_id}/charts/{chart_id}.png
app.mount("/static", StaticFiles(directory="storage"), name="static")
```

### Chart generation in run_service.py
```python
# Inside run_service.py — after metrics are computed

def _render_all_charts(self, run_id: str, df: pd.DataFrame,
                        mapping: ColumnMapping,
                        metric_results: dict,
                        df_baseline: pd.DataFrame = None) -> list[ChartPayload]:
    charts_dir = settings.runs_dir / run_id / "charts"
    renderer = ChartRenderer(charts_dir)
    payloads = []

    def make_url(path: str) -> str:
        rel = Path(path).relative_to("storage")
        return f"/static/{rel}"

    # Score distribution
    if mapping.prediction_score and mapping.prediction_score in df.columns:
        path = renderer.render_score_distribution(df[mapping.prediction_score])
        payloads.append(ChartPayload(chart_id="score_distribution",
            chart_type="histogram", title="Model Score Distribution",
            series=[], image_url=make_url(path), image_path=path))

    # PD distribution
    if mapping.prediction_probability and mapping.prediction_probability in df.columns:
        path = renderer.render_pd_distribution(df[mapping.prediction_probability])
        payloads.append(ChartPayload(chart_id="pd_distribution",
            chart_type="histogram", title="Predicted PD Distribution",
            series=[], image_url=make_url(path), image_path=path))

    # ROC curve
    roc = metric_results.get("perf_auc", {})
    if roc.get("chart_data", {}).get("fpr"):
        path = renderer.render_roc_curve(
            fpr=roc["chart_data"]["fpr"],
            tpr=roc["chart_data"]["tpr"],
            auc=roc["scalar_value"]
        )
        payloads.append(ChartPayload(chart_id="roc_curve",
            chart_type="roc", title="ROC Curve",
            series=[], image_url=make_url(path), image_path=path))

    # KS plot
    ks = metric_results.get("perf_ks", {})
    if ks.get("scalar_value") and mapping.target:
        path = renderer.render_ks_plot(
            df=df,
            score_col=mapping.prediction_score,
            target_col=mapping.target,
            ks_stat=ks["scalar_value"]
        )
        payloads.append(ChartPayload(chart_id="ks_plot",
            chart_type="ks", title="KS Plot",
            series=[], image_url=make_url(path), image_path=path))

    # Bad rate by score band
    band_metric = metric_results.get("perf_bad_rate_by_score_band", {})
    if band_metric.get("table_data"):
        path = renderer.render_bad_rate_by_score_band(band_metric["table_data"])
        payloads.append(ChartPayload(chart_id="bad_rate_by_score_band",
            chart_type="bar", title="Bad Rate by Score Band",
            series=[], image_url=make_url(path), image_path=path))

    # Approval by risk band
    risk_metric = metric_results.get("strategy_decision_by_risk_band", {})
    if risk_metric.get("table_data"):
        path = renderer.render_approval_by_risk_band(risk_metric["table_data"])
        payloads.append(ChartPayload(chart_id="approval_by_risk_band",
            chart_type="bar", title="Approval & Bad Rate by Risk Rating",
            series=[], image_url=make_url(path), image_path=path))

    # Calibration
    calib = metric_results.get("calib_observed_vs_predicted", {})
    if calib.get("table_data"):
        path = renderer.render_calibration_plot(calib["table_data"])
        payloads.append(ChartPayload(chart_id="calibration",
            chart_type="scatter", title="Calibration: Predicted vs Observed",
            series=[], image_url=make_url(path), image_path=path))

    # DPD distribution
    dpd = metric_results.get("delinq_bucket_distribution", {})
    if dpd.get("table_data"):
        path = renderer.render_dpd_distribution(dpd["table_data"])
        payloads.append(ChartPayload(chart_id="dpd_distribution",
            chart_type="bar", title="DPD Bucket Distribution",
            series=[], image_url=make_url(path), image_path=path))

    # Decile lift
    decile = metric_results.get("perf_decile_table", {})
    if decile.get("table_data"):
        path = renderer.render_decile_lift(decile["table_data"])
        payloads.append(ChartPayload(chart_id="decile_lift",
            chart_type="bar", title="Lift by Score Decile",
            series=[], image_url=make_url(path), image_path=path))

    # PSI chart (if baseline)
    psi_metrics = [r for k, r in metric_results.items()
                   if k.startswith("psi_") or k.startswith("csi_")]
    if psi_metrics:
        psi_data = [{"feature": r["metric_key"].replace("psi_","").replace("csi_",""),
                     "psi": r["scalar_value"],
                     "status": r["status"]} for r in psi_metrics if r.get("scalar_value")]
        if psi_data:
            path = renderer.render_psi_chart(psi_data)
            payloads.append(ChartPayload(chart_id="psi_features",
                chart_type="bar", title="Feature Drift (PSI / CSI)",
                series=[], image_url=make_url(path), image_path=path))

    # Segment bad rate charts (one per segment column)
    for seg_col in mapping.segment_fields:
        seg_data = [...]   # filter segment_results for this column
        if seg_data:
            path = renderer.render_segment_bad_rate(seg_data, seg_col)
            payloads.append(ChartPayload(
                chart_id=f"segment_{seg_col}_bad_rate",
                chart_type="bar",
                title=f"Bad Rate by {seg_col.replace('_',' ').title()}",
                series=[], image_url=make_url(path), image_path=path))

    # Feature distribution grid
    if mapping.feature_fields:
        path = renderer.render_feature_grid(
            df_current=df,
            feature_cols=mapping.feature_fields[:9],  # max 9 in grid
            df_baseline=df_baseline
        )
        payloads.append(ChartPayload(chart_id="feature_distributions",
            chart_type="grid", title="Feature Distributions",
            series=[], image_url=make_url(path), image_path=path))

    return payloads
```

### New endpoint — return image directly
```python
# Add to runs.py router

@router.get("/{run_id}/charts/{chart_id}/image")
async def get_chart_image(run_id: str, chart_id: str):
    """Return chart PNG image directly (viewable in browser)."""
    from fastapi.responses import FileResponse
    chart_path = settings.runs_dir / run_id / "charts" / f"{chart_id}.png"
    if not chart_path.exists():
        raise HTTPException(status_code=404, detail=f"Chart '{chart_id}' not found for run '{run_id}'")
    return FileResponse(chart_path, media_type="image/png")

@router.get("/{run_id}/charts")
async def list_charts(run_id: str):
    """List all available charts for a run with image URLs."""
    charts = run_store.get_charts(run_id)
    return APIResponse(success=True, data=charts)
```

### Add to requirements.txt
```
matplotlib==3.8.4
seaborn==0.13.2
```

---

## SECTION 30: SUMMARY OF ALL ADDITIONS (v2.1 vs v2.0)

| Addition | Section | Impact |
|----------|---------|--------|
| Dynamic CSV handling (pattern-based heuristics) | 27 | Backend works on ANY CSV, not just sample |
| Graceful degradation for unknown columns | 27 | No crashes on unfamiliar datasets |
| `ColumnSuggestion` with confidence + alternatives | 28 | Frontend can render a rich mapping UI |
| `SaveMappingRequest` with accept_all_auto flag | 28 | One-click accept or manual override |
| `ChartRenderer` class (matplotlib, 12 chart types) | 29 | Backend generates PNG images directly |
| `PALETTE` color system for consistent chart styling | 29 | Professional-looking charts |
| Static file serving for chart images | 29 | Charts viewable at /static/... URLs |
| `GET /runs/{run_id}/charts/{chart_id}/image` endpoint | 29 | Direct image URL access |
| `image_url` field in `ChartPayload` | 29 | Every chart response includes image URL |
| matplotlib + seaborn added to requirements | 29 | Required for chart rendering |

---

## SECTION 31: COMPLETE MODULE COVERAGE — 7 MISSING MODULES

This section fills the 7 gaps identified in the module cross-check audit. These are not optional niceties — they are the modules that make the platform feel complete and demo-ready at every priority tier (P0 through P2).

---

### MODULE 6 / 20 — Report Generation (PDF + HTML)

**Priority:** P0 (MVP) — required for demo  
**New files:** `app/services/report_service.py`, `app/templates/reports/` (Jinja2 HTML templates)  
**Dependencies:** `weasyprint`, `jinja2` (already added to requirements)

#### Report types
```python
class ReportType(str, Enum):
    EXECUTIVE_SUMMARY = "executive_summary"    # 1-2 page board-ready summary
    FULL_TECHNICAL    = "full_technical"        # complete monitoring report
    DATA_QUALITY      = "data_quality"          # data-only, no model performance
    SR_11_7_CHECKLIST = "sr_11_7"              # SR 11-7 compliant format with section headers
    IFRS9_MONITORING  = "ifrs9"                # IFRS 9 calibration-focused report

class ReportFormat(str, Enum):
    PDF  = "pdf"
    HTML = "html"
```

#### Report service contract
```python
class ReportService:
    def generate(
        self,
        run_id: str,
        report_type: ReportType,
        fmt: ReportFormat,
        run_store: MonitorRunStore,
    ) -> Path:
        """
        1. Load all run artifacts from storage/{run_id}/*.json
        2. Render Jinja2 HTML template with run data
        3. If fmt=PDF: pass HTML through WeasyPrint → bytes → save to storage/runs/{run_id}/report_{type}.pdf
        4. If fmt=HTML: save rendered HTML to storage/runs/{run_id}/report_{type}.html
        5. Return the saved file path
        """
```

#### HTML template structure (Jinja2)
Each template (`templates/reports/executive_summary.html`, `templates/reports/sr_11_7.html`, etc.) receives the complete `CompleteRunResult` as template context and includes:
- Embedded base64 chart images (generated by `ChartRenderer` during report build, NOT pre-stored)
- Metric summary tables
- Alert and findings sections
- Inline CSS (no external dependencies — report must be self-contained for PDF conversion)

#### Chart embedding in reports
During report generation, `ReportService` calls `ChartRenderer.render_to_base64()` for each chart in the run's `charts.json` and embeds the base64 PNG directly in the HTML as `<img src="data:image/png;base64,...">`. WeasyPrint handles this transparently for PDF conversion.

#### API endpoints (add to `/api/v1`)
```
POST /runs/{run_id}/reports/generate
  Body: {report_type: "executive_summary|full_technical|sr_11_7|ifrs9", format: "pdf|html"}
  Response: APIResponse[{report_id, file_path, download_url, size_bytes, generated_at}]

GET  /runs/{run_id}/reports
  Response: APIResponse[list[ReportMeta]]

GET  /runs/{run_id}/reports/{report_id}/download
  Response: binary file (Content-Type: application/pdf or text/html)
  Headers: Content-Disposition: attachment; filename="report_{run_id}_{type}.pdf"
```

#### SR 11-7 report sections (auto-populated)
The SR 11-7 template must include these labelled sections, each auto-populated from run artifacts:
1. Model identification and monitoring scope
2. Data quality assessment
3. Population stability (PSI results)
4. Model performance (AUC, Gini, KS vs development baseline)
5. Calibration assessment (Brier score, calibration ratio)
6. Segmentation analysis
7. Business / strategy metrics (approval rate, bad rate)
8. Alert summary
9. Key findings and recommendations
10. Monitoring conclusion (HEALTHY / WATCH / DETERIORATING / CRITICAL)

---

### MODULE 8 — Score Distribution Analysis (dedicated)

**Priority:** P1  
**New metric key:** `score_distribution_analysis`  
**Metric file addition:** `app/metrics/implementations/score_distribution.py`

#### Computations required
```python
# 1. Score histogram data — for chart_score_distribution
histogram_data = {
    "bins": [...],         # 20 equal-width bins across score range
    "counts": [...],
    "pcts": [...],
    "by_decision": {       # if decision mapped
        "APPROVED": {"counts": [...], "pcts": [...]},
        "DECLINED": {"counts": [...], "pcts": [...]},
    }
}

# 2. Score band counts and bad rates (already covered in strategy — reference here)
band_table = [
    {"band": "<600", "n": 69, "bad_rate": ..., "approval_rate": 0.812, "pct_of_portfolio": 0.350},
    {"band": "600-700", "n": 68, ...},
    {"band": "700-800", "n": 47, ...},
    {"band": "800+", "n": 13, ...},
]

# 3. Score monotonicity check
# Verify bad_rate is strictly decreasing as score_band increases
# IMPORTANT for this dataset: order bands correctly: <600, 600-700, 700-800, 800+
monotonic = all(
    band_table[i]["bad_rate"] >= band_table[i+1]["bad_rate"]
    for i in range(len(band_table) - 1)
)
monotonicity_status = "pass" if monotonic else "FAIL — rank ordering broken"

# 4. Score band migration matrix (only if baseline exists)
# Rows = baseline score band, Cols = current score band
# Each cell = count of accounts that moved from band X to band Y
# For single dataset: skip and return None

# 5. Approved vs declined score distribution split
approved_scores = df.loc[df[decision_col]=="APPROVED", score_col].describe()
declined_scores = df.loc[df[decision_col]=="DECLINED", score_col].describe()
```

#### Chart outputs
- `chart_score_histogram` — overlaid histograms: approved (green), declined (red), all (grey)
- `chart_score_band_table` — bar chart: score_band → [bad_rate, approval_rate] grouped bars
- `chart_score_monotonicity` — line plot of bad_rate vs score_band with pass/fail annotation

---

### MODULE 11 — Statistical Testing Suite

**Priority:** P1  
**New file:** `app/metrics/implementations/statistical_tests.py`

All tests use `scipy.stats`. Return a unified table of test results.

#### Tests to implement

```python
class StatTestResult(BaseModel):
    test_name: str
    test_key: str
    statistic: float
    p_value: float
    degrees_of_freedom: Optional[int]
    conclusion: str     # plain-English: "Fail to reject H₀ — distributions are similar"
    pass_fail: str      # "pass" (H₀ not rejected) | "fail" (H₀ rejected at α=0.05)
    alpha: float = 0.05
    small_sample_warning: bool   # True if n < 30 in any cell/group
    notes: Optional[str]
```

#### Test 1: Hosmer-Lemeshow (calibration goodness-of-fit)
```python
from scipy import stats

def hosmer_lemeshow_test(y_true, y_prob, n_groups=10):
    """
    H₀: The model is well-calibrated.
    Groups are deciles of predicted probability.
    HL statistic ~ χ²(df = n_groups - 2) under H₀.
    For our dataset (n=197, 11 bads): use n_groups=5 to avoid empty bins.
    """
    df_hl = pd.DataFrame({"y": y_true, "p": y_prob})
    df_hl["decile"] = pd.qcut(df_hl["p"], q=n_groups, duplicates="drop", labels=False)
    grouped = df_hl.groupby("decile").agg(n=("y","count"), obs=("y","sum"), exp=("p","sum"))
    hl_stat = ((grouped["obs"] - grouped["exp"])**2 / (grouped["n"] * grouped["exp"] / grouped["n"] * (1 - grouped["exp"]/grouped["n"]))).sum()
    df_free = len(grouped) - 2
    p_value = stats.chi2.sf(hl_stat, df=df_free)
    return hl_stat, p_value, df_free
```

#### Test 2: Chi-square for categorical drift (requires baseline)
```python
# For each categorical column (loan_purpose, home_ownership, risk_rating, etc.)
# Compare frequency distributions between baseline and current
from scipy.stats import chi2_contingency
observed = pd.crosstab(current_series, columns="count")
expected = baseline_freqs * len(current_series)
stat, p, dof, _ = chi2_contingency(pd.DataFrame({"obs": observed, "exp": expected}))
```

#### Test 3: Binomial test — bad rate per score band vs expected
```python
# H₀: bad rate in band = overall_bad_rate (or baseline band rate)
from scipy.stats import binomtest
for band in score_bands:
    sub = df[df[score_band_col] == band]
    result = binomtest(k=int(sub[target].sum()), n=len(sub), p=overall_bad_rate, alternative="greater")
    # "greater" = test if observed bad rate is significantly HIGHER than expected
```

#### Test 4: Fisher's exact test — for small-sample bands (n < 30)
```python
# For segments with small n, use Fisher's exact instead of chi-square
from scipy.stats import fisher_exact
# 2x2 contingency: [[TP, FP], [FN, TN]] or [[bads_in_band, goods_in_band], [bads_overall, goods_overall]]
oddsratio, p_value = fisher_exact([[a, b], [c, d]])
```

#### Test 5: Mann-Whitney U — score distribution, approved vs declined
```python
from scipy.stats import mannwhitneyu
approved_scores = df.loc[df[decision_col]=="APPROVED", score_col]
declined_scores = df.loc[df[decision_col]=="DECLINED", score_col]
stat, p = mannwhitneyu(approved_scores, declined_scores, alternative="greater")
# "greater" = approved scores are stochastically greater than declined (expected)
```

#### Multiple testing correction
```python
from scipy.stats import false_discovery_control
# Apply Bonferroni or BH-FDR correction to all p-values when running multiple tests
p_values = [t.p_value for t in test_results]
corrected = false_discovery_control(p_values, method="bh")  # Benjamini-Hochberg
```

#### API endpoint (add to runs router)
```
GET /runs/{run_id}/stat-tests
  Response: APIResponse[{tests: list[StatTestResult], correction_method: str, n_significant: int}]
```

---

### MODULE 14 — Vintage & Cohort Analysis (Roll Rate Focus)

**Priority:** P2  
**New file:** `app/metrics/implementations/vintage.py`

#### Important constraint for this dataset
`application_time` contains `"46:27.6"` for ALL 197 rows — same malformed value across the entire dataset. True vintage/cohort curves (which require grouping by origination date) are therefore **not possible**. The system must:
1. Detect this in the profiler (all rows same malformed timestamp = time-series analysis impossible)
2. Return a graceful response from vintage endpoints: `{"cohort_curves": null, "reason": "event_time column not parseable or contains single unique value — cohort analysis requires distinct origination dates", "roll_rate_matrix": {...}}`
3. Still compute and return the **roll rate transition matrix** from `past_due_days` — this does not require timestamps and is valuable on its own.

#### Roll rate transition matrix (the real deliverable for this dataset)
```python
def compute_roll_rate_matrix(df: pd.DataFrame, dpd_col: str) -> dict:
    """
    For a single snapshot dataset, the roll rate matrix shows
    the current distribution across DPD buckets — a cross-sectional
    view, not a true time-series roll rate (which needs two snapshots).
    Return it clearly labelled as 'DPD bucket distribution (cross-sectional)'.
    """
    def dpd_bucket(d: float) -> str:
        if d == 0: return "Current (0 DPD)"
        elif d <= 29: return "1-29 DPD"
        elif d <= 59: return "30-59 DPD"    # Note: 50 DPD placed here
        elif d <= 89: return "60-89 DPD"
        else: return "90+ DPD"

    bucket_order = ["Current (0 DPD)", "1-29 DPD", "30-59 DPD", "60-89 DPD", "90+ DPD"]
    df["_dpd_bucket"] = df[dpd_col].apply(dpd_bucket)
    counts = df["_dpd_bucket"].value_counts()

    return {
        "type": "cross_sectional_dpd_distribution",   # NOT a true roll rate — be explicit
        "note": "True roll rate matrix requires two time-snapshot datasets. This shows current DPD bucket distribution.",
        "buckets": [
            {
                "bucket": b,
                "count": int(counts.get(b, 0)),
                "pct": round(counts.get(b, 0) / len(df) * 100, 2),
                "cumulative_pct": None,  # computed post-loop
            }
            for b in bucket_order
        ],
        "severe_delinquency_rate": round((df[dpd_col] >= 90).mean(), 4),
    }
```

#### Cohort architecture (skeleton — ready for valid timestamps)
```python
class VintageService:
    def analyze(self, df, time_col, target_col, dpd_col) -> dict:
        # Step 1: Check if time_col is parseable
        if not self._is_time_parseable(df[time_col]):
            return {
                "cohort_curves": None,
                "reason": "event_time not parseable. Cohort curves require valid origination dates.",
                "roll_rate_matrix": self._compute_roll_rate(df, dpd_col),
            }
        # Step 2: If parseable, group by month/quarter and compute cumulative DR per cohort
        # (implement when valid timestamp data is available)
        ...

    def _is_time_parseable(self, series: pd.Series) -> bool:
        """Returns False if all values are the same, or if <80% parse successfully."""
        if series.nunique() <= 1:
            return False   # all rows same value = no useful time variation
        try:
            parsed = pd.to_datetime(series, errors="coerce")
            return parsed.notna().mean() >= 0.8
        except:
            return False
```

#### API endpoint (add to runs router)
```
GET /runs/{run_id}/vintage
  Response: APIResponse[VintageResult]
  # Returns roll_rate_matrix always, cohort_curves if timestamps valid
```

---

### MODULE 15 — Override Analysis

**Priority:** P2  
**New file:** `app/metrics/implementations/override.py`  
**Data insight:** 56 of 69 score<600 accounts are APPROVED (81.2% override rate). Override bad rate (1.8%) is lower than normal approved bad rate (7.3%) — this is a compelling, counterintuitive demo finding.

#### Override definition
An "override" is any account where the **model-implied decision** conflicts with the **actual business decision**:
- **Model-implied decision** = derived from `model_score` vs a configurable score threshold (`override_score_cutoff`, default: minimum of the second-lowest `score_band`, i.e. 600 for this dataset)
- Override (positive) = `model_score < cutoff` AND `application_status = APPROVED`
- Override (negative) = `model_score >= cutoff` AND `application_status = DECLINED`

```python
class OverrideAnalysis(BaseModel):
    score_cutoff_used: int
    total_model_declines: int     # count where model_score < cutoff
    total_model_approves: int

    # Override (positive): model says decline, business approved
    positive_override_count: int
    positive_override_rate: float    # of total model-declines
    positive_override_bad_rate: float
    positive_override_avg_score: float

    # Normal approved (model and business agree)
    normal_approved_count: int
    normal_approved_bad_rate: float
    normal_approved_avg_score: float

    # Override (negative): model says approve, business declined
    negative_override_count: int
    negative_override_rate: float

    # Key insight flag
    override_performing_better: bool   # True if positive_override_bad_rate < normal_approved_bad_rate
    insight_narrative: str             # deterministic: "Overridden accounts in this dataset show LOWER bad rate than
                                       # model-approved accounts (1.8% vs 7.3%), suggesting underwriters are
                                       # exercising sound judgment for this risk segment. Review override criteria."

    # By segment breakdown
    override_by_segment: list[dict]    # [{segment_col, segment_val, override_count, override_bad_rate}]
```

#### Configurable threshold
The `override_score_cutoff` should be configurable in the monitor config (default = lowest `score_band` upper boundary = 600). The user should be able to test different cutoffs via a `cutoff_sensitivity` array — run the override analysis at 550, 600, 650, 700 and return the override rate and bad rate at each threshold.

#### API endpoint (add to runs router)
```
GET /runs/{run_id}/override-analysis?score_cutoff=600
  Response: APIResponse[OverrideAnalysis]
```

---

### MODULE 17 — Time Series Monitoring (Architecture Skeleton)

**Priority:** P2  
**New file:** `app/services/timeseries_service.py`

#### Status for this dataset
`application_time = "46:27.6"` for ALL 197 rows — identical, malformed. Time series monitoring is **not possible** with this dataset. The module must be fully implemented architecturally but return a clean "not available" response for this dataset.

#### Architecture design
The time series engine activates only when:
1. `event_time` role is mapped
2. The column is parseable as datetime
3. At least 2 distinct time periods exist in the data (e.g., 2 months)

```python
class TimeSeriesConfig(BaseModel):
    period_freq: str = "M"    # "M"=monthly, "Q"=quarterly, "W"=weekly
    min_periods_required: int = 2
    metrics_to_track: list[str] = ["perf_auc", "perf_gini", "perf_ks", "psi_model_score",
                                    "strategy_approval_rate", "strategy_bad_rate_approved"]

class TimeSeriesResult(BaseModel):
    available: bool
    unavailable_reason: Optional[str]
    periods: Optional[list[str]]          # e.g., ["2024-01", "2024-02", "2024-03"]
    metric_trends: Optional[dict]         # {metric_key: [{period, value, status}]}
    trend_direction: Optional[dict]       # {metric_key: "improving|deteriorating|stable"}
    chart_data: Optional[list[ChartPayload]]  # line charts, one per metric
```

#### Trend detection logic (for when timestamps are valid)
```python
def detect_trend(values: list[float], direction: str = "higher_is_better") -> str:
    """Simple linear trend: fit OLS slope, classify."""
    if len(values) < 3:
        return "insufficient_data"
    x = np.arange(len(values))
    slope = np.polyfit(x, values, 1)[0]
    threshold = np.std(values) * 0.1   # 10% of std dev = meaningful change
    if abs(slope) < threshold:
        return "stable"
    improving = slope > 0 if direction == "higher_is_better" else slope < 0
    return "improving" if improving else "deteriorating"
```

#### API endpoint (add to runs router)
```
GET /runs/{run_id}/time-series
  Response: APIResponse[TimeSeriesResult]
  # Returns {available: false, reason: "..."} for this dataset
  # Returns full trend data when valid timestamps present
```

---

### MODULE 18 — Model Registry

**Priority:** P2  
**New files:** `app/storage/model_registry_store.py`, `app/api/routes/registry.py`, `app/schemas/registry.py`

#### Model registry schema
```python
class ModelLifecycleStage(str, Enum):
    DEVELOPMENT  = "development"
    VALIDATION   = "validation"
    PRODUCTION   = "production"
    SHADOW       = "shadow"         # running in parallel with champion, not decision-making
    CHALLENGER   = "challenger"     # actively competing with champion
    RETIRED      = "retired"

class RegisteredModel(BaseModel):
    model_id: str
    name: str                        # e.g., "CreditScorecard_v3"
    version: str                     # e.g., "3.2.1"
    model_type: str                  # "scorecard", "logistic_regression", "gradient_boosting", "neural_net"
    description: Optional[str]
    owner: str
    lifecycle_stage: ModelLifecycleStage = ModelLifecycleStage.DEVELOPMENT
    is_champion: bool = False        # only one model can be champion at a time
    # Development baseline metrics (set at registration — used for baseline comparison in monitoring)
    dev_auc: Optional[float]
    dev_gini: Optional[float]
    dev_ks: Optional[float]
    dev_bad_rate: Optional[float]
    dev_approval_rate: Optional[float]
    dev_dataset_description: Optional[str]  # e.g., "Training data: Jan 2022 – Dec 2022, 50K accounts"
    # Linked monitoring
    linked_monitor_ids: list[str] = []
    linked_run_ids: list[str] = []
    # Timestamps
    registered_at: datetime
    updated_at: datetime
    promoted_to_production_at: Optional[datetime]
```

#### Champion/Challenger comparison
```python
class ChampionChallengerResult(BaseModel):
    champion_model_id: str
    challenger_model_id: str
    # Latest run metrics for each
    champion_latest_metrics: dict    # {metric_key: value}
    challenger_latest_metrics: dict
    # Deltas (challenger - champion)
    metric_deltas: dict              # {metric_key: delta}
    # Winner per metric
    metric_winners: dict             # {metric_key: "champion|challenger|tie"}
    # Overall recommendation
    recommendation: str              # "Challenger outperforms champion on key metrics — consider promotion"
    summary: str
```

#### API endpoints (new router `/api/v1/registry`)
```
POST /registry/models
  Body: RegisteredModelCreate
  Response: APIResponse[RegisteredModel]

GET  /registry/models?page=1&limit=20&stage=production
  Response: PaginatedResponse[RegisteredModel]

GET  /registry/models/{model_id}
  Response: APIResponse[RegisteredModel]

PUT  /registry/models/{model_id}
  Body: RegisteredModelUpdate (partial — lifecycle_stage, is_champion, etc.)
  Response: APIResponse[RegisteredModel]

POST /registry/models/{model_id}/link-run/{run_id}
  Response: APIResponse[RegisteredModel]

GET  /registry/champion-challenger?champion_id=X&challenger_id=Y
  Response: APIResponse[ChampionChallengerResult]

GET  /registry/champion
  Response: APIResponse[RegisteredModel]    # returns current champion model
```

---

### MODULE 19 — Fairness & Bias Analysis

**Priority:** P2  
**New file:** `app/metrics/implementations/fairness.py`

#### Data findings for this dataset
From actual data analysis:
- `credit_car` loan purpose: **DI = 0.831** — approaching the 0.80 adverse impact threshold (ECOA/FHA 4/5ths rule)
- `75-100K` income band: **DI = 0.844** — also borderline
- All other groups have DI > 0.90 — within acceptable range
- `home_ownership=OTHER`: DI = 0.926 (small n=14 — flag low power)

These are **real findings** from the actual dataset and should be highlighted in demo.

#### Disparate Impact computation
```python
def compute_disparate_impact(
    df: pd.DataFrame,
    decision_col: str,
    group_col: str,
    positive_decision: str = "APPROVED",
    reference_mode: str = "overall",    # "overall" or "most_favoured_group"
) -> list[dict]:
    """
    Disparate Impact (DI) ratio per group.
    DI = group_approval_rate / reference_rate
    Reference = overall_approval_rate (when reference_mode='overall')
              = max group approval rate (when reference_mode='most_favoured_group')

    4/5ths rule (EEOC): DI < 0.80 = prima facie adverse impact.
    Note: loan_purpose, income_band, home_ownership used as proxy variables —
          actual protected characteristics (race, gender) not in this dataset.
          Flag clearly in output: these are PROXY groups, not legally protected classes.
    """
    overall_ar = (df[decision_col] == positive_decision).mean()
    results = []
    for val in df[group_col].unique():
        sub = df[df[group_col] == val]
        ar = (sub[decision_col] == positive_decision).mean()
        di = ar / overall_ar
        results.append({
            "group_col": group_col,
            "group_value": val,
            "n": len(sub),
            "approval_rate": round(ar, 4),
            "reference_rate": round(overall_ar, 4),
            "di_ratio": round(di, 4),
            "status": "critical" if di < 0.80 else ("warning" if di < 0.90 else "ok"),
            "fourfifths_rule_breach": di < 0.80,
            "low_power_warning": len(sub) < 30,
            "is_proxy": True,    # Always True — no direct protected characteristics in dataset
            "proxy_note": f"{group_col} used as proxy variable. Not a legally protected class.",
        })
    return sorted(results, key=lambda x: x["di_ratio"])
```

#### Fairness schema
```python
class FairnessAnalysis(BaseModel):
    proxy_groups_analyzed: list[str]       # ["income_band", "home_ownership", "loan_purpose"]
    overall_approval_rate: float
    di_results: list[dict]                 # one entry per (group_col, group_value) pair
    adverse_impact_flags: list[dict]       # entries where di_ratio < 0.80
    borderline_flags: list[dict]           # entries where 0.80 <= di_ratio < 0.90
    regulatory_note: str                   # "Proxy analysis only. ECOA/FHA require actual protected class data."
    recommended_actions: list[str]
    ecoa_compliance_summary: str           # "No direct adverse impact detected. Borderline: credit_car (DI=0.831)"
```

#### Fairness findings that should auto-trigger
```python
# Rule: DI < 0.90 for any group → generate fairness finding
# Narrative: "credit_car loan purpose shows DI=0.831, approaching the 0.80 adverse impact
#             threshold. While loan_purpose is a proxy variable (not a protected class),
#             monitor for correlation with protected characteristics."
```

#### API endpoint (add to runs router)
```
GET /runs/{run_id}/fairness
  Body/Query: {group_cols: ["income_band", "home_ownership", "loan_purpose"]}
  Response: APIResponse[FairnessAnalysis]
```

---

## SECTION 32: CHART RENDERING — COMPLETE SPECIFICATION

**File:** `app/charts/renderer.py`  
**Library:** `matplotlib` with `Agg` backend only  
**Purpose:** Convert `ChartPayload` JSON → PNG/SVG bytes — no new metric computation

### ChartRenderer class

```python
import matplotlib
matplotlib.use("Agg")   # MUST be before any other matplotlib import
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.gridspec import GridSpec
import numpy as np
import io
import base64
from typing import Literal

# ModelPulse dark-theme palette — consistent across all charts
PALETTE = {
    "bg":        "#0f1117",
    "surface":   "#1a1d27",
    "border":    "#2d3142",
    "text":      "#e2e8f0",
    "muted":     "#64748b",
    "accent":    "#3b82f6",    # blue — primary series
    "success":   "#22c55e",    # green — good/approved
    "warning":   "#f59e0b",    # amber — watch
    "danger":    "#ef4444",    # red — bad/declined/critical
    "purple":    "#8b5cf6",    # purple — secondary series
    "series":    ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"],
}

class ChartRenderer:
    """
    Stateless chart renderer. Takes ChartPayload JSON, renders to bytes.
    Never recomputes data — rendering is a pure transformation of the payload.
    """

    def render(self, payload: "ChartPayload", fmt: Literal["png", "svg"] = "png", dpi: int = 150) -> bytes:
        """Main entry point. Dispatches to chart-type-specific renderer."""
        fig = self._dispatch(payload)
        buf = io.BytesIO()
        fig.savefig(buf, format=fmt, dpi=dpi, bbox_inches="tight",
                    facecolor=PALETTE["bg"], edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    def render_to_base64(self, payload: "ChartPayload", fmt: str = "png") -> str:
        return base64.b64encode(self.render(payload, fmt)).decode("utf-8")

    def _dispatch(self, payload: "ChartPayload") -> plt.Figure:
        handlers = {
            "bar":       self._render_bar,
            "grouped_bar": self._render_grouped_bar,
            "line":      self._render_line,
            "histogram": self._render_histogram,
            "scatter":   self._render_scatter,
            "heatmap":   self._render_heatmap,
            "pie":       self._render_pie,
            "area":      self._render_area,
        }
        handler = handlers.get(payload.chart_type, self._render_bar)
        return handler(payload)

    def _base_fig(self, w=10, h=5) -> tuple[plt.Figure, plt.Axes]:
        fig, ax = plt.subplots(figsize=(w, h), facecolor=PALETTE["bg"])
        ax.set_facecolor(PALETTE["surface"])
        ax.tick_params(colors=PALETTE["muted"], labelsize=9)
        for spine in ax.spines.values():
            spine.set_edgecolor(PALETTE["border"])
        ax.title.set_color(PALETTE["text"])
        ax.xaxis.label.set_color(PALETTE["muted"])
        ax.yaxis.label.set_color(PALETTE["muted"])
        fig.tight_layout(pad=1.5)
        return fig, ax

    def _render_bar(self, payload: "ChartPayload") -> plt.Figure:
        fig, ax = self._base_fig()
        for i, series in enumerate(payload.series):
            xs = [d["x"] for d in series.data]
            ys = [d["y"] for d in series.data]
            color = series.color or PALETTE["series"][i % len(PALETTE["series"])]
            bars = ax.bar(xs, ys, color=color, alpha=0.85, label=series.name, edgecolor=PALETTE["border"])
            # Value labels on bars
            for bar, y in zip(bars, ys):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(ys)*0.01,
                        f"{y:.1%}" if max(ys) < 1 else f"{y:.1f}",
                        ha="center", va="bottom", fontsize=8, color=PALETTE["muted"])
        if payload.annotations:
            for ann in payload.annotations:
                ax.axhline(ann.get("value"), color=PALETTE["danger"], linestyle="--",
                           alpha=0.7, label=ann.get("label", "threshold"))
        ax.set_title(payload.title, fontsize=13, fontweight="bold", color=PALETTE["text"], pad=10)
        if payload.subtitle:
            ax.text(0.5, 1.02, payload.subtitle, transform=ax.transAxes,
                    fontsize=9, color=PALETTE["muted"], ha="center")
        ax.set_xlabel(payload.x_label or "", fontsize=10)
        ax.set_ylabel(payload.y_label or "", fontsize=10)
        if len(payload.series) > 1:
            ax.legend(framealpha=0.2, labelcolor=PALETTE["text"])
        ax.grid(axis="y", color=PALETTE["border"], alpha=0.5, linewidth=0.5)
        return fig

    def _render_line(self, payload: "ChartPayload") -> plt.Figure:
        fig, ax = self._base_fig()
        for i, series in enumerate(payload.series):
            xs = [d["x"] for d in series.data]
            ys = [d["y"] for d in series.data]
            color = series.color or PALETTE["series"][i % len(PALETTE["series"])]
            ax.plot(xs, ys, color=color, linewidth=2, label=series.name, marker="o", markersize=4)
        ax.set_title(payload.title, fontsize=13, fontweight="bold", color=PALETTE["text"], pad=10)
        ax.set_xlabel(payload.x_label or "", fontsize=10)
        ax.set_ylabel(payload.y_label or "", fontsize=10)
        ax.legend(framealpha=0.2, labelcolor=PALETTE["text"])
        ax.grid(color=PALETTE["border"], alpha=0.5, linewidth=0.5)
        return fig

    def _render_grouped_bar(self, payload: "ChartPayload") -> plt.Figure:
        """Two or more series plotted as grouped bars side by side."""
        fig, ax = self._base_fig(w=12, h=5)
        n_series = len(payload.series)
        xs_labels = [d["x"] for d in payload.series[0].data]
        x = np.arange(len(xs_labels))
        width = 0.7 / n_series
        for i, series in enumerate(payload.series):
            ys = [d["y"] for d in series.data]
            color = series.color or PALETTE["series"][i % len(PALETTE["series"])]
            offset = (i - n_series/2 + 0.5) * width
            ax.bar(x + offset, ys, width, label=series.name, color=color, alpha=0.85,
                   edgecolor=PALETTE["border"])
        ax.set_xticks(x)
        ax.set_xticklabels(xs_labels, rotation=15, ha="right")
        ax.set_title(payload.title, fontsize=13, fontweight="bold", color=PALETTE["text"], pad=10)
        ax.set_xlabel(payload.x_label or "", fontsize=10)
        ax.set_ylabel(payload.y_label or "", fontsize=10)
        ax.legend(framealpha=0.2, labelcolor=PALETTE["text"])
        ax.grid(axis="y", color=PALETTE["border"], alpha=0.5, linewidth=0.5)
        return fig

    def _render_histogram(self, payload: "ChartPayload") -> plt.Figure:
        """For pre-binned histogram data (x=bin_center or label, y=count/pct)."""
        # Same as bar but with no gap between bars
        fig, ax = self._base_fig()
        for i, series in enumerate(payload.series):
            xs = [d["x"] for d in series.data]
            ys = [d["y"] for d in series.data]
            color = series.color or PALETTE["series"][i]
            ax.bar(range(len(xs)), ys, color=color, alpha=0.7, label=series.name,
                   edgecolor=PALETTE["surface"], linewidth=0.3)
        ax.set_xticks(range(len(xs)))
        ax.set_xticklabels(xs, rotation=45, ha="right", fontsize=8)
        ax.set_title(payload.title, fontsize=13, fontweight="bold", color=PALETTE["text"], pad=10)
        ax.set_xlabel(payload.x_label or "Score", fontsize=10)
        ax.set_ylabel(payload.y_label or "Count", fontsize=10)
        if len(payload.series) > 1:
            ax.legend(framealpha=0.2, labelcolor=PALETTE["text"])
        ax.grid(axis="y", color=PALETTE["border"], alpha=0.4)
        return fig

    def _render_heatmap(self, payload: "ChartPayload") -> plt.Figure:
        """Expects payload.series[0].data = [{x: row_label, y: col_label, v: value}]"""
        fig, ax = self._base_fig(w=10, h=6)
        data_pts = payload.series[0].data
        rows = sorted(set(d["x"] for d in data_pts))
        cols = sorted(set(d["y"] for d in data_pts))
        matrix = np.zeros((len(rows), len(cols)))
        for d in data_pts:
            ri, ci = rows.index(d["x"]), cols.index(d["y"])
            matrix[ri, ci] = d.get("v", d.get("z", 0))
        im = ax.imshow(matrix, cmap="RdYlGn_r", aspect="auto")
        ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols, rotation=30, ha="right", fontsize=8)
        ax.set_yticks(range(len(rows))); ax.set_yticklabels(rows, fontsize=8)
        for i in range(len(rows)):
            for j in range(len(cols)):
                ax.text(j, i, f"{matrix[i,j]:.2f}", ha="center", va="center",
                        fontsize=8, color="white" if matrix[i,j] > matrix.max()*0.6 else "black")
        plt.colorbar(im, ax=ax, fraction=0.03)
        ax.set_title(payload.title, fontsize=13, fontweight="bold", color=PALETTE["text"], pad=10)
        return fig

    def _render_pie(self, payload: "ChartPayload") -> plt.Figure:
        fig, ax = self._base_fig(w=7, h=7)
        data = payload.series[0].data
        labels = [d["x"] for d in data]
        vals = [d["y"] for d in data]
        colors = [PALETTE["series"][i % len(PALETTE["series"])] for i in range(len(vals))]
        wedges, texts, autotexts = ax.pie(vals, labels=labels, autopct="%1.1f%%",
                                           colors=colors, startangle=90,
                                           wedgeprops={"edgecolor": PALETTE["bg"], "linewidth": 2})
        for t in texts: t.set_color(PALETTE["text"]); t.set_fontsize(9)
        for a in autotexts: a.set_color("white"); a.set_fontsize(8)
        ax.set_title(payload.title, fontsize=13, fontweight="bold", color=PALETTE["text"], pad=10)
        return fig

    def _render_scatter(self, payload: "ChartPayload") -> plt.Figure:
        fig, ax = self._base_fig()
        for i, series in enumerate(payload.series):
            xs = [d["x"] for d in series.data]
            ys = [d["y"] for d in series.data]
            color = series.color or PALETTE["series"][i]
            ax.scatter(xs, ys, color=color, alpha=0.7, label=series.name, s=30, edgecolors="none")
        ax.set_title(payload.title, fontsize=13, fontweight="bold", color=PALETTE["text"], pad=10)
        ax.set_xlabel(payload.x_label or "", fontsize=10)
        ax.set_ylabel(payload.y_label or "", fontsize=10)
        if len(payload.series) > 1:
            ax.legend(framealpha=0.2, labelcolor=PALETTE["text"])
        ax.grid(color=PALETTE["border"], alpha=0.4)
        return fig

    def _render_area(self, payload: "ChartPayload") -> plt.Figure:
        fig, ax = self._base_fig()
        for i, series in enumerate(payload.series):
            xs = list(range(len(series.data)))
            ys = [d["y"] for d in series.data]
            xlabels = [d["x"] for d in series.data]
            color = series.color or PALETTE["series"][i]
            ax.fill_between(xs, ys, alpha=0.3, color=color)
            ax.plot(xs, ys, color=color, linewidth=1.5, label=series.name)
        ax.set_xticks(xs); ax.set_xticklabels(xlabels, rotation=30, ha="right", fontsize=8)
        ax.set_title(payload.title, fontsize=13, fontweight="bold", color=PALETTE["text"], pad=10)
        ax.legend(framealpha=0.2, labelcolor=PALETTE["text"])
        ax.grid(color=PALETTE["border"], alpha=0.4)
        return fig
```

### Chart rendering API endpoints (add to runs router)
```
GET  /runs/{run_id}/charts
  Query: format=json (default) | format=png | format=svg
  Response (json):   APIResponse[list[ChartPayload]]
  Response (png):    ZIP archive of all chart PNGs (Content-Type: application/zip)

GET  /runs/{run_id}/charts/{chart_id}
  Query: format=json (default)
  Response: APIResponse[ChartPayload]

GET  /runs/{run_id}/charts/{chart_id}/image
  Query: format=png (default) | format=svg, dpi=150
  Response: binary image (Content-Type: image/png or image/svg+xml)
  Use case: <img src="/api/v1/runs/{run_id}/charts/{chart_id}/image"> in HTML

POST /runs/{run_id}/charts/render-all
  Body: {format: "png|svg", dpi: 150}
  Response: APIResponse[list[{chart_id, chart_title, image_b64, format}]]
  Use case: generate all charts as base64 at once (for report embedding)
```

### `image_url` field in ChartPayload
Add to the `ChartPayload` schema:
```python
class ChartPayload(BaseModel):
    chart_id: str
    chart_type: str
    title: str
    subtitle: Optional[str]
    x_label: Optional[str]
    y_label: Optional[str]
    series: list[ChartSeries]
    annotations: Optional[list[dict]]
    image_url: Optional[str] = None    # ADD: populated as "/api/v1/runs/{run_id}/charts/{chart_id}/image"
    # This means every chart in the response self-describes where to fetch its rendered image
```

---

## SECTION 33: UPDATED FOLDER STRUCTURE (COMPLETE — ALL MODULES)

Replace Section 4's folder structure with this complete version:

```
modelpulse/
├── main.py
├── requirements.txt
├── .env.example
├── README.md
│
├── app/
│   ├── core/
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── logging_config.py
│   │
│   ├── api/
│   │   └── routes/
│   │       ├── health.py
│   │       ├── datasets.py
│   │       ├── mappings.py
│   │       ├── monitors.py
│   │       ├── runs.py
│   │       ├── registry.py          # NEW: model registry endpoints
│   │       └── helpers.py
│   │
│   ├── schemas/
│   │   ├── common.py
│   │   ├── dataset.py
│   │   ├── mapping.py
│   │   ├── monitor.py
│   │   ├── run.py
│   │   ├── metrics.py
│   │   ├── segments.py
│   │   ├── alerts.py
│   │   ├── insights.py
│   │   ├── charts.py
│   │   ├── registry.py              # NEW: model registry schemas
│   │   ├── fairness.py              # NEW: fairness analysis schemas
│   │   ├── override.py              # NEW: override analysis schemas
│   │   └── reports.py               # NEW: report generation schemas
│   │
│   ├── services/
│   │   ├── dataset_service.py
│   │   ├── mapping_service.py
│   │   ├── monitor_service.py
│   │   ├── run_service.py
│   │   ├── insight_service.py
│   │   ├── health_score_service.py
│   │   ├── report_service.py        # NEW: PDF/HTML report generation
│   │   ├── timeseries_service.py    # NEW: time series monitoring (skeleton)
│   │   └── llm_service.py           # placeholder (deterministic mock only)
│   │
│   ├── profiling/
│   │   └── profiler.py
│   │
│   ├── mapping/
│   │   ├── heuristics.py
│   │   └── validator.py
│   │
│   ├── charts/
│   │   └── renderer.py              # NEW: matplotlib Agg chart renderer (Section 32)
│   │
│   ├── metrics/
│   │   ├── registry.py
│   │   ├── base.py
│   │   ├── engine.py
│   │   └── implementations/
│   │       ├── data_quality.py
│   │       ├── drift.py
│   │       ├── performance.py
│   │       ├── calibration.py
│   │       ├── strategy.py
│   │       ├── delinquency.py
│   │       ├── score_distribution.py  # NEW: Module 8 (dedicated score analysis)
│   │       ├── statistical_tests.py   # NEW: Module 11 (H-L, chi-sq, binomial, etc.)
│   │       ├── vintage.py             # NEW: Module 14 (roll rate + cohort skeleton)
│   │       ├── override.py            # NEW: Module 15 (override analysis)
│   │       └── fairness.py            # NEW: Module 19 (DI ratio, ECOA)
│   │
│   ├── segmentation/
│   │   └── engine.py
│   │
│   ├── alerts/
│   │   └── engine.py
│   │
│   ├── storage/
│   │   ├── base.py
│   │   ├── dataset_store.py
│   │   ├── mapping_store.py
│   │   ├── monitor_store.py
│   │   ├── run_store.py
│   │   └── model_registry_store.py   # NEW: model registry persistence
│   │
│   ├── templates/
│   │   └── reports/                  # NEW: Jinja2 HTML templates for reports
│   │       ├── base.html
│   │       ├── executive_summary.html
│   │       ├── full_technical.html
│   │       ├── sr_11_7.html
│   │       └── ifrs9.html
│   │
│   └── utils/
│       ├── dataframe.py
│       └── formatting.py
│
└── storage/
    ├── uploads/
    ├── profiles/
    ├── mappings/
    ├── monitor_configs/
    ├── model_registry/               # NEW: registered model JSON files
    ├── runs/
    │   └── {run_id}/
    │       ├── run_metadata.json
    │       ├── summary_cards.json
    │       ├── metrics.json
    │       ├── charts.json
    │       ├── segments.json
    │       ├── alerts.json
    │       ├── findings.json
    │       ├── insight_context.json
    │       ├── narratives.json
    │       ├── health_score.json
    │       ├── stat_tests.json        # NEW: statistical test results
    │       ├── override_analysis.json # NEW: override analysis results
    │       ├── fairness.json          # NEW: fairness/DI analysis
    │       ├── vintage.json           # NEW: roll rate + cohort (if available)
    │       └── reports/              # NEW: generated PDF/HTML reports
    │           ├── executive_summary.pdf
    │           ├── sr_11_7.html
    │           └── ...
    └── temp/
```

---

## SECTION 34: COMPLETE API ENDPOINT LIST (ALL 20 MODULES)

This is the final, complete API contract including all new module endpoints:

```
# Health
GET  /api/v1/health

# Datasets
POST /api/v1/datasets/upload
GET  /api/v1/datasets
GET  /api/v1/datasets/{dataset_id}
GET  /api/v1/datasets/{dataset_id}/profile
GET  /api/v1/datasets/{dataset_id}/preview

# Mapping
POST /api/v1/datasets/{dataset_id}/suggest-mapping
POST /api/v1/datasets/{dataset_id}/save-mapping
GET  /api/v1/datasets/{dataset_id}/mapping
GET  /api/v1/datasets/{dataset_id}/mapping/validate

# Monitor Config
POST   /api/v1/monitors/create
GET    /api/v1/monitors
GET    /api/v1/monitors/{monitor_id}
PUT    /api/v1/monitors/{monitor_id}
DELETE /api/v1/monitors/{monitor_id}

# Core Run Endpoints
POST /api/v1/monitors/{monitor_id}/run
GET  /api/v1/runs
GET  /api/v1/runs/{run_id}/summary
GET  /api/v1/runs/{run_id}/metrics
GET  /api/v1/runs/{run_id}/segments
GET  /api/v1/runs/{run_id}/alerts
GET  /api/v1/runs/{run_id}/results

# Charts — JSON + Image Rendering (Section 32)
GET  /api/v1/runs/{run_id}/charts                          # ?format=json|png|svg
GET  /api/v1/runs/{run_id}/charts/{chart_id}
GET  /api/v1/runs/{run_id}/charts/{chart_id}/image         # ?format=png|svg&dpi=150
POST /api/v1/runs/{run_id}/charts/render-all               # bulk base64 render

# AI Insight Layer
GET  /api/v1/runs/{run_id}/findings
GET  /api/v1/runs/{run_id}/insight-context
POST /api/v1/runs/{run_id}/generate-narrative-placeholder
GET  /api/v1/runs/{run_id}/narratives

# Module 11 — Statistical Testing Suite
GET  /api/v1/runs/{run_id}/stat-tests

# Module 14 — Vintage & Cohort
GET  /api/v1/runs/{run_id}/vintage

# Module 15 — Override Analysis
GET  /api/v1/runs/{run_id}/override-analysis               # ?score_cutoff=600

# Module 17 — Time Series
GET  /api/v1/runs/{run_id}/time-series

# Module 19 — Fairness & Bias
GET  /api/v1/runs/{run_id}/fairness                        # ?group_cols=income_band,home_ownership

# Module 18 — Model Registry
POST /api/v1/registry/models
GET  /api/v1/registry/models
GET  /api/v1/registry/models/{model_id}
PUT  /api/v1/registry/models/{model_id}
POST /api/v1/registry/models/{model_id}/link-run/{run_id}
GET  /api/v1/registry/champion
GET  /api/v1/registry/champion-challenger                  # ?champion_id=X&challenger_id=Y

# Module 6/20 — Report Generation
POST /api/v1/runs/{run_id}/reports/generate
GET  /api/v1/runs/{run_id}/reports
GET  /api/v1/runs/{run_id}/reports/{report_id}/download

# Helpers
GET  /api/v1/metric-library
GET  /api/v1/templates
GET  /api/v1/segments/recommendations/{dataset_id}
GET  /api/v1/health-score/{run_id}
```

**Total endpoint count: 50 endpoints across 20 modules.**

---

## SECTION 35: FINAL MODULE COVERAGE TABLE (v3 — COMPLETE)

| # | Module | Priority | v3 Status | Key file |
|---|--------|----------|-----------|----------|
| 1 | Data onboarding & quality | P0 | ✅ Complete | `profiler.py`, `data_quality.py` |
| 2 | PSI | P0 | ✅ Complete | `drift.py` (exact formula) |
| 3 | Gini / KS / AUC | P0 | ✅ Complete | `performance.py` |
| 4 | Calibration analysis | P0 | ✅ Complete | `calibration.py` |
| 5 | Traffic light dashboard | P0 | ✅ Complete | `health_score_service.py` |
| 6 | Report generation (PDF/HTML) | P0 | ✅ Added | `report_service.py`, `templates/reports/` |
| 7 | CSI (per feature) | P1 | ✅ Complete | `drift.py` |
| 8 | Score distribution analysis | P1 | ✅ Added | `score_distribution.py` |
| 9 | Segment performance | P1 | ✅ Complete | `segmentation/engine.py` |
| 10 | Approval rate analysis | P1 | ✅ Complete | `strategy.py` |
| 11 | Statistical testing suite | P1 | ✅ Added | `statistical_tests.py` |
| 12 | Model health scorecard | P1 | ✅ Complete | `health_score_service.py` |
| 13 | Alerts & rules engine | P1 | ✅ Complete | `alerts/engine.py` |
| 14 | Vintage & cohort analysis | P2 | ✅ Added* | `vintage.py` (*roll rate; cohort skeleton for malformed time) |
| 15 | Override analysis | P2 | ✅ Added | `override.py` (81.2% override rate — great demo) |
| 16 | Feature drift deep dive | P2 | ✅ Complete | `drift.py` heatmap |
| 17 | Time series monitoring | P2 | ✅ Added* | `timeseries_service.py` (*skeleton; app_time malformed) |
| 18 | Model registry | P2 | ✅ Added | `model_registry_store.py`, `registry.py` routes |
| 19 | Fairness & bias analysis | P2 | ✅ Added | `fairness.py` (DI ratio, credit_car DI=0.831) |
| 20 | Regulatory report suite | P2 | ✅ Added | `report_service.py` (SR 11-7, IFRS 9 templates) |
| + | Server-side chart rendering | P0 | ✅ Added | `charts/renderer.py` (8 chart types, dark theme) |

**All 20 modules + chart rendering are now covered. 50 API endpoints. v3 is complete.**

---

*End of prompt v3.0 — all modules complete*