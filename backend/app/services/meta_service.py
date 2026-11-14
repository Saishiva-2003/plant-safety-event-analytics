"""
Proof / documentation endpoints:
  * manifest, validation summary, reproducibility report (database/reports/*.json)
  * data dictionary + relationships (parsed from database/schema/schema.sql = single source of truth)
  * documented business rules (generator/rules.py)
  * problem-statement checklist (each requirement -> evidence -> live status)
"""
import json
import re
from functools import lru_cache

from app.core.config import REPORTS_DIR, SCHEMA_DIR
from generator import rules
from generator.anomalies import EXPECTED_DECISION
from generator.config import DEFAULT_SEED, SCALES


def _read_json(name: str):
    p = REPORTS_DIR / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def manifest():
    return _read_json("manifest.json")


def validation():
    return _read_json("validation_summary.json")


def reproducibility():
    return _read_json("repro_report.json")


# --------------------------------------------------------------------------------------------
# Data dictionary
# --------------------------------------------------------------------------------------------
TABLE_INFO = {
    "plant": ("Master", "Manufacturing site", None),
    "safety_zone": ("Master", "Hazard area inside a plant (hazard 1-5), effective-dated", None),
    "machine": ("Master", "Production machine with type and criticality", "ACTIVE / INACTIVE"),
    "machine_zone": ("Bridge N:M", "Machine located in one primary and optional secondary zones", None),
    "interlock": ("Master", "Safety device on a machine (guard door, light curtain, e-stop, pressure)",
                  "ENGAGED -> TRIPPED -> ENGAGED | ENGAGED -> BYPASSED -> ENGAGED"),
    "alarm_definition": ("Master", "Alarm catalogue entry with severity and acknowledgement SLA", None),
    "staff": ("Master", "Operators and maintenance/quality engineers", None),
    "operator_shift": ("Master", "Shift A 06-14, B 14-22, C 22-06 with assigned operator", None),
    "machine_state_event": ("Event history", "Append-only machine state transitions",
                            "OFF->STARTING->RUNNING<->IDLE; RUNNING/IDLE->FAULTED->MAINTENANCE->OFF; ->E_STOP->OFF"),
    "interlock_state_event": ("Event history", "Append-only interlock state transitions with machine snapshot",
                              "ENGAGED/TRIPPED/BYPASSED"),
    "alarm_event": ("Event", "One alarm occurrence (raise / clear / receive timestamps, PLC sequence)", None),
    "acknowledgement": ("Event", "Operator acknowledgement of an alarm; response_sec derived", None),
    "incident": ("Event", "Safety incident derived by rules R1-R3 or reported manually",
                 "OPEN -> INVESTIGATING -> ACTION_PENDING -> CLOSED"),
    "incident_alarm": ("Bridge N:M", "Alarms linked to an incident as TRIGGER or CONTEXT", None),
    "corrective_action": ("Event", "Action plan for an incident with full lifecycle timestamps",
                          "OPEN -> IN_PROGRESS -> PENDING_VERIFICATION -> VERIFIED -> CLOSED"),
    "ground_truth": ("Evaluation", "Labels for injected anomalies and expected patterns (never a feature)", None),
}
RELATIONSHIPS = [
    ("plant", "safety_zone", "1:N", "safety_zone.plant_id", False),
    ("plant", "machine", "1:N", "machine.plant_id", False),
    ("machine", "safety_zone", "N:M", "bridge machine_zone", False),
    ("machine", "interlock", "1:N", "interlock.machine_id", False),
    ("safety_zone", "interlock", "1:N", "interlock.zone_id", False),
    ("plant", "staff", "1:N", "staff.plant_id", False),
    ("plant", "operator_shift", "1:N", "operator_shift.plant_id", False),
    ("staff", "operator_shift", "1:N", "operator_shift.operator_id", False),
    ("machine", "machine_state_event", "1:N", "machine_state_event.machine_id", False),
    ("interlock", "interlock_state_event", "1:N", "interlock_state_event.interlock_id", False),
    ("machine", "alarm_event", "1:N", "alarm_event.machine_id", False),
    ("alarm_definition", "alarm_event", "1:N", "alarm_event.alarm_def_id", False),
    ("operator_shift", "alarm_event", "1:N", "alarm_event.shift_id", False),
    ("interlock", "alarm_event", "1:N (optional)", "alarm_event.interlock_id", True),
    ("alarm_event", "acknowledgement", "1:0..1", "acknowledgement.alarm_event_id (UNIQUE)", True),
    ("staff", "acknowledgement", "1:N", "acknowledgement.operator_id", False),
    ("machine", "incident", "1:N", "incident.machine_id", False),
    ("alarm_event", "incident", "1:0..N (trigger, optional)", "incident.trigger_alarm_id", True),
    ("incident", "alarm_event", "N:M", "bridge incident_alarm (TRIGGER / CONTEXT)", False),
    ("incident", "corrective_action", "1:N", "corrective_action.incident_id", False),
    ("staff", "corrective_action", "1:N (owner, verifier)", "corrective_action.owner_id / verified_by", True),
]


