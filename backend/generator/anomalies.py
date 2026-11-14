"""
Step 5 - Inject LABELLED edge cases AFTER the valid baseline exists.

Every injected record gets a row in ground_truth (never a column in the input tables):
    ACK_BEFORE_ALARM               acknowledgement timestamp earlier than alarm raise
    IMPOSSIBLE_INTERLOCK_STATE     interlock TRIPPED while machine snapshot says RUNNING
    INCIDENT_NO_TRIGGER            incident with no trigger alarm and no linked context
    REPLAY_DUPLICATE_FLOOD         flood alarms re-ingested by a replay (same source_seq)
    ACTION_CLOSED_NO_VERIFICATION  corrective action CLOSED without verification
"""
from datetime import timedelta

from generator import id_factory as ids
from generator.config import add_seconds

EXPECTED_DECISION = {
    "ACK_BEFORE_ALARM": "REJECT_ACK_FLAG_CLOCK_SKEW",
    "IMPOSSIBLE_INTERLOCK_STATE": "FLAG_SENSOR_FAULT_QUARANTINE",
    "INCIDENT_NO_TRIGGER": "REQUIRE_CONTEXT_BEFORE_CLOSURE",
    "REPLAY_DUPLICATE_FLOOD": "DEDUPLICATE_EXCLUDE_FROM_KPIS",
    "ACTION_CLOSED_NO_VERIFICATION": "REOPEN_ACTION_REQUIRE_VERIFICATION",
    "ALARM_FLOOD": "SUPPRESS_LOW_PRIORITY_DURING_FLOOD",
    "NUISANCE_ALARM": "REVIEW_SETPOINT_DEADBAND",
    "REPEATED_UNSAFE_CONDITION": "ESCALATE_ROOT_CAUSE_REVIEW",
}


def contextless_incident_candidates(cfg, rng, machines, primary_zone, count):
    """Incidents that lack any triggering context (injected before IDs are assigned)."""
    out = []
    total = (cfg.end_ts - cfg.start_ts).total_seconds()
    for _ in range(count):
        m = rng.choice(machines)
        out.append({
            "machine_id": m["machine_id"], "plant_id": m["plant_id"], "zone_id": primary_zone[m["machine_id"]],
            "trigger_alarm_id": None, "rule_code": "MANUAL_REPORT", "severity": rng.choice(["HIGH", "MEDIUM"]),
            "opened_ts": add_seconds(cfg.start_ts, rng.uniform(3600, total - 3 * 86400)),
            "reported_by": "SYSTEM", "description": "Unsafe condition logged",
            "_gt": "INCIDENT_NO_TRIGGER",
        })
    return out


def inject_ack_before_alarm(cfg, rng, alarms, acks, incident_alarm_ids, count):
    alarm_by_id = {a["alarm_event_id"]: a for a in alarms}
    pool = [k for k in acks
            if alarm_by_id[k["alarm_event_id"]]["_source"] == "BASELINE"
            and alarm_by_id[k["alarm_event_id"]]["severity"] in ("LOW", "MEDIUM")
            and k["alarm_event_id"] not in incident_alarm_ids
            and alarm_by_id[k["alarm_event_id"]]["raised_ts"] > cfg.start_ts + timedelta(hours=2)]
    labels = []
    for k in sorted(rng.sample(pool, count), key=lambda x: x["ack_id"]):
        raised = alarm_by_id[k["alarm_event_id"]]["raised_ts"]
        k["ack_ts"] = add_seconds(raised, -rng.uniform(5, 120))
        k["response_sec"] = round((k["ack_ts"] - raised).total_seconds(), 3)   # derived -> negative
        labels.append(("ACK_BEFORE_ALARM", "acknowledgement", k["ack_id"], k["alarm_event_id"], k["ack_ts"],
                       f"ack {k['response_sec']} s relative to alarm raise"))
    return labels


def inject_impossible_interlock(rng, ilk_events, count):
    pool = [e for e in ilk_events if e["to_state"] == "TRIPPED"]
    labels = []
    for e in sorted(rng.sample(pool, count), key=lambda x: x["interlock_event_id"]):
        e["machine_state_snapshot"] = "RUNNING"
        labels.append(("IMPOSSIBLE_INTERLOCK_STATE", "interlock_state_event", e["interlock_event_id"],
                       e["interlock_id"], e["event_ts"], "interlock TRIPPED while machine RUNNING"))
    return labels


