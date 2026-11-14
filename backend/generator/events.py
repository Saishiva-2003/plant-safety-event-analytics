"""
Step 2b - Dependent event data (uses only valid parent IDs):
    machine_state_event, interlock_state_event, alarm_event, acknowledgement

Order of generation
    1. Machine + interlock timelines (state machine walk) incl. genuine safety scenarios
    2. Alarm floods          (plant-wide bursts)
    3. Chattering alarms     (bad-actor machine/definition pairs -> nuisance)
    4. Baseline alarms       (fill to target volume)
    5. Deterministic alarm IDs + shift links
    6. Acknowledgements      (response time derived from timestamps)
"""
import bisect
import math

from generator import id_factory as ids
from generator.config import add_seconds
from generator.master_data import shift_key

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
H = 3600.0
M = 60.0


def _lognormal(rng, median: float, sigma: float) -> float:
    return median * math.exp(rng.gauss(0, sigma))


class StateIndex:
    """Fast 'what was the state at time t' lookup for machines and interlocks."""

    def __init__(self, events: list[dict], key: str, default: str):
        self.default = default
        self._ts, self._st = {}, {}
        for e in sorted(events, key=lambda x: x["event_ts"]):
            self._ts.setdefault(e[key], []).append(e["event_ts"])
            self._st.setdefault(e[key], []).append(e["to_state"])

    def state_at(self, obj_id: str, ts):
        times = self._ts.get(obj_id)
        if not times:
            return self.default
        i = bisect.bisect_right(times, ts) - 1
        return self._st[obj_id][i] if i >= 0 else self.default


