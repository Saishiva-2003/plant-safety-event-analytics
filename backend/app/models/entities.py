"""
ORM entities (Tier 2 <-> Tier 3 mapping). One class per MySQL table in database/schema/schema.sql.
Relationships mirror the foreign keys (1:N) and the two N:M bridge tables.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DECIMAL, Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ------------------------------- master -----------------------------------
class Plant(Base):
    __tablename__ = "plant"
    plant_id: Mapped[str] = mapped_column(String(8), primary_key=True)
    plant_name: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(60))
    state: Mapped[str] = mapped_column(String(60))
    country: Mapped[str] = mapped_column(String(2))
    timezone: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(12))
    opened_date: Mapped[date] = mapped_column(Date)
    machines: Mapped[list["Machine"]] = relationship(back_populates="plant")


class SafetyZone(Base):
    __tablename__ = "safety_zone"
    zone_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    plant_id: Mapped[str] = mapped_column(ForeignKey("plant.plant_id"))
    zone_name: Mapped[str] = mapped_column(String(100))
    zone_type: Mapped[str] = mapped_column(String(20))
    hazard_level: Mapped[int] = mapped_column(Integer)
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(12))


class Machine(Base):
    __tablename__ = "machine"
    machine_id: Mapped[str] = mapped_column(String(12), primary_key=True)
    plant_id: Mapped[str] = mapped_column(ForeignKey("plant.plant_id"))
    machine_name: Mapped[str] = mapped_column(String(100))
    machine_type: Mapped[str] = mapped_column(String(20))
    manufacturer: Mapped[str] = mapped_column(String(40))
    criticality: Mapped[str] = mapped_column(String(1))
    commissioned_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(12))
    plant: Mapped[Plant] = relationship(back_populates="machines")
    interlocks: Mapped[list["Interlock"]] = relationship(back_populates="machine")


class MachineZone(Base):            # N:M bridge
    __tablename__ = "machine_zone"
    machine_id: Mapped[str] = mapped_column(ForeignKey("machine.machine_id"), primary_key=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("safety_zone.zone_id"), primary_key=True)
    is_primary: Mapped[bool] = mapped_column(Boolean)
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)


class Interlock(Base):
    __tablename__ = "interlock"
    interlock_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    machine_id: Mapped[str] = mapped_column(ForeignKey("machine.machine_id"))
    zone_id: Mapped[str] = mapped_column(ForeignKey("safety_zone.zone_id"))
    interlock_type: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(String(150))
    sil_level: Mapped[int] = mapped_column(Integer)
    initial_state: Mapped[str] = mapped_column(String(10))
    installed_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(12))
    machine: Mapped[Machine] = relationship(back_populates="interlocks")


class AlarmDefinition(Base):
    __tablename__ = "alarm_definition"
    alarm_def_id: Mapped[str] = mapped_column(String(8), primary_key=True)
    alarm_code: Mapped[str] = mapped_column(String(20), unique=True)
    base_code: Mapped[str] = mapped_column(String(16))
    alarm_name: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(12))
    severity: Mapped[str] = mapped_column(String(10))
    machine_type: Mapped[str] = mapped_column(String(20))
    interlock_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    ack_required: Mapped[bool] = mapped_column(Boolean)
    ack_sla_sec: Mapped[int] = mapped_column(Integer)
    effective_from: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(12))


class Staff(Base):
    __tablename__ = "staff"
    staff_id: Mapped[str] = mapped_column(String(12), primary_key=True)
    plant_id: Mapped[str] = mapped_column(ForeignKey("plant.plant_id"))
    role: Mapped[str] = mapped_column(String(10))
    display_name: Mapped[str] = mapped_column(String(60))


class OperatorShift(Base):
    __tablename__ = "operator_shift"
    shift_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    plant_id: Mapped[str] = mapped_column(ForeignKey("plant.plant_id"))
    shift_code: Mapped[str] = mapped_column(String(1))
    shift_date: Mapped[date] = mapped_column(Date)
    start_ts: Mapped[datetime] = mapped_column(DateTime)
    end_ts: Mapped[datetime] = mapped_column(DateTime)
    operator_id: Mapped[str] = mapped_column(ForeignKey("staff.staff_id"))


# ------------------------------- events -----------------------------------
class MachineStateEvent(Base):
    __tablename__ = "machine_state_event"
    state_event_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    machine_id: Mapped[str] = mapped_column(ForeignKey("machine.machine_id"))
    event_ts: Mapped[datetime] = mapped_column(DateTime)
    from_state: Mapped[str] = mapped_column(String(12))
    to_state: Mapped[str] = mapped_column(String(12))
    reason: Mapped[str] = mapped_column(String(100))


class InterlockStateEvent(Base):
    __tablename__ = "interlock_state_event"
    interlock_event_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    interlock_id: Mapped[str] = mapped_column(ForeignKey("interlock.interlock_id"))
    event_ts: Mapped[datetime] = mapped_column(DateTime)
    from_state: Mapped[str] = mapped_column(String(10))
    to_state: Mapped[str] = mapped_column(String(10))
    machine_state_snapshot: Mapped[str] = mapped_column(String(12))
    reason: Mapped[str] = mapped_column(String(100))
    actor: Mapped[str] = mapped_column(String(12))


class AlarmEvent(Base):
    __tablename__ = "alarm_event"
    alarm_event_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    machine_id: Mapped[str] = mapped_column(ForeignKey("machine.machine_id"))
    alarm_def_id: Mapped[str] = mapped_column(ForeignKey("alarm_definition.alarm_def_id"))
    shift_id: Mapped[str] = mapped_column(ForeignKey("operator_shift.shift_id"))
    interlock_id: Mapped[Optional[str]] = mapped_column(ForeignKey("interlock.interlock_id"), nullable=True)
    raised_ts: Mapped[datetime] = mapped_column(DateTime)
    cleared_ts: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    received_ts: Mapped[datetime] = mapped_column(DateTime)
    source_seq: Mapped[int] = mapped_column(Integer)
    machine_state: Mapped[str] = mapped_column(String(12))
    definition: Mapped[AlarmDefinition] = relationship()


class Acknowledgement(Base):        # 1:1 (optional) with alarm_event
    __tablename__ = "acknowledgement"
    ack_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    alarm_event_id: Mapped[str] = mapped_column(ForeignKey("alarm_event.alarm_event_id"), unique=True)
    shift_id: Mapped[str] = mapped_column(ForeignKey("operator_shift.shift_id"))
    operator_id: Mapped[str] = mapped_column(ForeignKey("staff.staff_id"))
    ack_ts: Mapped[datetime] = mapped_column(DateTime)
    response_sec: Mapped[Decimal] = mapped_column(DECIMAL(12, 3))
    ack_method: Mapped[str] = mapped_column(String(8))


class Incident(Base):
    __tablename__ = "incident"
    incident_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    machine_id: Mapped[str] = mapped_column(ForeignKey("machine.machine_id"))
    zone_id: Mapped[str] = mapped_column(ForeignKey("safety_zone.zone_id"))
    trigger_alarm_id: Mapped[Optional[str]] = mapped_column(ForeignKey("alarm_event.alarm_event_id"), nullable=True)
    rule_code: Mapped[str] = mapped_column(String(24))
    severity: Mapped[str] = mapped_column(String(10))
    opened_ts: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(16))
    closed_ts: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reported_by: Mapped[str] = mapped_column(String(12))
    description: Mapped[str] = mapped_column(String(200))
    actions: Mapped[list["CorrectiveAction"]] = relationship(back_populates="incident",
                                                             order_by="CorrectiveAction.action_id")


class IncidentAlarm(Base):          # N:M bridge
    __tablename__ = "incident_alarm"
    incident_id: Mapped[str] = mapped_column(ForeignKey("incident.incident_id"), primary_key=True)
    alarm_event_id: Mapped[str] = mapped_column(ForeignKey("alarm_event.alarm_event_id"), primary_key=True)
    link_role: Mapped[str] = mapped_column(String(8))


class CorrectiveAction(Base):
    __tablename__ = "corrective_action"
    action_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incident.incident_id"))
    action_type: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(String(150))
    owner_id: Mapped[str] = mapped_column(ForeignKey("staff.staff_id"))
    created_ts: Mapped[datetime] = mapped_column(DateTime)
    due_ts: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(24))
    started_ts: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_ts: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    verified_ts: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    verified_by: Mapped[Optional[str]] = mapped_column(ForeignKey("staff.staff_id"), nullable=True)
    closed_ts: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    incident: Mapped[Incident] = relationship(back_populates="actions")


# --------------------------- evaluation only ------------------------------
class GroundTruth(Base):
    __tablename__ = "ground_truth"
    gt_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    category: Mapped[str] = mapped_column(String(10))
    issue_type: Mapped[str] = mapped_column(String(32))
    record_type: Mapped[str] = mapped_column(String(24))
    record_id: Mapped[str] = mapped_column(String(32))
    related_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    event_ts: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    detail: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    expected_decision: Mapped[str] = mapped_column(String(40))