def inject_replay_floods(rng, alarms, flood_episodes, budget):
    """Duplicate whole floods (last one partially) with new IDs but the SAME source_seq."""
    max_seq = {}
    for a in alarms:
        max_seq[a["machine_id"]] = max(max_seq.get(a["machine_id"], 0), a["source_seq"])
    by_flood = {}
    for a in alarms:
        if a.get("_flood_id"):
            by_flood.setdefault(a["_flood_id"], []).append(a)
    order = [f["flood_id"] for f in flood_episodes]
    rng.shuffle(order)
    dups, labels, n = [], [], 0
    for fid in order:
        if n >= budget:
            break
        lag = rng.uniform(2 * 3600, 6 * 3600)          # replay arrives hours later
        for a in sorted(by_flood[fid], key=lambda x: (x["raised_ts"], x["alarm_event_id"])):
            if n >= budget:
                break
            num = max_seq[a["machine_id"]] + 1
            max_seq[a["machine_id"]] = num
            d = dict(a)
            d["alarm_event_id"] = ids.alarm_event_id(a["machine_id"], num)
            d["raised_ts"] = add_seconds(a["raised_ts"], rng.choice([0, 0.001, 0.002]))
            d["received_ts"] = add_seconds(a["received_ts"], lag)
            d["_source"] = "REPLAY"
            dups.append(d)
            labels.append(("REPLAY_DUPLICATE_FLOOD", "alarm_event", d["alarm_event_id"], a["alarm_event_id"],
                           d["raised_ts"], f"replay of {fid} (source_seq {a['source_seq']})"))
            n += 1
    return dups, labels


def inject_action_no_verification(rng, actions, count):
    pool = [a for a in actions if a["status"] == "CLOSED"]
    labels = []
    for a in sorted(rng.sample(pool, count), key=lambda x: x["action_id"]):
        a["verified_ts"], a["verified_by"] = None, None
        labels.append(("ACTION_CLOSED_NO_VERIFICATION", "corrective_action", a["action_id"], a["incident_id"],
                       a["closed_ts"], "status CLOSED but verified_ts/verified_by empty"))
    return labels


def build_ground_truth(anomaly_labels, incidents, flood_episodes, nuisance_pairs, repeated):
    rows = []

    def add(category, issue, rtype, rid, related, ts, detail):
        rows.append({"gt_id": ids.ground_truth_id(len(rows) + 1), "category": category, "issue_type": issue,
                     "record_type": rtype, "record_id": rid, "related_id": related, "event_ts": ts,
                     "detail": detail, "expected_decision": EXPECTED_DECISION[issue]})

    for issue, rtype, rid, related, ts, detail in anomaly_labels:
        add("ANOMALY", issue, rtype, rid, related, ts, detail)
    for inc in incidents:
        if inc.get("_gt") == "INCIDENT_NO_TRIGGER":
            add("ANOMALY", "INCIDENT_NO_TRIGGER", "incident", inc["incident_id"], inc["machine_id"],
                inc["opened_ts"], "no trigger alarm and no linked alarm context")
    for f in flood_episodes:
        add("PATTERN", "ALARM_FLOOD", "plant", f["plant_id"], f["flood_id"], f["start_ts"],
            f"{f['alarm_count']} alarms between {f['start_ts']:%H:%M} and {f['end_ts']:%H:%M}; "
            f"trigger {f['trigger_machine_id']}")
    for p in nuisance_pairs:
        add("PATTERN", "NUISANCE_ALARM", "alarm_definition", p["alarm_def_id"], p["machine_id"], None,
            f"chattering bad actor, {p['episodes']} episodes")
    for r in repeated:
        add("PATTERN", "REPEATED_UNSAFE_CONDITION", "machine", r["machine_id"], r["rule_code"], r["window_start"],
            f"{r['max_count_in_window']} incidents in 7 days ({r['total_count']} total): "
            + ",".join(r["incident_ids"]))
    return rows