# ---------------------------------------------------------------------------
# 1. Machine + interlock timelines
# ---------------------------------------------------------------------------
def build_timelines(cfg, rng, machines, interlocks, defs, problem_ids, staff):
    """Walk every machine through the documented state machine for the whole window."""
    end = cfg.end_ts
    ilks_by_machine = {}
    for i in interlocks:
        ilks_by_machine.setdefault(i["machine_id"], []).append(i)
    def_lookup = {(d["machine_type"], d["base_code"]): d for d in defs}
    engineers = {}
    for s in staff:
        if s["role"] == "ENGINEER":
            engineers.setdefault(s["plant_id"], []).append(s["staff_id"])

    state_events, ilk_events, alarms = [], [], []

    for m in machines:
        mid, mtype, plant = m["machine_id"], m["machine_type"], m["plant_id"]
        problem = mid in problem_ids
        ilks = {i["interlock_type"]: i["interlock_id"] for i in ilks_by_machine[mid]}
        ilk_state = {iid: "ENGAGED" for iid in ilks.values()}
        cur = {"state": "OFF"}

        def go(ts, to, reason):
            if ts >= end:
                return False
            state_events.append({"machine_id": mid, "event_ts": ts, "from_state": cur["state"],
                                 "to_state": to, "reason": reason})
            cur["state"] = to
            return True

        def ilk(ts, iid, to, snapshot, reason, actor):
            if ts >= end:
                return
            ilk_events.append({"interlock_id": iid, "machine_id": mid, "event_ts": ts,
                               "from_state": ilk_state[iid], "to_state": to,
                               "machine_state_snapshot": snapshot, "reason": reason, "actor": actor})
            ilk_state[iid] = to

        def alarm(base_code, ts, iid=None, source="SCENARIO"):
            d = def_lookup.get((mtype, base_code))
            if d is None or ts >= end:
                return None
            a = {"machine_id": mid, "plant_id": plant, "alarm_def_id": d["alarm_def_id"],
                 "severity": d["severity"], "category": d["category"], "raised_ts": ts,
                 "cleared_ts": None, "interlock_id": iid, "_source": source}
            alarms.append(a)
            return a

        def clear(a, ts):
            if a is not None and ts < end:
                a["cleared_ts"] = ts

        t = add_seconds(cfg.start_ts, rng.uniform(0, 30 * M))
        go(t, "STARTING", "Initial start-up")
        t = add_seconds(t, rng.uniform(2 * M, 8 * M))
        go(t, "RUNNING", "Start-up complete")
        pending_bypass = None          # interlock left BYPASSED after maintenance (unsafe)
        tripped, open_alarm = None, None

        while t < end:
            st = cur["state"]
            if st == "RUNNING":
                dur = min(max(rng.expovariate(1 / (4 * H)), 20 * M), 12 * H)
                if pending_bypass:
                    reset_delay = rng.uniform(20 * M, 180 * M)
                    a = alarm("BYPASS-RUN", add_seconds(t, rng.uniform(1 * M, 10 * M)), pending_bypass)
                    ilk(add_seconds(t, reset_delay), pending_bypass, "ENGAGED", "RUNNING",
                        "Bypass removed after safety alarm", rng.choice(engineers[plant]))
                    clear(a, add_seconds(t, reset_delay))
                    pending_bypass = None
                    dur = max(dur, reset_delay + 10 * M)
                    nxt = "IDLE"
                else:
                    r = rng.random()
                    p_trip = 0.07 if problem else 0.02
                    if r < p_trip:
                        nxt = "GUARD_TRIP"
                    elif r < p_trip + 0.01:
                        nxt = "ESTOP_BUTTON"
                    elif r < p_trip + 0.09:
                        nxt = "FAULT"
                    elif r < p_trip + 0.17:
                        nxt = "OFF"
                    else:
                        nxt = "IDLE"
                t = add_seconds(t, dur)
                if t >= end:
                    break
                if nxt == "GUARD_TRIP":
                    options = [x for x in ("GUARD_DOOR", "LIGHT_CURTAIN") if x in ilks]
                    itype = rng.choice(options)
                    code = "GRD-OPEN" if itype == "GUARD_DOOR" else "LC-BREAK"
                    open_alarm = alarm(code, add_seconds(t, -rng.uniform(0.5, 3.0)), ilks[itype])
                    ilk(t, ilks[itype], "TRIPPED", "E_STOP", "Protective device opened while running", "SYSTEM")
                    go(t, "E_STOP", f"{itype} interlock trip")
                    tripped = ilks[itype]
                elif nxt == "ESTOP_BUTTON":
                    open_alarm = alarm("ESTOP-PB", t, ilks["E_STOP"])
                    ilk(t, ilks["E_STOP"], "TRIPPED", "E_STOP", "Emergency stop pressed", "OPERATOR")
                    go(t, "E_STOP", "Emergency stop push-button")
                    tripped = ilks["E_STOP"]
                elif nxt == "FAULT":
                    if "PRESSURE" in ilks and rng.random() < 0.3:
                        open_alarm = alarm("PRS-OVER", t, ilks["PRESSURE"])
                        ilk(t, ilks["PRESSURE"], "TRIPPED", "FAULTED", "Overpressure relief", "SYSTEM")
                        tripped = ilks["PRESSURE"]
                    else:
                        open_alarm = alarm(rng.choice(["MOTOR-OVL", "DRV-FLT"]),
                                           add_seconds(t, -rng.uniform(1, 20)), source="FAULT")
                    go(t, "FAULTED", "Equipment fault")
                else:
                    go(t, nxt, "Production schedule")

            elif st == "IDLE":
                t = add_seconds(t, rng.uniform(10 * M, 90 * M))
                r = rng.random()
                go(t, "RUNNING" if r < 0.88 else ("OFF" if r < 0.98 else "FAULTED"), "Production schedule")

            elif st == "OFF":
                t = add_seconds(t, rng.uniform(20 * M, 240 * M))
                if not go(t, "STARTING", "Scheduled start"):
                    break
                t = add_seconds(t, rng.uniform(2 * M, 8 * M))
                if rng.random() < 0.04:
                    go(t, "FAULTED", "Start-up failure")
                else:
                    go(t, "RUNNING", "Start-up complete")

            elif st == "E_STOP":
                t = add_seconds(t, rng.uniform(3 * M, 25 * M))
                if tripped:
                    ilk(t, tripped, "ENGAGED", "E_STOP", "Reset after inspection", "OPERATOR")
                    tripped = None
                clear(open_alarm, t)
                open_alarm = None
                go(add_seconds(t, 1), "OFF", "E-stop reset")
                t = add_seconds(t, 1)

            elif st == "FAULTED":
                t = add_seconds(t, rng.uniform(5 * M, 30 * M))
                if not go(t, "MAINTENANCE", "Maintenance started"):
                    break
                m_start = t
                m_end = add_seconds(t, rng.uniform(30 * M, 240 * M))
                if tripped:
                    ilk(add_seconds(m_start, rng.uniform(1 * M, 5 * M)), tripped, "ENGAGED",
                        "MAINTENANCE", "Reset by maintenance", rng.choice(engineers[plant]))
                    tripped = None
                gd = ilks["GUARD_DOOR"]
                if pending_bypass:         # still bypassed from an earlier job -> remove it now
                    ilk(add_seconds(m_end, -rng.uniform(1 * M, 4 * M)), pending_bypass, "ENGAGED",
                        "MAINTENANCE", "Bypass removed", rng.choice(engineers[plant]))
                    pending_bypass = None
                elif rng.random() < 0.7:   # maintenance needs guard access -> bypass
                    ilk(add_seconds(m_start, rng.uniform(5 * M, 15 * M)), gd, "BYPASSED", "MAINTENANCE",
                        "Maintenance access bypass", rng.choice(engineers[plant]))
                    unsafe = rng.random() < (0.35 if problem else 0.05)
                    if unsafe:
                        pending_bypass = gd    # bypass NOT removed before restart
                    else:
                        ilk(add_seconds(m_end, -rng.uniform(1 * M, 4 * M)), gd, "ENGAGED", "MAINTENANCE",
                            "Bypass removed", rng.choice(engineers[plant]))
                clear(open_alarm, m_end)
                open_alarm = None
                t = m_end
                go(t, "OFF", "Maintenance complete")
            else:   # STARTING handled inside OFF branch; safety net
                t = add_seconds(t, 60)
                go(t, "RUNNING", "Start-up complete")

    return state_events, ilk_events, alarms


