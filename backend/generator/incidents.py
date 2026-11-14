"""
Step 2c - Incidents and corrective actions.

Incidents are NOT randomly assigned: they are DERIVED by applying the documented
rules (generator/rules.py -> INCIDENT_RULES) to the generated alarms, machine
states, interlock states and acknowledgements.  Corrective-action timelines and
incident statuses are then derived from timestamps.
"""
import bisect
from datetime import timedelta

from generator import id_factory as ids
from generator.config import add_seconds
from generator.rules import (
    INCIDENT_CONTEXT_WINDOW_SEC, R2_ESTOP_WINDOW_SEC, R3_UNACKED_SEC, RULE_SEVERITY,
)

H = 3600.0


def derive_incidents(cfg, rng, alarms, acks, defs, state_events, ilk_index, interlocks, primary_zone):
    def_by_id = {d["alarm_def_id"]: d for d in defs}
    ack_by_alarm = {a["alarm_event_id"]: a for a in acks}
    ilks_by_machine, ilk_zone = {}, {}
    for i in interlocks:
        ilks_by_machine.setdefault(i["machine_id"], []).append(i["interlock_id"])
        ilk_zone[i["interlock_id"]] = i["zone_id"]
    estops = {}
    for e in state_events:
        if e["to_state"] == "E_STOP":
            estops.setdefault(e["machine_id"], []).append(e["event_ts"])
    for v in estops.values():
        v.sort()

    candidates = []
    for a in alarms:
        d = def_by_id[a["alarm_def_id"]]
        rule = None
        # R1: CRITICAL safety alarm while any interlock BYPASSED and machine RUNNING
        if d["category"] == "SAFETY" and d["severity"] == "CRITICAL" and a["machine_state"] == "RUNNING":
            if any(ilk_index.state_at(i, a["raised_ts"]) == "BYPASSED" for i in ilks_by_machine[a["machine_id"]]):
                rule = "R1_BYPASS_CRITICAL"
        # R2: guard / light-curtain alarm while RUNNING, then E_STOP within 60 s
        if rule is None and d["base_code"] in ("GRD-OPEN", "LC-BREAK") and a["machine_state"] == "RUNNING":
            times = estops.get(a["machine_id"], [])
            k = bisect.bisect_left(times, a["raised_ts"])
            if k < len(times) and (times[k] - a["raised_ts"]).total_seconds() <= R2_ESTOP_WINDOW_SEC:
                rule = "R2_GUARD_TRIP_ESTOP"
        # R3: CRITICAL alarm not acknowledged within 300 s
        if rule is None and d["severity"] == "CRITICAL":
            ack = ack_by_alarm.get(a["alarm_event_id"])
            deadline = add_seconds(a["raised_ts"], R3_UNACKED_SEC)
            if deadline < cfg.end_ts and (ack is None or ack["response_sec"] > R3_UNACKED_SEC):
                rule = "R3_CRITICAL_UNACKED"
        if rule is None:
            continue
        opened = (add_seconds(a["raised_ts"], R3_UNACKED_SEC + rng.uniform(5, 60)) if rule == "R3_CRITICAL_UNACKED"
                  else add_seconds(a["raised_ts"], rng.uniform(60, 600)))
        if opened >= cfg.end_ts:
            continue
        candidates.append({
            "machine_id": a["machine_id"], "plant_id": a["plant_id"],
            "zone_id": ilk_zone.get(a["interlock_id"]) or primary_zone[a["machine_id"]],
            "trigger_alarm_id": a["alarm_event_id"], "rule_code": rule,
            "severity": RULE_SEVERITY[rule], "opened_ts": opened, "reported_by": "SYSTEM",
            "description": f"{rule}: {d['alarm_name']}", "_trigger": a,
        })
    return candidates


def manual_reports(cfg, rng, alarms, acks, shifts, primary_zone, taken_ids, count):
    """Operator near-miss reports: no trigger alarm, but linked to context alarms (traceable)."""
    shift_by_id = {s["shift_id"]: s for s in shifts}
    pool = [a for a in alarms if a["severity"] in ("HIGH", "CRITICAL") and a["_source"] != "FLOOD"
            and a["alarm_event_id"] not in taken_ids]
    picks = rng.sample(pool, min(count, len(pool)))
    out = []
    for a in sorted(picks, key=lambda x: x["raised_ts"]):
        opened = add_seconds(a["raised_ts"], rng.uniform(10 * 60, 120 * 60))
        if opened >= cfg.end_ts:
            continue
        out.append({
            "machine_id": a["machine_id"], "plant_id": a["plant_id"], "zone_id": primary_zone[a["machine_id"]],
            "trigger_alarm_id": None, "rule_code": "MANUAL_REPORT", "severity": a["severity"],
            "opened_ts": opened, "reported_by": shift_by_id[a["shift_id"]]["operator_id"],
            "description": "Near-miss reported by operator", "_context_alarm": a,
        })
    return out


ACTION_TEXT = {
    "R1_BYPASS_CRITICAL": ["Remove bypass key and audit bypass log", "Retrain maintenance on bypass permit",
                           "Install bypass time-out relay"],
    "R2_GUARD_TRIP_ESTOP": ["Inspect guard switch and door alignment", "Brief operators on guarded-area entry",
                            "Add warning signage at guard door"],
    "R3_CRITICAL_UNACKED": ["Review alarm response staffing", "Re-prioritise HMI alarm display",
                            "Coach operator on critical alarm response"],
    "MANUAL_REPORT": ["Investigate near-miss report", "Update risk assessment", "Toolbox talk with crew"],
}
ACTION_TYPE_BY_IDX = ["ENGINEERING", "TRAINING", "ADMINISTRATIVE"]
DUE_DAYS = {"CRITICAL": 3, "HIGH": 5, "MEDIUM": 7, "LOW": 10}


