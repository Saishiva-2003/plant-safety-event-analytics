"""
Application configuration (Tier 2 - core).

Reads backend/.env once and exposes:
  * get_settings()  -> typed Settings object
  * folder paths    -> shared by generator, validator, loader and API
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Folder paths
# This file lives at backend/app/core/config.py
#   parents[0] = core, parents[1] = app, parents[2] = backend
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent

# Tier-3 data folders
DATABASE_DIR = PROJECT_ROOT / "database"
SCHEMA_DIR = DATABASE_DIR / "schema"
SEED_DIR = DATABASE_DIR / "seed"
CSV_DIR = SEED_DIR / "csv"
JSON_DIR = SEED_DIR / "json"
SQL_DIR = SEED_DIR / "sql"
GROUND_TRUTH_DIR = DATABASE_DIR / "ground_truth"
REPORTS_DIR = DATABASE_DIR / "reports"


class Settings(BaseSettings):
    """All runtime settings. Values come from backend/.env (defaults below)."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Plant Safety Event Analytics"
    APP_ENV: str = "dev"

    # MySQL
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "safety_db"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""

    # Data generator
    SEED: int = 20261022
    SCALE: str = "full"

    # CORS (comma-separated list of allowed frontend URLs)
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Load settings once and reuse the same object everywhere."""
    return Settings()