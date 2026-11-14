from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dto.incident_dto import IncidentListDTO, IncidentTraceDTO
from app.services import incident_service, trace_service
from app.services.context import get_context

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("", response_model=IncidentListDTO)
def list_incidents(
    plant: Optional[str] = Query(None, pattern=r"^P\d{2}$"),
    machine: Optional[str] = Query(None, pattern=r"^P\d{2}-M\d{3}$"),
    rule: Optional[Literal["R1_BYPASS_CRITICAL", "R2_GUARD_TRIP_ESTOP", "R3_CRITICAL_UNACKED", "MANUAL_REPORT"]] = None,
    status: Optional[Literal["OPEN", "INVESTIGATING", "ACTION_PENDING", "CLOSED"]] = None,
    severity: Optional[Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]] = None,
    db: Session = Depends(get_db),
):
    return incident_service.list_incidents(get_context(db), plant, machine, rule, status, severity)


@router.get("/{incident_id}/trace", response_model=IncidentTraceDTO)
def trace(incident_id: str = Path(..., pattern=r"^INC-\d{4}-\d{6}$"), db: Session = Depends(get_db)):
    """Ordered timeline: machine states, interlocks, alarms, acknowledgements, corrective actions."""
    result = trace_service.incident_trace(get_context(db), db, incident_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return result