# ---------------------------------------------------------------------------
# 2. Alarm floods
# ---------------------------------------------------------------------------
def build_floods(cfg, rng, machines, defs_by_type, budget):
    """Plant-wide bursts: 20-400 alarms within 4-10 minutes, centred on a trigger machine."""
    by_plant = {}
    for m in machines:
        by_plant.setdefault(m["plant_id"], []).append(m)
    plants = sorted(by_plant)
    alarms, episodes = [], []
    total_sec = (cfg.end_ts - cfg.start_ts).total_seconds()
    n = 0
    while len(alarms) < budget:
        n += 1
        plant = rng.choice(plants)
        size = int(min(400, max(20, _lognormal(rng, 160, 0.6))))
        size = min(size, budget - len(alarms))
        start = add_seconds(cfg.start_ts, rng.uniform(1 * H, total_sec - 1 * H))
        duration = rng.uniform(4 * M, 10 * M)
        trigger = rng.choice(by_plant[plant])
        flood_id = f"FLOOD-{plant}-{n:03d}"
        times = sorted(rng.uniform(0, duration) for _ in range(size))
        for off in times:
            mach = trigger if rng.random() < 0.4 else rng.choice(by_plant[plant])
            d = rng.choice(defs_by_type[mach["machine_type"]])
            raised = add_seconds(start, off)
            alarms.append({"machine_id": mach["machine_id"], "plant_id": plant,
                           "alarm_def_id": d["alarm_def_id"], "severity": d["severity"],
                           "category": d["category"], "raised_ts": raised,
                           "cleared_ts": add_seconds(raised, _lognormal(rng, 90, 0.8)),
                           "interlock_id": None, "_source": "FLOOD", "_flood_id": flood_id})
        episodes.append({"flood_id": flood_id, "plant_id": plant, "trigger_machine_id": trigger["machine_id"],
                         "start_ts": start, "end_ts": add_seconds(start, duration), "alarm_count": size})
    return alarms, episodes


# ---------------------------------------------------------------------------
# 3. Chattering / nuisance alarms
# ---------------------------------------------------------------------------
def build_chatter(cfg, rng, machines, defs_by_type, n_pairs, budget):
    """Bad-actor (machine, definition) pairs fire 3-12 times within ~1 minute, clearing in < 5 s."""
    pairs = []
    pool = list(machines)
    while len(pairs) < n_pairs:
        m = rng.choice(pool)
        low_med = [d for d in defs_by_type[m["machine_type"]] if d["severity"] in ("LOW", "MEDIUM")]
        d = rng.choice(low_med)
        if (m["machine_id"], d["alarm_def_id"]) not in [(p[0]["machine_id"], p[1]["alarm_def_id"]) for p in pairs]:
            pairs.append((m, d))
    alarms = []
    total_sec = (cfg.end_ts - cfg.start_ts).total_seconds()
    episode_count = {}
    while len(alarms) < budget:
        m, d = rng.choice(pairs)
        t = add_seconds(cfg.start_ts, rng.uniform(0, total_sec - 600))
        repeats = min(rng.randint(3, 12), budget - len(alarms))
        key = (m["machine_id"], d["alarm_def_id"])
        episode_count[key] = episode_count.get(key, 0) + 1
        for _ in range(repeats):
            alarms.append({"machine_id": m["machine_id"], "plant_id": m["plant_id"],
                           "alarm_def_id": d["alarm_def_id"], "severity": d["severity"],
                           "category": d["category"], "raised_ts": t,
                           "cleared_ts": add_seconds(t, rng.uniform(0.3, 4.0)),
                           "interlock_id": None, "_source": "CHATTER"})
            t = add_seconds(t, rng.uniform(2, 15))
    pair_rows = [{"machine_id": m["machine_id"], "alarm_def_id": d["alarm_def_id"],
                  "episodes": episode_count.get((m["machine_id"], d["alarm_def_id"]), 0)} for m, d in pairs]
    return alarms, pair_rows


