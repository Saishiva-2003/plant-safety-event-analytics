"""
FastAPI application (Tier 2).   Run:  cd backend  ->  uvicorn app.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import check_connection, get_db
from app.core.exceptions import register_exception_handlers
from app.dto.common import HealthDTO
from app.routes import alarms, analytics, dashboard, incidents, master, meta, quality

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
settings = get_settings()
app = FastAPI(title=settings.APP_NAME, version="1.0.0",
              description="Analyse safety events, machine states, acknowledgements and corrective actions "
                          "to find repeated unsafe conditions.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

register_exception_handlers(app)

for r in (dashboard, alarms, analytics, incidents, quality, meta, master):
    app.include_router(r.router)


@app.get("/api/health", response_model=HealthDTO, tags=["health"])
def health(db: Session = Depends(get_db)):
    info = check_connection()
    count = db.execute(text("SELECT COUNT(*) FROM alarm_event")).scalar()
    return {"status": "ok", "database": info["database"], "mysql_version": info["mysql_version"], "alarm_events": count}


@app.get("/", include_in_schema=False)
def root():
    return {"app": settings.APP_NAME, "docs": "/docs", "health": "/api/health"}