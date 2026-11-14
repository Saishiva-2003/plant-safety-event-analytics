"""
Documented business rules (single source of truth).

Used by the generator to CREATE data and by the backend services to ANALYSE it,
so outcomes/labels always follow the same documented rules (see docs/RULES.md).
"""

# ---------------------------------------------------------------------------
# 1. Alarm severity, weight and acknowledgement SLA
# ---------------------------------------------------------------------------
SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
SEVERITY_RANK = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4}
SEVERITY_WEIGHT = {"CRITICAL": 100, "HIGH": 50, "MEDIUM": 20, "LOW": 5}
ACK_SLA_SEC = {"CRITICAL": 60, "HIGH": 300, "MEDIUM": 900, "LOW": 1800}

ALARM_CATEGORIES = ["SAFETY", "PROCESS", "EQUIPMENT", "SYSTEM"]
ACK_METHODS = ["HMI", "MOBILE"]

# ---------------------------------------------------------------------------
# 2. Machine state machine (lifecycle). History is appended, never overwritten.
# ---------------------------------------------------------------------------
MACHINE_STATES = ["OFF", "STARTING", "RUNNING", "IDLE", "FAULTED", "E_STOP", "MAINTENANCE"]
MACHINE_TRANSITIONS = {
    "OFF": {"STARTING"},
    "STARTING": {"RUNNING", "FAULTED"},
    "RUNNING": {"IDLE", "OFF", "FAULTED", "E_STOP"},
    "IDLE": {"RUNNING", "OFF", "FAULTED", "E_STOP"},
    "FAULTED": {"MAINTENANCE"},
    "E_STOP": {"OFF"},
    "MAINTENANCE": {"OFF"},
}

# ---------------------------------------------------------------------------
# 3. Interlocks
# ---------------------------------------------------------------------------
INTERLOCK_TYPES = ["GUARD_DOOR", "LIGHT_CURTAIN", "E_STOP", "PRESSURE"]
INTERLOCK_STATES = ["ENGAGED", "TRIPPED", "BYPASSED"]
INTERLOCK_TRANSITIONS = {
    "ENGAGED": {"TRIPPED", "BYPASSED"},
    "TRIPPED": {"ENGAGED"},        # reset
    "BYPASSED": {"ENGAGED"},       # bypass removed
}
# A tripped interlock must stop the machine -> machine can never be RUNNING while TRIPPED
STATES_IMPOSSIBLE_WHEN_TRIPPED = {"RUNNING"}

# ---------------------------------------------------------------------------
# 4. Shifts (plant local time)
# ---------------------------------------------------------------------------
SHIFTS = {"A": (6, 14), "B": (14, 22), "C": (22, 6)}   # C crosses midnight

# ---------------------------------------------------------------------------
# 5. Alarm-management rules (ISA-18.2 inspired)
# ---------------------------------------------------------------------------
FLOOD_WINDOW_SEC = 600          # 10 minutes
FLOOD_THRESHOLD = 10            # > 10 alarms in 10 min per plant = flood
CHATTER_WINDOW_SEC = 60
CHATTER_MIN_COUNT = 3           # >= 3 activations of same alarm on same machine in 60 s
FLEETING_MAX_SEC = 5            # alarm that clears itself within 5 s = fleeting
NUISANCE_MIN_EPISODES = 5       # pair with >= 5 chatter episodes in window = nuisance alarm

# ---------------------------------------------------------------------------
# 6. Incident rules  (incidents are DERIVED from data with these rules)
# ---------------------------------------------------------------------------
INCIDENT_RULES = {
    "R1_BYPASS_CRITICAL": "CRITICAL safety alarm raised while an interlock is BYPASSED and machine is RUNNING",
    "R2_GUARD_TRIP_ESTOP": "Guard door / light curtain alarm while RUNNING followed by E_STOP within 60 s",
    "R3_CRITICAL_UNACKED": "CRITICAL alarm not acknowledged within 300 s",
    "MANUAL_REPORT": "Near-miss reported by an operator (linked to context alarms)",
}
RULE_SEVERITY = {
    "R1_BYPASS_CRITICAL": "CRITICAL",
    "R2_GUARD_TRIP_ESTOP": "HIGH",
    "R3_CRITICAL_UNACKED": "CRITICAL",
}
R2_ESTOP_WINDOW_SEC = 60
R3_UNACKED_SEC = 300
INCIDENT_CONTEXT_WINDOW_SEC = 600   # alarms 10 min before trigger are linked as CONTEXT

