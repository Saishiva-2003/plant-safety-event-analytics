"""Repeated unsafe conditions: same machine + same incident rule >= 3 times in a rolling 7 days."""
from collections import Counter

from generator.rules import INCIDENT_RULES, REPEAT_MIN_COUNT, REPEAT_WINDOW_DAYS, find_repeated_unsafe


def repeated_unsafe(ctx) -> dict:
    clean = [i for i in ctx.incidents if i["trigger_alarm_id"] or i["linked_alarms"] > 0]
    machines = {m["machine_id"]: m for m in ctx.machines}
    inc_by_id = {i["incident_id"]: i for i in ctx.incidents}
    open_actions = Counter(a["incident_id"] for a in ctx.actions if a["status"] != "CLOSED")
    rows = []
    for r in find_repeated_unsafe(clean):
        m = machines[r["machine_id"]]
        incs = [inc_by_id[x] for x in r["incident_ids"]]
        all_for_pair = [i for i in clean if i["machine_id"] == r["machine_id"] and i["rule_code"] == r["rule_code"]]
        rows.append({
            **{k: v for k, v in r.items()},
            "machine_name": m["machine_name"], "plant_id": m["plant_id"], "machine_type": m["machine_type"],
            "zone_name": m["zone_name"], "hazard_level": m["hazard_level"],
            "rule_description": INCIDENT_RULES[r["rule_code"]],
            "risk_score": r["max_count_in_window"] * m["hazard_level"] * (2 if r["rule_code"] == "R1_BYPASS_CRITICAL" else 1),
            "open_incidents": sum(1 for i in all_for_pair if i["status"] != "CLOSED"),
            "open_actions": sum(open_actions[i["incident_id"]] for i in all_for_pair),
            "last_incident_ts": max(i["opened_ts"] for i in all_for_pair),
            "incidents": [{"incident_id": i["incident_id"], "opened_ts": i["opened_ts"], "status": i["status"]} for i in incs],
        })
    rows.sort(key=lambda x: (-x["risk_score"], x["machine_id"]))
    per_machine = Counter(i["machine_id"] for i in clean if i["rule_code"] != "MANUAL_REPORT")
    return {
        "rule": f"same machine + same rule >= {REPEAT_MIN_COUNT} incidents within {REPEAT_WINDOW_DAYS} days",
        "conditions": len(rows), "machines_affected": len({r["machine_id"] for r in rows}),
        "items": rows,
        "incidents_per_machine": [{"machine_id": k, "machine_name": machines[k]["machine_name"], "incidents": v}
                                  for k, v in per_machine.most_common(15)],
    }