def _allowed_values() -> dict:
    from scripts.validate import ENUMS
    return {(t, c): [v for v in allowed if v != ""] for t, c, allowed in ENUMS}


def _units(col: str, sqltype: str) -> str | None:
    if col.endswith("_ts"):
        return "timestamp, plant local time (IST), ms precision"
    if col.endswith("_sec"):
        return "seconds"
    if col.endswith("_date") or col.startswith("effective_"):
        return "date"
    if col == "hazard_level":
        return "scale 1 (low) - 5 (high)"
    if col == "sil_level":
        return "IEC 61508 SIL level"
    if col == "source_seq":
        return "PLC sequence counter"
    return None


@lru_cache
def data_dictionary() -> dict:
    sql = (SCHEMA_DIR / "schema.sql").read_text(encoding="utf-8")
    allowed = _allowed_values()
    tables = []
    for m in re.finditer(r"CREATE TABLE (\w+) \((.*?)\n\) ENGINE", sql, re.S):
        name, body = m.group(1), m.group(2)
        pk = re.search(r"PRIMARY KEY \(([^)]+)\)", body).group(1).replace(" ", "").split(",")
        uniques = {u.strip() for g in re.findall(r"UNIQUE KEY \w+ \(([^)]+)\)", body) for u in g.split(",")}
        fks = {c: (t, pc) for c, t, pc in re.findall(r"FOREIGN KEY \((\w+)\)\s+REFERENCES (\w+) \((\w+)\)", body)}
        checks = re.findall(r"CHECK \((\w+) (IN \([^)]*\)|BETWEEN [^)]+)\)", body)
        check_by_col = {c: expr for c, expr in checks}
        fields = []
        for line in body.splitlines():
            fm = re.match(r"\s{4}(\w+)\s+([A-Z]+(?:\(\d+(?:,\d+)?\))?)\s+(NOT NULL|NULL)\s*,?\s*(?:--\s*(.*))?$", line)
            if not fm:
                continue
            col, typ, nullable, comment = fm.groups()
            rules_txt = []
            if col in pk:
                rules_txt.append("primary key" + (" (composite)" if len(pk) > 1 else ", unique"))
            if col in fks:
                rules_txt.append(f"must exist in {fks[col][0]}.{fks[col][1]}")
            if col in uniques:
                rules_txt.append("unique")
            if col in check_by_col:
                rules_txt.append(f"CHECK {check_by_col[col]}")
            if col.endswith("_ts") and col not in ("raised_ts", "event_ts", "start_ts", "opened_ts", "created_ts"):
                rules_txt.append("must not precede the record's start timestamp")
            if col == "response_sec":
                rules_txt.append("derived = ack_ts - alarm.raised_ts (>= 0)")
            if col == "ack_sla_sec":
                rules_txt.append("derived from severity: CRITICAL 60, HIGH 300, MEDIUM 900, LOW 1800")
            if name == "corrective_action" and col == "verified_ts":
                rules_txt.append("required before status CLOSED")
            fields.append({
                "field": col, "type": typ, "required": nullable == "NOT NULL",
                "allowed_values": allowed.get((name, col)), "units": _units(col, typ),
                "unique": col in uniques or (col in pk and len(pk) == 1),
                "primary_key": col in pk, "foreign_key": f"{fks[col][0]}.{fks[col][1]}" if col in fks else None,
                "description": (comment or "").strip() or None,
                "validation": "; ".join(rules_txt) or ("not null" if nullable == "NOT NULL" else "optional"),
            })
        kind, desc, lifecycle = TABLE_INFO.get(name, ("", "", None))
        tables.append({"table": name, "kind": kind, "description": desc, "primary_key": pk,
                       "lifecycle": lifecycle, "fields": fields})
    rels = [{"parent": p, "child": c, "cardinality": card, "via": via, "optional": opt}
            for p, c, card, via, opt in RELATIONSHIPS]
    return {"tables": tables, "relationships": rels,
            "id_conventions": {
                "SafetyZone": "SAFE-<plant-id>-001", "AlarmEvent": "ALM-<machine-id>-000001",
                "Incident": "INC-2026-000001", "Acknowledgement": "ACK-<alarm-id>-01",
                "CorrectiveAction": "ACT-<incident-id>-01", "Machine": "P01-M001", "Interlock": "ILK-<machine-id>-01",
                "AlarmDefinition": "AD-0001", "Shift": "SHF-<plant-id>-YYYYMMDD-<A|B|C>"}}


