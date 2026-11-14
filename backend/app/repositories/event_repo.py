"""Machine-state and interlock-state history queries (append-only event tables)."""
from sqlalchemy import text
from sqlalchemy.orm import Session


def fetch_all_state_events(db: Session) -> list[dict]:
    sql = "SELECT state_event_id, machine_id, event_ts, from_state, to_state, reason FROM machine_state_event"
    return [dict(r) for r in db.execute(text(sql)).mappings()]


def fetch_all_interlock_events(db: Session) -> list[dict]:
    sql = """SELECT e.interlock_event_id, e.interlock_id, i.machine_id, i.interlock_type, e.event_ts,
                    e.from_state, e.to_state, e.machine_state_snapshot, e.reason, e.actor
             FROM interlock_state_event e JOIN interlock i ON i.interlock_id = e.interlock_id"""
    return [dict(r) for r in db.execute(text(sql)).mappings()]


def state_events_for_machine(db: Session, machine_id: str, start, end) -> list[dict]:
    sql = """SELECT state_event_id, machine_id, event_ts, from_state, to_state, reason
             FROM machine_state_event WHERE machine_id = :m AND event_ts BETWEEN :s AND :e
             ORDER BY event_ts, state_event_id"""
    return [dict(r) for r in db.execute(text(sql), {"m": machine_id, "s": start, "e": end}).mappings()]


def last_state_before(db: Session, machine_id: str, ts) -> str:
    sql = """SELECT to_state FROM machine_state_event WHERE machine_id = :m AND event_ts <= :t
             ORDER BY event_ts DESC, state_event_id DESC LIMIT 1"""
    return db.execute(text(sql), {"m": machine_id, "t": ts}).scalar() or "OFF"


def interlock_events_for_machine(db: Session, machine_id: str, start, end) -> list[dict]:
    sql = """SELECT e.interlock_event_id, e.interlock_id, i.interlock_type, e.event_ts, e.from_state,
                    e.to_state, e.machine_state_snapshot, e.reason, e.actor
             FROM interlock_state_event e JOIN interlock i ON i.interlock_id = e.interlock_id
             WHERE i.machine_id = :m AND e.event_ts BETWEEN :s AND :e
             ORDER BY e.event_ts, e.interlock_event_id"""
    return [dict(r) for r in db.execute(text(sql), {"m": machine_id, "s": start, "e": end}).mappings()]