# ---------------------------------------------------------------------------
# 4. Baseline alarms
# ---------------------------------------------------------------------------
def build_baseline(cfg, rng, machines, defs_by_type, state_index, count):
    sev_weight = {"LOW": 4, "MEDIUM": 4, "HIGH": 1, "CRITICAL": 0}
    alarms = []
    total_sec = (cfg.end_ts - cfg.start_ts).total_seconds()
    weights_cache = {t: [sev_weight[d["severity"]] for d in ds] for t, ds in defs_by_type.items()}
    while len(alarms) < count:
        m = rng.choice(machines)
        ts = add_seconds(cfg.start_ts, rng.uniform(0, total_sec - 1))
        hour_factor = 1.0 if 6 <= ts.hour < 22 else 0.7          # quieter at night
        state = state_index.state_at(m["machine_id"], ts)
        if rng.random() > hour_factor or (state == "OFF" and rng.random() < 0.7):
            continue
        d = rng.choices(defs_by_type[m["machine_type"]], weights=weights_cache[m["machine_type"]])[0]
        alarms.append({"machine_id": m["machine_id"], "plant_id": m["plant_id"],
                       "alarm_def_id": d["alarm_def_id"], "severity": d["severity"],
                       "category": d["category"], "raised_ts": ts,
                       "cleared_ts": add_seconds(ts, _lognormal(rng, 120, 1.0)),
                       "interlock_id": None, "_source": "BASELINE"})
    return alarms


# ---------------------------------------------------------------------------
# 5. IDs, shift links, machine-state snapshot, received timestamp
# ---------------------------------------------------------------------------
def finalize_alarms(cfg, rng, alarms, state_index, shift_ids: set):
    """Sort per machine by time -> ALM-<machine>-000001; source_seq = PLC sequence number."""
    alarms.sort(key=lambda a: (a["machine_id"], a["raised_ts"], a["alarm_def_id"]))
    counter = {}
    for a in alarms:
        n = counter.get(a["machine_id"], 0) + 1
        counter[a["machine_id"]] = n
        a["alarm_event_id"] = ids.alarm_event_id(a["machine_id"], n)
        a["source_seq"] = n
        a["received_ts"] = add_seconds(a["raised_ts"], rng.uniform(0.05, 1.5))
        a["machine_state"] = state_index.state_at(a["machine_id"], a["raised_ts"])
        if a["cleared_ts"] is not None and a["cleared_ts"] >= cfg.end_ts:
            a["cleared_ts"] = None
        day, code = shift_key(a["raised_ts"])
        sid = ids.shift_id(a["plant_id"], day, code)
        assert sid in shift_ids, sid
        a["shift_id"] = sid
    alarms.sort(key=lambda a: (a["raised_ts"], a["alarm_event_id"]))
    return alarms


def finalize_state_events(state_events, ilk_events):
    state_events.sort(key=lambda e: (e["machine_id"], e["event_ts"]))
    c = {}
    for e in state_events:
        n = c.get(e["machine_id"], 0) + 1
        c[e["machine_id"]] = n
        e["state_event_id"] = ids.machine_state_event_id(e["machine_id"], n)
    ilk_events.sort(key=lambda e: (e["interlock_id"], e["event_ts"]))
    c = {}
    for e in ilk_events:
        n = c.get(e["interlock_id"], 0) + 1
        c[e["interlock_id"]] = n
        e["interlock_event_id"] = ids.interlock_event_id(e["interlock_id"], n)


# ---------------------------------------------------------------------------
# 6. Acknowledgements
# ---------------------------------------------------------------------------
ACK_PROB = {"CRITICAL": 0.95, "HIGH": 0.96, "MEDIUM": 0.9, "LOW": 0.7}
ACK_MEDIAN_SEC = {"CRITICAL": 25, "HIGH": 90, "MEDIUM": 300, "LOW": 600}


def build_acknowledgements(cfg, rng, alarms, shifts):
    shift_by_id = {s["shift_id"]: s for s in shifts}
    acks = []
    for a in alarms:
        sev, src = a["severity"], a["_source"]
        p = ACK_PROB[sev] * (0.35 if src == "CHATTER" else 0.75 if src == "FLOOD" else 1.0)
        if rng.random() > p:
            continue
        median = ACK_MEDIAN_SEC[sev] * (4.0 if src == "FLOOD" else 1.0)
        if a["shift_id"].endswith("-C"):
            median *= 1.3                                   # night shift slower
        resp = max(1.0, _lognormal(rng, median, 0.9))
        ack_ts = add_seconds(a["raised_ts"], resp)
        if ack_ts >= cfg.end_ts:
            continue
        day, code = shift_key(ack_ts)
        sid = ids.shift_id(a["plant_id"], day, code)
        acks.append({
            "ack_id": ids.ack_id(a["alarm_event_id"]), "alarm_event_id": a["alarm_event_id"],
            "shift_id": sid, "operator_id": shift_by_id[sid]["operator_id"], "ack_ts": ack_ts,
            "response_sec": round((ack_ts - a["raised_ts"]).total_seconds(), 3),
            "ack_method": "HMI" if rng.random() < 0.85 else "MOBILE",
        })
    return acks