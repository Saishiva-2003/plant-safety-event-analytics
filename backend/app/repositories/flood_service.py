"""Alarm-flood detection: > FLOOD_THRESHOLD alarms within FLOOD_WINDOW_SEC per plant (ISA-18.2 style)."""
from collections import Counter
from datetime import timedelta

from generator.rules import FLOOD_THRESHOLD, FLOOD_WINDOW_SEC

WINDOW = timedelta(seconds=FLOOD_WINDOW_SEC)


def detect_floods(alarms: list[dict]) -> list[dict]:
    """Marks a['flood_id'] and returns flood episodes.
    Replay duplicates and chattering alarms (already handled as nuisance) are excluded first,
    so a single chattering sensor is not mistaken for a plant-wide flood."""
    by_plant = {}
    for a in alarms:
        a["flood_id"] = None
        if not a.get("is_replay") and not a.get("chatter"):
            by_plant.setdefault(a["plant_id"], []).append(a)
    episodes = []
    for plant in sorted(by_plant):
        items = by_plant[plant]                      # already time-ordered
        in_flood = [False] * len(items)
        j = 0
        for i in range(len(items)):
            while items[i]["raised_ts"] - items[j]["raised_ts"] > WINDOW:
                j += 1
            if i - j + 1 > FLOOD_THRESHOLD:
                for k in range(j, i + 1):
                    in_flood[k] = True
        n, cur = 0, None
        for k, a in enumerate(items):
            if not in_flood[k]:
                cur = None
                continue
            if cur is None or a["raised_ts"] - cur["end_ts"] > WINDOW:
                n += 1
                cur = {"flood_id": f"F-{plant}-{n:03d}", "plant_id": plant, "start_ts": a["raised_ts"],
                       "end_ts": a["raised_ts"], "alarms": []}
                episodes.append(cur)
            cur["end_ts"] = a["raised_ts"]
            cur["alarms"].append(a)
            a["flood_id"] = cur["flood_id"]
    out = []
    for e in episodes:
        al = e.pop("alarms")
        machines = Counter(a["machine_id"] for a in al)
        sev = Counter(a["severity"] for a in al)
        dur = max((e["end_ts"] - e["start_ts"]).total_seconds(), 1)
        e.update({
            "alarm_count": len(al), "duration_sec": round(dur, 1),
            "peak_rate_per_10min": round(len(al) * 600 / max(dur, 600), 1),
            "machines_involved": len(machines), "top_machine_id": machines.most_common(1)[0][0],
            "severity_mix": dict(sev),
            "unacked": sum(1 for a in al if a["ack_status"] == "UNACKED"),
            "delayed": sum(1 for a in al if a["ack_status"] == "DELAYED"),
        })
        out.append(e)
    return out


def flood_summary(ctx) -> dict:
    eps = ctx.floods
    flood_alarms = sum(e["alarm_count"] for e in eps)
    per_plant = Counter(e["plant_id"] for e in eps)
    return {
        "rule": f"> {FLOOD_THRESHOLD} alarms in {FLOOD_WINDOW_SEC // 60} min per plant",
        "episodes": len(eps), "flood_alarms": flood_alarms,
        "share_of_alarms_pct": round(100 * flood_alarms / max(len(ctx.unique_alarms), 1), 1),
        "per_plant": dict(sorted(per_plant.items())),
        "largest": max((e["alarm_count"] for e in eps), default=0),
        "items": sorted(eps, key=lambda e: e["start_ts"]),
    }