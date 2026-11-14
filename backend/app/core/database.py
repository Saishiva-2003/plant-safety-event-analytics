"""
Database layer (Tier 2 -> Tier 3 bridge).

Single source of:
  * engine        - MySQL connection pool
  * SessionLocal  - session factory
  * Base          - parent class for all ORM models
  * get_db()      - FastAPI dependency (one session per request)
  * check_connection() - health check
"""
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()


def build_db_url(include_db: bool = True) -> URL:
    """Build the MySQL URL safely (special characters in the password are escaped)."""
    return URL.create(
        drivername="mysql+pymysql",
        username=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME if include_db else None,
        query={"charset": "utf8mb4"},
    )


engine = create_engine(
    build_db_url(),
    pool_pre_ping=True,   # test connection before use; reconnect if dropped
    pool_recycle=3600,    # recycle connections every hour
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Parent class for all ORM models in app/models/."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: open one session per request and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_connection() -> dict:
    """Return MySQL version + current database. Raises an error if unreachable."""
    with engine.connect() as conn:
        version = conn.execute(text("SELECT VERSION()")).scalar()
        current_db = conn.execute(text("SELECT DATABASE()")).scalar()
    return {"status": "ok", "mysql_version": version, "database": current_db}