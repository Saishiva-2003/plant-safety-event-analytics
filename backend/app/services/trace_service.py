"""Incident traceability: one ordered timeline of machine states, interlock states, alarms,
acknowledgements and corrective actions around an incident."""
from datetime import timedelta

from sqlalchemy.orm import Session

from app.repositories import event_repo, incident_repo


def incident_trace(ctx, db: Session, incident_id: str) -> dict | None:
    inc = next((i for i in ctx.incidents if i["incident_id"] == incident_id), None)
    if inc is None:
        return None
    links = incident_repo.links_for_incident(db, incident_id)
    linked = [ctx.by_id[l["alarm_event_id"]] | {"link_role": l["link_role"]} for l in links if l["alarm_event_id"] in ctx.by_id]
    anchor = min([a["raised_ts"] for a in linked] + [inc["opened_ts"]])
    start, end = anchor - timedelta(minutes=30), inc["opened_ts"] + timedelta(minutes=30)
    states = event_repo.state_events_for_machine(db, inc["machine_id"], start, end)
    ilks = event_repo.interlock_events_for_machine(db, inc["machine_id"], start, end)
    actions = [a for a in ctx.actions if a["incident_id"] == incident_id]
    state_at_open = event_repo.last_state_before(db, inc["machine_id"], inc["opened_ts"])
    state_before = event_repo.last_state_before(db, inc["machine_id"], start)

    tl = [{"ts": start, "type": "STATE", "title": f"Machine state: {state_before}", "detail": "state at start of window"}]
    # interlocks that were already TRIPPED / BYPASSED before the window -> show the event that caused it
    for iid in ctx.interlocks_by_machine.get(inc["machine_id"], []):
        if ctx.ilk_index.state_at(iid, start) != "ENGAGED":
            prior = [e for e in ctx.ilk_events if e["interlock_id"] == iid and e["event_ts"] <= start]
            if prior:
                e = max(prior, key=lambda x: x["event_ts"])
                ilks.insert(0, {**e, "reason": e["reason"] + " (still active at window start)"})
    for s in states:
        tl.append({"ts": s["event_ts"], "type": "STATE", "title": f"{s['from_state']} -> {s['to_state']}",
                   "detail": s["reason"], "ref": s["state_event_id"]})
    for e in ilks:
        tl.append({"ts": e["event_ts"], "type": "INTERLOCK",
                   "title": f"{e['interlock_type']} {e['from_state']} -> {e['to_state']}",
                   "detail": f"{e['reason']} (actor {e['actor']}, machine {e['machine_state_snapshot']})",
                   "ref": e["interlock_event_id"],
                   "flag": "IMPOSSIBLE_STATE" if e["to_state"] == "TRIPPED" and e["machine_state_snapshot"] == "RUNNING" else None})
    for a in linked:
        tl.append({"ts": a["raised_ts"], "type": "ALARM", "title": f"{a['severity']} {a['alarm_code']} ({a['link_role']})",
                   "detail": f"{a['alarm_name']} - machine {a['machine_state']}, interlocks {a['interlock_state_at_raise']}, "
                             f"priority {a['priority_score']}", "ref": a["alarm_event_id"], "severity": a["severity"]})
        if a["ack_id"]:
            tl.append({"ts": a["ack_ts"], "type": "ACK", "title": f"Acknowledged by {a['ack_operator_id']}",
                       "detail": f"response {a['response_sec']:.0f}s ({a['ack_status']})", "ref": a["ack_id"],
                       "flag": "ACK_BEFORE_ALARM" if a["ack_status"] == "INVALID" else None})
    tl.append({"ts": inc["opened_ts"], "type": "INCIDENT", "title": f"Incident opened ({inc['rule_code']})",
               "detail": inc["description"], "ref": incident_id, "severity": inc["severity"]})
    for a in actions:
        for col, label in (("created_ts", "created"), ("started_ts", "started"), ("completed_ts", "completed"),
                           ("verified_ts", "verified"), ("closed_ts", "closed")):
            if a[col]:
                tl.append({"ts": a[col], "type": "ACTION", "title": f"{a['action_id']} {label}",
                           "detail": a["description"] + (f" (verified by {a['verified_by']})" if col == "verified_ts" else ""),
                           "ref": a["action_id"],
                           "flag": "CLOSED_NO_VERIFICATION" if col == "closed_ts" and not a["verified_ts"] else None})
    tl.sort(key=lambda x: (x["ts"], x["type"]))

    flags = []
    if not inc["trigger_alarm_id"] and not links:
        flags.append("INCIDENT_NO_TRIGGER: no trigger alarm and no context - cannot be traced")
    flags += [f"{x['flag']}: {x['ref']}" for x in tl if x.get("flag")]
    return {
        "incident": inc | {"traceable": bool(inc["trigger_alarm_id"] or links)},
        "machine_state_at_open": state_at_open, "window_start": start, "window_end": end,
        "linked_alarms": len(linked), "state_events": len(states), "interlock_events": len(ilks),
        "actions": actions, "flags": flags, "traceable": bool(inc["trigger_alarm_id"] or links),
        "timeline": tl,
    }