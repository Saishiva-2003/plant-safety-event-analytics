"""Alarm explorer DTOs."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AlarmDTO(BaseModel):
    alarm_event_id: str
    plant_id: str
    machine_id: str
    machine_name: str
    alarm_def_id: str
    alarm_code: str
    alarm_name: str
    category: str
    severity: str
    raised_ts: datetime
    cleared_ts: Optional[datetime] = None
    machine_state: str
    interlock_state_at_raise: str
    zone_id: str
    hazard_level: int
    repeat_24h: int
    priority_score: float
    ack_status: str
    response_sec: Optional[float] = None
    ack_operator_id: Optional[str] = None
    shift_id: str
    flood_id: Optional[str] = None
    chatter: bool
    is_replay: bool


class AlarmPageDTO(BaseModel):
    total: int
    page: int
    size: int
    pages: int
    items: list[AlarmDTO]