def finalize_incidents(cfg, rng, candidates, alarms, staff):
    """Assign INC IDs in time order, link alarms (bridge), build actions, derive statuses."""
    end = cfg.end_ts
    engineers = {}
    for s in staff:
        if s["role"] == "ENGINEER":
            engineers.setdefault(s["plant_id"], []).append(s["staff_id"])
    alarms_by_machine = {}
    for a in alarms:
        alarms_by_machine.setdefault(a["machine_id"], []).append(a)
    for v in alarms_by_machine.values():
        v.sort(key=lambda x: x["raised_ts"])
    times_by_machine = {k: [a["raised_ts"] for a in v] for k, v in alarms_by_machine.items()}

    def context_alarms(anchor):
        mid = anchor["machine_id"]
        times = times_by_machine[mid]
        lo = bisect.bisect_left(times, add_seconds(anchor["raised_ts"], -INCIDENT_CONTEXT_WINDOW_SEC))
        hi = bisect.bisect_left(times, anchor["raised_ts"])
        return [a for a in alarms_by_machine[mid][lo:hi] if a is not anchor][-5:]

    candidates.sort(key=lambda c: (c["opened_ts"], c["machine_id"]))
    incidents, links, actions = [], [], []
    for n, c in enumerate(candidates, start=1):
        inc_id = ids.incident_id(n)
        c["incident_id"] = inc_id
        # ---- bridge: incident <-> alarm (N:M) ----
        if c.get("_trigger"):
            links.append({"incident_id": inc_id, "alarm_event_id": c["_trigger"]["alarm_event_id"], "link_role": "TRIGGER"})
            anchor = c["_trigger"]
        elif c.get("_context_alarm"):
            links.append({"incident_id": inc_id, "alarm_event_id": c["_context_alarm"]["alarm_event_id"], "link_role": "CONTEXT"})
            anchor = c["_context_alarm"]
        else:
            anchor = None                   # injected: no triggering context
        if anchor is not None:
            for ca in context_alarms(anchor):
                links.append({"incident_id": inc_id, "alarm_event_id": ca["alarm_event_id"], "link_role": "CONTEXT"})

        # ---- corrective actions with lifecycle timestamps ----
        n_actions = 1 if rng.random() < 0.6 else (2 if rng.random() < 0.75 else 3)
        texts = ACTION_TEXT.get(c["rule_code"], ACTION_TEXT["MANUAL_REPORT"])
        inc_actions = []
        for k in range(1, n_actions + 1):
            created = add_seconds(c["opened_ts"], rng.uniform(0.5 * H, 24 * H))
            if created >= end:
                continue
            owner, verifier = rng.sample(engineers[c["plant_id"]], 2)
            started = add_seconds(created, rng.uniform(1 * H, 48 * H))
            completed = add_seconds(started, rng.uniform(4 * H, 6 * 24 * H))
            verified = add_seconds(completed, rng.uniform(4 * H, 3 * 24 * H))
            closed = add_seconds(verified, rng.uniform(0.5 * H, 24 * H))
            steps = [("IN_PROGRESS", started), ("PENDING_VERIFICATION", completed),
                     ("VERIFIED", verified), ("CLOSED", closed)]
            status = "OPEN"
            reached = {}
            for st, ts in steps:
                if ts < end:
                    status, reached[st] = st, ts
            a = {
                "action_id": ids.action_id(inc_id, k), "incident_id": inc_id,
                "action_type": ACTION_TYPE_BY_IDX[(k - 1) % 3], "description": texts[(k - 1) % len(texts)],
                "owner_id": owner, "created_ts": created,
                "due_ts": created + timedelta(days=DUE_DAYS[c["severity"]]),
                "status": status, "started_ts": reached.get("IN_PROGRESS"),
                "completed_ts": reached.get("PENDING_VERIFICATION"),
                "verified_ts": reached.get("VERIFIED"),
                "verified_by": verifier if "VERIFIED" in reached else None,
                "closed_ts": reached.get("CLOSED"),
            }
            inc_actions.append(a)
        actions.extend(inc_actions)

        # ---- incident status derived from its actions ----
        if not inc_actions:
            status, closed_ts = "OPEN", None
        elif all(a["status"] == "CLOSED" for a in inc_actions):
            status, closed_ts = "CLOSED", max(a["closed_ts"] for a in inc_actions)
        elif all(a["status"] == "OPEN" for a in inc_actions):
            status, closed_ts = "INVESTIGATING", None
        else:
            status, closed_ts = "ACTION_PENDING", None
        incidents.append({
            "incident_id": inc_id, "machine_id": c["machine_id"], "zone_id": c["zone_id"],
            "trigger_alarm_id": c["trigger_alarm_id"], "rule_code": c["rule_code"],
            "severity": c["severity"], "opened_ts": c["opened_ts"], "status": status,
            "closed_ts": closed_ts, "reported_by": c["reported_by"], "description": c["description"],
            "_gt": c.get("_gt"),
        })
    return incidents, links, actions