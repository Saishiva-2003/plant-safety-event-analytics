"""Master-data queries (plants, zones, machines, interlocks, alarm definitions, staff)."""
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.entities import AlarmDefinition, Interlock, Machine, Plant, SafetyZone


def list_plants(db: Session) -> list[Plant]:
    return list(db.scalars(select(Plant).order_by(Plant.plant_id)))


def list_zones(db: Session) -> list[SafetyZone]:
    return list(db.scalars(select(SafetyZone).order_by(SafetyZone.zone_id)))


def list_machines(db: Session, plant_id: str | None = None) -> list[dict]:
    sql = """
        SELECT m.machine_id, m.plant_id, m.machine_name, m.machine_type, m.criticality, m.manufacturer,
               z.zone_id, z.zone_name, z.hazard_level
        FROM machine m
        JOIN machine_zone mz ON mz.machine_id = m.machine_id AND mz.is_primary = 1
        JOIN safety_zone z ON z.zone_id = mz.zone_id
        WHERE (:plant IS NULL OR m.plant_id = :plant)
        ORDER BY m.machine_id"""
    return [dict(r) for r in db.execute(text(sql), {"plant": plant_id}).mappings()]


def get_machine(db: Session, machine_id: str) -> Machine | None:
    return db.get(Machine, machine_id)


def list_interlocks(db: Session, machine_id: str | None = None) -> list[Interlock]:
    q = select(Interlock).order_by(Interlock.interlock_id)
    if machine_id:
        q = q.where(Interlock.machine_id == machine_id)
    return list(db.scalars(q))


def list_alarm_definitions(db: Session) -> list[AlarmDefinition]:
    return list(db.scalars(select(AlarmDefinition).order_by(AlarmDefinition.alarm_def_id)))


def table_counts(db: Session, tables: list[str]) -> dict[str, int]:
    return {t: db.execute(text(f"SELECT COUNT(*) FROM `{t}`")).scalar() for t in tables}