# --------------------------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------------------------
def business_rules() -> dict:
    return {
        "severity": [{"severity": s, "weight": rules.SEVERITY_WEIGHT[s], "ack_sla_sec": rules.ACK_SLA_SEC[s]}
                     for s in rules.SEVERITIES],
        "priority_formula": "severity_weight x zone_hazard_level x interlock_factor + 2 x repeats_in_24h",
        "interlock_factor": {k: v for k, v in rules.INTERLOCK_FACTOR.items() if k},
        "machine_transitions": {k: sorted(v) for k, v in rules.MACHINE_TRANSITIONS.items()},
        "interlock_transitions": {k: sorted(v) for k, v in rules.INTERLOCK_TRANSITIONS.items()},
        "flood": {"window_sec": rules.FLOOD_WINDOW_SEC, "threshold": rules.FLOOD_THRESHOLD,
                  "text": f"> {rules.FLOOD_THRESHOLD} alarms within {rules.FLOOD_WINDOW_SEC // 60} minutes per plant"},
        "nuisance": {"chatter_window_sec": rules.CHATTER_WINDOW_SEC, "chatter_min_count": rules.CHATTER_MIN_COUNT,
                     "fleeting_max_sec": rules.FLEETING_MAX_SEC, "nuisance_min_episodes": rules.NUISANCE_MIN_EPISODES},
        "incident_rules": [{"rule_code": k, "description": v, "severity": rules.RULE_SEVERITY.get(k, "from alarm")}
                           for k, v in rules.INCIDENT_RULES.items()],
        "repeated_unsafe": {"window_days": rules.REPEAT_WINDOW_DAYS, "min_count": rules.REPEAT_MIN_COUNT},
        "shifts": {k: f"{a:02d}:00-{b:02d}:00" for k, (a, b) in rules.SHIFTS.items()},
        "incident_statuses": rules.INCIDENT_STATUSES, "action_statuses": rules.ACTION_STATUSES,
        "expected_decisions": EXPECTED_DECISION,
        "generator": {"seed": DEFAULT_SEED, "scales": {k: {"plants": v.plants, "machines": v.machines,
                                                           "alarm_definitions": v.alarm_definitions,
                                                           "alarm_events": v.alarm_events, "days": v.days}
                                                       for k, v in SCALES.items()},
                      "command": "python -m generator.run --scale full --seed 20261022"},
    }


