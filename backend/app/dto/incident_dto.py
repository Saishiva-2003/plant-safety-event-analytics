"""Incident + traceability DTOs."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class IncidentDTO(BaseModel):
    incident_id: str
    machine_id: str
    machine_name: str
    plant_id: str
    zone_id: str
    zone_name: str
    hazard_level: int
    trigger_alarm_id: Optional[str] = None
    rule_code: str
    severity: str
    opened_ts: datetime
    status: str
    closed_ts: Optional[datetime] = None
    reported_by: str
    description: str
    linked_alarms: int
    actions_total: int
    actions_closed: int
    traceable: bool


class IncidentListDTO(BaseModel):
    total: int
    items: list[IncidentDTO]


class ActionDTO(BaseModel):
    action_id: str
    incident_id: str
    action_type: str
    description: str
    owner_id: str
    created_ts: datetime
    due_ts: datetime
    status: str
    started_ts: Optional[datetime] = None
    completed_ts: Optional[datetime] = None
    verified_ts: Optional[datetime] = None
    verified_by: Optional[str] = None
    closed_ts: Optional[datetime] = None


class TimelineEntryDTO(BaseModel):
    ts: datetime
    type: str
    title: str
    detail: str
    ref: Optional[str] = None
    severity: Optional[str] = None
    flag: Optional[str] = None


class IncidentTraceDTO(BaseModel):
    incident: IncidentDTO
    machine_state_at_open: str
    window_start: datetime
    window_end: datetime
    linked_alarms: int
    state_events: int
    interlock_events: int
    traceable: bool
    flags: list[str]
    actions: list[ActionDTO]
    timeline: list[TimelineEntryDTO]