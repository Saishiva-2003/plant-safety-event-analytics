from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import dashboard_service
from app.services.context import get_context

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/kpis")
def kpis(db: Session = Depends(get_db)):
    """Overview KPIs (replay duplicates excluded)."""
    return dashboard_service.kpis(get_context(db))