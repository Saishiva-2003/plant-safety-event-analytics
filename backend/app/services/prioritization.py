"""Alarm prioritisation + acknowledgement status (documented in generator/rules.py)."""
import bisect
from datetime import timedelta

from generator.rules import ACK_SLA_SEC, SEVERITY_RANK, priority_score

INTERLOCK_RANK = {"BYPASSED": 3, "TRIPPED": 2, "ENGAGED": 1}
REPEAT_WINDOW = timedelta(hours=24)


def worst_interlock_state(ilk_index, interlock_ids: list[str], ts) -> str:
    """Most dangerous interlock state on the machine at time ts (BYPASSED > TRIPPED > ENGAGED)."""
    states = [ilk_index.state_at(i, ts) for i in interlock_ids] or ["ENGAGED"]
    return max(states, key=lambda s: INTERLOCK_RANK.get(s, 0))


def ack_status(alarm: dict) -> str:
    r = alarm["response_sec"]
    if r is None:
        return "UNACKED"
    if r < 0:
        return "INVALID"                          # acknowledgement before alarm (data-quality issue)
    return "DELAYED" if r > ACK_SLA_SEC[alarm["severity"]] else "ON_TIME"


def enrich(alarms: list[dict], ilk_index, interlocks_by_machine: dict) -> None:
    """Adds priority_score, interlock_state_at_raise, repeat_24h, ack_status to each alarm (in place)."""
    times = {}
    for a in alarms:
        if not a.get("is_replay"):
            times.setdefault((a["machine_id"], a["alarm_def_id"]), []).append(a["raised_ts"])
    for a in alarms:
        state = worst_interlock_state(ilk_index, interlocks_by_machine.get(a["machine_id"], []), a["raised_ts"])
        t = times.get((a["machine_id"], a["alarm_def_id"]), [])
        lo = bisect.bisect_left(t, a["raised_ts"] - REPEAT_WINDOW)
        hi = bisect.bisect_left(t, a["raised_ts"])
        a["interlock_state_at_raise"] = state
        a["repeat_24h"] = hi - lo
        a["priority_score"] = priority_score(a["severity"], a["hazard_level"], state, min(hi - lo, 20))
        a["severity_rank"] = SEVERITY_RANK[a["severity"]]
        a["ack_status"] = ack_status(a)