from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import flood_service, nuisance_service, unsafe_service
from app.services.context import get_context

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/floods")
def floods(db: Session = Depends(get_db)):
    """Alarm-flood episodes (> 10 alarms / 10 min / plant)."""
    return flood_service.flood_summary(get_context(db))


@router.get("/nuisance")
def nuisance(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    """Chattering / fleeting bad-actor alarms (nuisance clusters)."""
    return nuisance_service.nuisance_summary(get_context(db), limit)


@router.get("/repeated-unsafe")
def repeated_unsafe(db: Session = Depends(get_db)):
    """Repeated unsafe conditions: same machine + rule >= 3 times in 7 days."""
    return unsafe_service.repeated_unsafe(get_context(db))