from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import master_repo

router = APIRouter(prefix="/api/master", tags=["master data"])


@router.get("/plants")
def plants(db: Session = Depends(get_db)):
    return [{"plant_id": p.plant_id, "plant_name": p.plant_name, "city": p.city, "state": p.state}
            for p in master_repo.list_plants(db)]


@router.get("/machines")
def machines(plant: Optional[str] = Query(None, pattern=r"^P\d{2}$"), db: Session = Depends(get_db)):
    return master_repo.list_machines(db, plant)


@router.get("/zones")
def zones(db: Session = Depends(get_db)):
    return [{"zone_id": z.zone_id, "plant_id": z.plant_id, "zone_name": z.zone_name, "zone_type": z.zone_type,
             "hazard_level": z.hazard_level} for z in master_repo.list_zones(db)]


@router.get("/alarm-definitions")
def alarm_definitions(db: Session = Depends(get_db)):
    return [{"alarm_def_id": d.alarm_def_id, "alarm_code": d.alarm_code, "alarm_name": d.alarm_name,
             "category": d.category, "severity": d.severity, "ack_sla_sec": d.ack_sla_sec}
            for d in master_repo.list_alarm_definitions(db)]