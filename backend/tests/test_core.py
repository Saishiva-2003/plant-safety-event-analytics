"""Core tests: configuration + database connectivity."""
from sqlalchemy import text

from app.core.config import (
    CSV_DIR,
    GROUND_TRUTH_DIR,
    PROJECT_ROOT,
    REPORTS_DIR,
    get_settings,
)
from app.core.database import SessionLocal, build_db_url, check_connection


def test_settings_loaded_with_types():
    s = get_settings()
    assert s.DB_NAME == "safety_db"
    assert isinstance(s.DB_PORT, int)
    assert s.SEED == 20261022
    assert s.DB_PASSWORD, "DB_PASSWORD missing in backend/.env"


def test_paths_point_to_database_tier():
    assert (PROJECT_ROOT / "backend").is_dir()
    assert CSV_DIR.parts[-3:] == ("database", "seed", "csv")
    for folder in (CSV_DIR, GROUND_TRUTH_DIR, REPORTS_DIR):
        assert folder.is_dir(), f"missing folder: {folder}"


def test_db_url_hides_password():
    url = build_db_url()
    assert url.drivername == "mysql+pymysql"
    assert "***" in repr(url)  # password masked when printed


def test_mysql_connection():
    result = check_connection()
    assert result["status"] == "ok"
    assert result["database"] == "safety_db"


def test_session_can_query():
    with SessionLocal() as db:
        assert db.execute(text("SELECT 1 + 1")).scalar() == 2