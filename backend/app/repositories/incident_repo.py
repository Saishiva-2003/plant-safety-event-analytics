"""Incident, incident_alarm (bridge) and corrective-action queries."""
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.models.entities import CorrectiveAction, Incident


def list_incidents(db: Session) -> list[dict]:
    sql = """
        SELECT i.incident_id, i.machine_id, m.machine_name, m.plant_id, i.zone_id, z.zone_name, z.hazard_level,
               i.trigger_alarm_id, i.rule_code, i.severity, i.opened_ts, i.status, i.closed_ts,
               i.reported_by, i.description,
               (SELECT COUNT(*) FROM incident_alarm ia WHERE ia.incident_id = i.incident_id) AS linked_alarms,
               (SELECT COUNT(*) FROM corrective_action c WHERE c.incident_id = i.incident_id) AS actions_total,
               (SELECT COUNT(*) FROM corrective_action c WHERE c.incident_id = i.incident_id
                    AND c.status = 'CLOSED') AS actions_closed
        FROM incident i
        JOIN machine m ON m.machine_id = i.machine_id
        JOIN safety_zone z ON z.zone_id = i.zone_id
        ORDER BY i.opened_ts, i.incident_id"""
    return [dict(r) for r in db.execute(text(sql)).mappings()]


def get_incident(db: Session, incident_id: str) -> Incident | None:
    q = select(Incident).options(selectinload(Incident.actions)).where(Incident.incident_id == incident_id)
    return db.scalars(q).first()


def links_for_incident(db: Session, incident_id: str) -> list[dict]:
    sql = "SELECT alarm_event_id, link_role FROM incident_alarm WHERE incident_id = :i"
    return [dict(r) for r in db.execute(text(sql), {"i": incident_id}).mappings()]


def all_links(db: Session) -> list[dict]:
    return [dict(r) for r in db.execute(text("SELECT incident_id, alarm_event_id, link_role FROM incident_alarm")).mappings()]


def list_actions(db: Session) -> list[CorrectiveAction]:
    return list(db.scalars(select(CorrectiveAction).order_by(CorrectiveAction.action_id)))