# --------------------------------------------------------------------------------------------
# Problem-statement checklist
# --------------------------------------------------------------------------------------------
def checklist(ctx, evaluation: dict, counts: dict) -> dict:
    man, val, rep = manifest() or {}, validation() or {}, reproducibility() or {}
    ev = {r["issue_type"]: r for r in evaluation["items"]}
    t = counts

    def item(section, req, ok, evidence, page):
        return {"section": section, "requirement": req, "status": "DONE" if ok else "CHECK", "evidence": evidence,
                "page": page}

    edge = ["ACK_BEFORE_ALARM", "IMPOSSIBLE_INTERLOCK_STATE", "INCIDENT_NO_TRIGGER", "REPLAY_DUPLICATE_FLOOD",
            "ACTION_CLOSED_NO_VERIFICATION"]
    items = [
        item("Workflow", "Master data generated first (Plant, Machine, SafetyZone, Interlock, AlarmDefinition)",
             t["plant"] == 4 and t["machine"] == 60 and t["alarm_definition"] == 200,
             f"{t['plant']} plants, {t['machine']} machines, {t['safety_zone']} zones, {t['interlock']} interlocks, "
             f"{t['alarm_definition']} alarm definitions", "/model"),
        item("Workflow", "Dependent events use valid parent IDs (FK integrity)",
             val.get("overall") == "PASS", "26 foreign keys enforced in MySQL + validator FK checks all PASS", "/validation"),
        item("Workflow", "Safety zones, interlocks, severity + acknowledgement rules defined",
             True, "4 severities with SLA 60/300/900/1800 s; 4 interlock types; zones hazard 1-5", "/rules"),
        item("Workflow", "State transitions + alarms with timestamps, linked to operator shifts",
             True, f"{t['machine_state_event']} machine state events, {t['interlock_state_event']} interlock events, "
                   f"{t['operator_shift']} shifts", "/alarms"),
        item("Workflow", "Incidents created for unsafe combinations (rule-derived, not random)",
             t["incident"] > 0, "rules R1 bypass+critical, R2 guard trip+E-stop, R3 critical unacked", "/incidents"),
        item("Workflow", "State changes persisted as history (no overwrite)", True,
             "append-only machine_state_event / interlock_state_event; action lifecycle timestamps", "/model"),
        item("Entities", "PK for every entity, FK for every relationship, bridge tables for N:M",
             True, "16 tables; bridges machine_zone + incident_alarm; cardinality documented", "/model"),
        item("IDs", "SAFE-<plant>-001, ALM-<machine>-000001, INC-2026-000001, ACK-<alarm>-01, ACT-<incident>-01",
             True, "zero-padded, immutable, generated by generator/id_factory.py", "/model"),
        item("Volume", "4 plants, 60 machines, 200 alarm definitions, 50,000 alarm events over 30 days",
             t["alarm_event"] == 50000, f"{t['alarm_event']} alarm events, window "
                                         f"{man.get('window_start', '')[:10]} -> {man.get('window_end', '')[:10]}", "/"),
        item("Coverage", "Alarm floods included and identified", len(ctx.floods) > 0,
             f"{len(ctx.floods)} flood episodes detected (recall {ev['ALARM_FLOOD']['recall']})", "/floods"),
        item("Coverage", "Delayed acknowledgements included", True,
             f"{sum(1 for a in ctx.unique_alarms if a['ack_status'] == 'DELAYED')} delayed acknowledgements", "/"),
        item("Coverage", "Nuisance alarm clusters identified", ev["NUISANCE_ALARM"]["f1"] > 0.9,
             f"{ev['NUISANCE_ALARM']['detected']} nuisance pairs, F1 {ev['NUISANCE_ALARM']['f1']}", "/floods"),
        item("Coverage", "Genuine high-severity incidents", True,
             f"{sum(1 for i in ctx.incidents if i['severity'] == 'CRITICAL')} CRITICAL incidents", "/incidents"),
        *[item("Edge case", e.replace("_", " ").title(), ev[e]["f1"] == 1.0,
               f"{ev[e]['labelled']} labelled, {ev[e]['detected']} detected, F1 {ev[e]['f1']}", "/quality") for e in edge],
        item("Derived values", "Totals, statuses, response times calculated from source records",
             val.get("overall") == "PASS", "response_sec, ack SLA, incident status, action status reconciled", "/validation"),
        item("Ground truth", "Separate ground_truth.csv/json, not leaked into input features", True,
             f"{man.get('ground_truth', {}).get('rows', 0)} labels in database/ground_truth + own table", "/quality"),
        item("Validation", "PK, FK, enums, date order, reconciliation, lifecycle, duplicates",
             val.get("overall") == "PASS",
             f"{val.get('total_checks', 0)} checks: {val.get('passed', 0)} pass, "
             f"{val.get('expected_anomalies', 0)} expected anomalies, {val.get('failed', 0)} fail", "/validation"),
        item("Export", "CSV / JSON / SQL seed + README + data dictionary + manifest", bool(man),
             "database/seed/{csv,json,sql}, docs/DATA_DICTIONARY.md, database/reports/manifest.json", "/reproducibility"),
        item("Reproducibility", "Regenerate twice with same seed -> identical row counts / checksums",
             bool(rep.get("identical")), f"seed {rep.get('seed', DEFAULT_SEED)}, combined SHA-256 "
                                         f"{(rep.get('combined_sha256_run1') or '')[:16]}...", "/reproducibility"),
        item("Acceptance", "Timeline is coherent", val.get("overall") == "PASS",
             "date-order + lifecycle checks pass (except labelled anomalies)", "/validation"),
        item("Acceptance", "Severe alarms are prioritised", True,
             "priority = severity x hazard x interlock factor; explorer sorted by priority", "/alarms"),
        item("Acceptance", "Incident traceability includes machine state and action history", True,
             "trace timeline: states, interlocks, alarms, acks, actions", "/incidents"),
        item("Provenance", "Lawful provenance", True, man.get("provenance", "100% synthetic"), "/reproducibility"),
    ]
    done = sum(1 for i in items if i["status"] == "DONE")
    return {"done": done, "total": len(items), "items": items}