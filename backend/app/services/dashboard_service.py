"""Overview KPIs: volumes, alarm trends, severity mix, acknowledgement performance, per-plant summary."""
import statistics
from collections import Counter, defaultdict

from generator.rules import ACK_SLA_SEC, SEVERITIES


def kpis(ctx) -> dict:
    alarms = ctx.unique_alarms                            # replay duplicates excluded from KPIs
    sev = Counter(a["severity"] for a in alarms)
    acked = [a for a in alarms if a["ack_status"] in ("ON_TIME", "DELAYED")]
    delayed = [a for a in alarms if a["ack_status"] == "DELAYED"]
    by_day = defaultdict(Counter)
    for a in alarms:
        by_day[a["raised_ts"].date().isoformat()][a["severity"]] += 1
    ack_perf = []
    for s in SEVERITIES:
        items = [a for a in alarms if a["severity"] == s]
        resp = [a["response_sec"] for a in items if a["ack_status"] in ("ON_TIME", "DELAYED")]
        ack_perf.append({
            "severity": s, "sla_sec": ACK_SLA_SEC[s], "alarms": len(items),
            "acked_pct": round(100 * len(resp) / max(len(items), 1), 1),
            "mtta_sec": round(statistics.mean(resp), 1) if resp else None,
            "median_sec": round(statistics.median(resp), 1) if resp else None,
            "delayed_pct": round(100 * sum(1 for a in items if a["ack_status"] == "DELAYED") / max(len(resp), 1), 1),
        })
    plants = defaultdict(lambda: {"alarms": 0, "critical": 0, "delayed": 0, "floods": 0, "incidents": 0})
    for a in alarms:
        p = plants[a["plant_id"]]
        p["alarms"] += 1
        p["critical"] += a["severity"] == "CRITICAL"
        p["delayed"] += a["ack_status"] == "DELAYED"
    for f in ctx.floods:
        plants[f["plant_id"]]["floods"] += 1
    for i in ctx.incidents:
        plants[i["plant_id"]]["incidents"] += 1
    shifts = defaultdict(lambda: [0, 0])
    for a in acked:
        code = a["shift_id"][-1]
        shifts[code][0] += 1
        shifts[code][1] += a["ack_status"] == "DELAYED"
    inc_status = Counter(i["status"] for i in ctx.incidents)
    return {
        "window": {"start": ctx.window_start, "end": ctx.window_end},
        "totals": {
            "plants": len({m["plant_id"] for m in ctx.machines}), "machines": len(ctx.machines),
            "alarm_definitions": len({a["alarm_def_id"] for a in ctx.alarms}),
            "alarm_events_raw": len(ctx.alarms), "alarm_events_unique": len(alarms),
            "replay_duplicates_removed": len(ctx.alarms) - len(alarms),
            "acknowledgements": len(acked) + sum(1 for a in alarms if a["ack_status"] == "INVALID"),
            "incidents": len(ctx.incidents), "open_incidents": len(ctx.incidents) - inc_status.get("CLOSED", 0),
            "corrective_actions": len(ctx.actions), "state_events": len(ctx.state_events),
            "interlock_events": len(ctx.ilk_events), "floods": len(ctx.floods),
            "nuisance_pairs": sum(1 for p in ctx.chatter_pairs if p["is_nuisance"]),
        },
        "rates": {
            "alarms_per_day": round(len(alarms) / max((ctx.window_end - ctx.window_start).days, 1), 1),
            "acked_pct": round(100 * len(acked) / len(alarms), 1),
            "delayed_ack_pct": round(100 * len(delayed) / max(len(acked), 1), 1),
            "critical_alarms": sev.get("CRITICAL", 0),
            "mtta_sec": round(statistics.mean(a["response_sec"] for a in acked), 1),
        },
        "severity_mix": [{"severity": s, "count": sev.get(s, 0)} for s in SEVERITIES],
        "category_mix": [{"category": k, "count": v} for k, v in Counter(a["category"] for a in alarms).most_common()],
        "machine_state_at_raise": [{"state": k, "count": v} for k, v in Counter(a["machine_state"] for a in alarms).most_common()],
        "alarms_per_day": [{"date": d, **{s: c.get(s, 0) for s in SEVERITIES}, "total": sum(c.values())}
                           for d, c in sorted(by_day.items())],
        "ack_performance": ack_perf,
        "shift_performance": [{"shift": k, "acked": v[0], "delayed_pct": round(100 * v[1] / max(v[0], 1), 1)}
                              for k, v in sorted(shifts.items())],
        "plants": [{"plant_id": k, **v} for k, v in sorted(plants.items())],
        "incident_rules": [{"rule_code": k, "count": v} for k, v in Counter(i["rule_code"] for i in ctx.incidents).most_common()],
        "incident_status": [{"status": k, "count": v} for k, v in inc_status.most_common()],
        "context_build_seconds": ctx.build_seconds,
    }