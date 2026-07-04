"""ModelPulse — FastAPI POC backend for credit risk model monitoring."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.config import settings
from app.core.exceptions import (
    DatasetNotFoundError,
    FileTooLargeError,
    InsufficientDataError,
    InvalidFileTypeError,
    MappingNotFoundError,
    ModelPulseError,
    MonitorNotFoundError,
    RunNotFoundError,
)
from app.core.logging_config import setup_logging
from app.schemas.common import APIResponse

# --- Logging ---
setup_logging(debug=settings.debug)

# --- App ---
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Credit risk model monitoring platform — POC backend",
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # POC: allow all. Restrict in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Exception handlers ---
_NOT_FOUND_ERRORS = (
    DatasetNotFoundError,
    MappingNotFoundError,
    MonitorNotFoundError,
    RunNotFoundError,
)


@app.exception_handler(DatasetNotFoundError)
@app.exception_handler(MappingNotFoundError)
@app.exception_handler(MonitorNotFoundError)
@app.exception_handler(RunNotFoundError)
async def not_found_handler(request: Request, exc: ModelPulseError) -> JSONResponse:
    """Handle resource-not-found errors with 404."""
    return JSONResponse(
        status_code=404,
        content=APIResponse(success=False, error=str(exc)).model_dump(mode="json"),
    )


@app.exception_handler(InvalidFileTypeError)
@app.exception_handler(FileTooLargeError)
async def bad_request_handler(request: Request, exc: ModelPulseError) -> JSONResponse:
    """Handle invalid input errors with 400."""
    return JSONResponse(
        status_code=400,
        content=APIResponse(success=False, error=str(exc)).model_dump(mode="json"),
    )


@app.exception_handler(InsufficientDataError)
async def insufficient_data_handler(
    request: Request, exc: InsufficientDataError
) -> JSONResponse:
    """Handle insufficient data errors with 400."""
    return JSONResponse(
        status_code=400,
        content=APIResponse(success=False, error=str(exc)).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — log full traceback, return safe 500."""
    logger.exception("Unhandled exception on {} {}", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=APIResponse(
            success=False, error="Internal server error"
        ).model_dump(mode="json"),
    )


# --- Startup ---
@app.on_event("startup")
async def startup_event() -> None:
    """Ensure all storage directories exist on startup."""
    for dir_path in [
        settings.storage_root,
        settings.uploads_dir,
        settings.profiles_dir,
        settings.mappings_dir,
        settings.monitor_configs_dir,
        settings.runs_dir,
        settings.model_registry_dir,
        settings.temp_dir,
    ]:
        dir_path.mkdir(parents=True, exist_ok=True)
    logger.info(
        "ModelPulse {} started — storage at {}",
        settings.app_version,
        settings.storage_root,
    )


# --- Routers ---
from app.api.routes import health, datasets, mappings, monitors, runs  # noqa: E402

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(datasets.router, prefix="/api/v1", tags=["datasets"])
app.include_router(mappings.router, prefix="/api/v1", tags=["mappings"])
app.include_router(monitors.router, prefix="/api/v1", tags=["monitors"])
app.include_router(runs.router, prefix="/api/v1", tags=["runs"])