# Repeated unsafe condition: same machine + same rule >= 3 times in rolling 7 days
REPEAT_WINDOW_DAYS = 7
REPEAT_MIN_COUNT = 3

# ---------------------------------------------------------------------------
# 7. Incident & corrective-action lifecycles
# ---------------------------------------------------------------------------
INCIDENT_STATUSES = ["OPEN", "INVESTIGATING", "ACTION_PENDING", "CLOSED"]
ACTION_STATUSES = ["OPEN", "IN_PROGRESS", "PENDING_VERIFICATION", "VERIFIED", "CLOSED"]
ACTION_TYPES = ["ENGINEERING", "ADMINISTRATIVE", "TRAINING", "MAINTENANCE"]
# An action may only be CLOSED after it has been VERIFIED (verified_ts + verified_by set)

# ---------------------------------------------------------------------------
# 8. Priority score used to rank alarms (severe first)
# ---------------------------------------------------------------------------
INTERLOCK_FACTOR = {"BYPASSED": 2.0, "TRIPPED": 1.5, "ENGAGED": 1.0, None: 1.0}


def priority_score(severity: str, hazard_level: int, interlock_state=None, repeat_count: int = 0) -> float:
    """severity weight x zone hazard x interlock factor + repeat bonus."""
    base = SEVERITY_WEIGHT[severity] * max(1, hazard_level) * INTERLOCK_FACTOR.get(interlock_state, 1.0)
    return round(base + 2 * repeat_count, 2)


def is_ack_delayed(severity: str, response_sec) -> bool:
    return response_sec is not None and response_sec > ACK_SLA_SEC[severity]


def is_valid_machine_transition(from_state, to_state) -> bool:
    if from_state is None:
        return to_state in MACHINE_STATES
    return to_state in MACHINE_TRANSITIONS.get(from_state, set())


def is_valid_interlock_transition(from_state, to_state) -> bool:
    return to_state in INTERLOCK_TRANSITIONS.get(from_state, set())


def find_repeated_unsafe(incidents: list[dict]) -> list[dict]:
    """
    Repeated unsafe condition = same machine + same rule_code occurring
    >= REPEAT_MIN_COUNT times inside a rolling REPEAT_WINDOW_DAYS window.
    incidents: dicts with machine_id, rule_code, opened_ts (datetime), incident_id
    Returns one row per (machine, rule) with the worst (max) window count.
    """
    from datetime import timedelta

    window = timedelta(days=REPEAT_WINDOW_DAYS)
    groups: dict = {}
    for inc in incidents:
        if inc["rule_code"] in (None, "MANUAL_REPORT"):
            continue
        groups.setdefault((inc["machine_id"], inc["rule_code"]), []).append(inc)

    results = []
    for (machine, rule), items in sorted(groups.items()):
        items = sorted(items, key=lambda x: x["opened_ts"])
        best, best_i, j = 0, 0, 0
        for i in range(len(items)):
            while items[i]["opened_ts"] - items[j]["opened_ts"] > window:
                j += 1
            if i - j + 1 > best:
                best, best_i = i - j + 1, i
        if best >= REPEAT_MIN_COUNT:
            first = best_i - best + 1
            results.append({
                "machine_id": machine, "rule_code": rule, "max_count_in_window": best,
                "total_count": len(items),
                "window_start": items[first]["opened_ts"], "window_end": items[best_i]["opened_ts"],
                "incident_ids": [x["incident_id"] for x in items[first: best_i + 1]],
            })
    return results