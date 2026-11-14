"""Alarm + acknowledgement queries (one wide, joined row per alarm for analytics)."""
from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

ALARM_FACTS_SQL = """
SELECT a.alarm_event_id, a.machine_id, m.plant_id, m.machine_name, a.alarm_def_id, d.alarm_code,
       d.base_code, d.alarm_name, d.category, d.severity, d.ack_sla_sec, a.shift_id, a.interlock_id,
       a.raised_ts, a.cleared_ts, a.received_ts, a.source_seq, a.machine_state,
       z.zone_id, z.hazard_level,
       k.ack_id, k.ack_ts, k.response_sec, k.operator_id AS ack_operator_id
FROM alarm_event a
JOIN machine m           ON m.machine_id = a.machine_id
JOIN alarm_definition d  ON d.alarm_def_id = a.alarm_def_id
JOIN machine_zone mz     ON mz.machine_id = a.machine_id AND mz.is_primary = 1
JOIN safety_zone z       ON z.zone_id = mz.zone_id
LEFT JOIN acknowledgement k ON k.alarm_event_id = a.alarm_event_id
ORDER BY a.raised_ts, a.alarm_event_id
"""


def fetch_alarm_facts(db: Session) -> list[dict]:
    rows = []
    for r in db.execute(text(ALARM_FACTS_SQL)).mappings():
        d = dict(r)
        d["response_sec"] = float(d["response_sec"]) if d["response_sec"] is not None else None
        rows.append(d)
    return rows


def fetch_alarms_by_ids(db: Session, ids: list[str]) -> list[dict]:
    if not ids:
        return []
    sql = ALARM_FACTS_SQL.replace("ORDER BY", "WHERE a.alarm_event_id IN :ids ORDER BY")
    stmt = text(sql).bindparams(bindparam("ids", expanding=True))
    return [dict(r) for r in db.execute(stmt, {"ids": ids}).mappings()]


def fetch_alarms_for_machine(db: Session, machine_id: str, start, end) -> list[dict]:
    sql = ALARM_FACTS_SQL.replace(
        "ORDER BY", "WHERE a.machine_id = :m AND a.raised_ts BETWEEN :s AND :e ORDER BY")
    return [dict(r) for r in db.execute(text(sql), {"m": machine_id, "s": start, "e": end}).mappings()]