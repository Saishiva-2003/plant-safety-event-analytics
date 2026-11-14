from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import BadRequestError
from app.dto.alarm_dto import AlarmPageDTO
from app.services import alarm_service
from app.services.context import get_context

router = APIRouter(prefix="/api/alarms", tags=["alarms"])


@router.get("", response_model=AlarmPageDTO)
def list_alarms(
    plant: Optional[str] = Query(None, pattern=r"^P\d{2}$"),
    machine: Optional[str] = Query(None, pattern=r"^P\d{2}-M\d{3}$"),
    severity: Optional[Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]] = None,
    category: Optional[Literal["SAFETY", "PROCESS", "EQUIPMENT", "SYSTEM"]] = None,
    ack_status: Optional[Literal["ON_TIME", "DELAYED", "UNACKED", "INVALID"]] = None, flood_only: bool = False,
    include_replays: bool = False, search: Optional[str] = Query(None, max_length=60),
    date_from: Optional[date] = None, date_to: Optional[date] = None,
    sort: str = Query("priority", pattern="^(priority|newest|oldest)$"),
    page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Alarm explorer - default sort = priority score (severe alarms first)."""
    if date_from and date_to and date_from > date_to:
        raise BadRequestError("date_from must be on or before date_to",
                              {"date_from": str(date_from), "date_to": str(date_to)})
    return alarm_service.list_alarms(get_context(db), plant, machine, severity, category, ack_status, flood_only,
                                     include_replays, search, date_from, date_to, sort, page, size)