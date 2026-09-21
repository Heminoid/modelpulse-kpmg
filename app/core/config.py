"""Application configuration using pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """ModelPulse application settings, loaded from environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ModelPulse API"
    app_version: str = "1.0.0"
    debug: bool = True

    # LLM config
    cloudflare_account_id: str = ""
    cloudflare_api_token: str = ""
    llm_provider: str = "auto"

    # Storage paths
    storage_root: Path = Path("storage")
    uploads_dir: Path = Path("storage/uploads")
    profiles_dir: Path = Path("storage/profiles")
    mappings_dir: Path = Path("storage/mappings")
    monitor_configs_dir: Path = Path("storage/monitor_configs")
    runs_dir: Path = Path("storage/runs")
    reports_dir: Path = Path("storage/reports")
    model_registry_dir: Path = Path("storage/model_registry")
    temp_dir: Path = Path("storage/temp")

    # Upload limits
    max_upload_size_mb: int = 10240
    allowed_extensions: list[str] = [".csv", ".tsv", ".xlsx"]

    # Monitoring defaults
    default_psi_bins: int = 10
    default_calibration_bins: int = 10
    score_higher_is_better: bool = True

    # Default alert thresholds
    psi_amber_threshold: float = 0.10
    psi_red_threshold: float = 0.25
    auc_decline_threshold: float = 0.05
    gini_decline_threshold: float = 0.05
    ks_decline_threshold: float = 0.05
    approval_rate_change_threshold: float = 0.05
    bad_rate_increase_threshold: float = 0.02
    calibration_gap_threshold: float = 0.03
    severe_dpd_rate_threshold: float = 0.10
    null_rate_warning_threshold: float = 0.05


settings = Settings()
