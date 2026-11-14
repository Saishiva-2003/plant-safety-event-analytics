"""Nuisance-alarm detection: chattering (>= CHATTER_MIN_COUNT activations of the same alarm on the same
machine inside CHATTER_WINDOW_SEC) and fleeting alarms (clear within FLEETING_MAX_SEC)."""
from collections import defaultdict

from generator.rules import CHATTER_MIN_COUNT, CHATTER_WINDOW_SEC, FLEETING_MAX_SEC, NUISANCE_MIN_EPISODES


def detect_chatter(alarms: list[dict]) -> list[dict]:
    """Marks a['chatter'] and returns one row per (machine, alarm definition) pair."""
    groups = defaultdict(list)
    for a in alarms:
        a["chatter"] = False
        if not a.get("is_replay"):
            groups[(a["machine_id"], a["alarm_def_id"])].append(a)
    pairs = []
    for (machine, adef), items in groups.items():
        episodes, run = 0, [items[0]]
        for prev, cur in zip(items, items[1:]):
            if (cur["raised_ts"] - prev["raised_ts"]).total_seconds() <= CHATTER_WINDOW_SEC:
                run.append(cur)
            else:
                if len(run) >= CHATTER_MIN_COUNT:
                    episodes += 1
                    for x in run:
                        x["chatter"] = True
                run = [cur]
        if len(run) >= CHATTER_MIN_COUNT:
            episodes += 1
            for x in run:
                x["chatter"] = True
        fleeting = sum(1 for a in items if a["cleared_ts"] is not None
                       and (a["cleared_ts"] - a["raised_ts"]).total_seconds() <= FLEETING_MAX_SEC)
        chatter_alarms = sum(1 for a in items if a["chatter"])
        first = items[0]
        pairs.append({
            "machine_id": machine, "machine_name": first["machine_name"], "plant_id": first["plant_id"],
            "alarm_def_id": adef, "alarm_code": first["alarm_code"], "alarm_name": first["alarm_name"],
            "severity": first["severity"], "total_alarms": len(items), "chatter_episodes": episodes,
            "chatter_alarms": chatter_alarms, "fleeting_alarms": fleeting,
            "fleeting_pct": round(100 * fleeting / len(items), 1),
            "unacked_pct": round(100 * sum(1 for a in items if a["ack_status"] == "UNACKED") / len(items), 1),
            "is_nuisance": episodes >= NUISANCE_MIN_EPISODES,
        })
    pairs.sort(key=lambda p: (-p["chatter_episodes"], -p["total_alarms"]))
    return pairs


def nuisance_summary(ctx, limit: int = 50) -> dict:
    nuisance = [p for p in ctx.chatter_pairs if p["is_nuisance"]]
    alarms_in_nuisance = sum(p["total_alarms"] for p in nuisance)
    return {
        "rule": (f">= {CHATTER_MIN_COUNT} activations in {CHATTER_WINDOW_SEC}s = chatter episode; "
                 f">= {NUISANCE_MIN_EPISODES} episodes = nuisance alarm; clear <= {FLEETING_MAX_SEC}s = fleeting"),
        "nuisance_pairs": len(nuisance), "alarms_from_nuisance": alarms_in_nuisance,
        "share_of_alarms_pct": round(100 * alarms_in_nuisance / max(len(ctx.unique_alarms), 1), 1),
        "chatter_alarms_total": sum(1 for a in ctx.unique_alarms if a["chatter"]),
        "items": ctx.chatter_pairs[:limit],
    }