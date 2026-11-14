"""Event generation tests: timelines, alarms, acknowledgements (full scale, fixed seed)."""
import random
from collections import Counter

from generator import events, master_data as md
from generator.config import DEFAULT_SEED, get_scale
from generator.rules import (
    is_valid_interlock_transition, is_valid_machine_transition,
)


def build():
    cfg = get_scale("full")
    rng = random.Random(DEFAULT_SEED)
    plants = md.build_plants(cfg)
    zones = md.build_zones(cfg, plants)
    machines, bridge = md.build_machines(cfg, rng, plants, zones)
    interlocks = md.build_interlocks(machines, bridge)
    defs = md.build_alarm_definitions(cfg)
    staff = md.build_staff(cfg, plants)
    shifts = md.build_shifts(cfg, rng, plants, staff)
    defs_by_type = {}
    for d in defs:
        if d["category"] != "SAFETY":
            defs_by_type.setdefault(d["machine_type"], []).append(d)
    problem = {m["machine_id"] for m in rng.sample(machines, cfg.problem_machines)}
    se, ie, scen = events.build_timelines(cfg, rng, machines, interlocks, defs, problem, staff)
    events.finalize_state_events(se, ie)
    sidx = events.StateIndex(se, "machine_id", "OFF")
    floods, eps = events.build_floods(cfg, rng, machines, defs_by_type, round(cfg.alarm_events * cfg.flood_share))
    chat, pairs = events.build_chatter(cfg, rng, machines, defs_by_type, cfg.bad_actor_pairs,
                                       round(cfg.alarm_events * cfg.chatter_share))
    remaining = cfg.alarm_events - cfg.n_replay_rows - len(scen) - len(floods) - len(chat)
    base = events.build_baseline(cfg, rng, machines, defs_by_type, sidx, remaining)
    alarms = scen + floods + chat + base
    events.finalize_alarms(cfg, rng, alarms, sidx, {s["shift_id"] for s in shifts})
    acks = events.build_acknowledgements(cfg, rng, alarms, shifts)
    return cfg, se, ie, alarms, acks, eps


DATA = build()


def test_volumes():
    cfg, se, ie, alarms, acks, eps = DATA
    print(f"\nstate_events={len(se)} interlock_events={len(ie)} alarms={len(alarms)} "
          f"acks={len(acks)} floods={len(eps)}")
    print("alarm sources:", dict(Counter(a["_source"] for a in alarms)))
    assert len(alarms) == cfg.alarm_events - cfg.n_replay_rows      # 49,500 (+500 replays later = 50,000)


def test_machine_transitions_follow_state_machine():
    _, se, *_ = DATA
    last, bad = {}, 0
    for e in sorted(se, key=lambda x: (x["machine_id"], x["event_ts"])):
        prev = last.get(e["machine_id"], "OFF")
        if e["from_state"] != prev or not is_valid_machine_transition(e["from_state"], e["to_state"]):
            bad += 1
        last[e["machine_id"]] = e["to_state"]
    assert bad == 0


def test_interlock_transitions_valid_and_never_tripped_while_running():
    _, _, ie, *_ = DATA
    last, bad = {}, 0
    for e in sorted(ie, key=lambda x: (x["interlock_id"], x["event_ts"])):
        prev = last.get(e["interlock_id"], "ENGAGED")
        if e["from_state"] != prev or not is_valid_interlock_transition(e["from_state"], e["to_state"]):
            bad += 1
        last[e["interlock_id"]] = e["to_state"]
    assert bad == 0
    assert not any(e["to_state"] == "TRIPPED" and e["machine_state_snapshot"] == "RUNNING" for e in ie)


def test_alarm_ids_unique_and_inside_window():
    cfg, _, _, alarms, _, _ = DATA
    ids = [a["alarm_event_id"] for a in alarms]
    assert len(ids) == len(set(ids))
    assert ids[0].startswith("ALM-P0") and len(ids[0].split("-")[-1]) == 6
    assert all(cfg.start_ts <= a["raised_ts"] < cfg.end_ts for a in alarms)
    assert all(a["cleared_ts"] is None or a["cleared_ts"] >= a["raised_ts"] for a in alarms)


def test_acks_after_alarm_and_response_derived():
    _, _, _, alarms, acks, _ = DATA
    by_id = {a["alarm_event_id"]: a for a in alarms}
    for k in acks:
        a = by_id[k["alarm_event_id"]]
        assert k["ack_ts"] > a["raised_ts"]                       # baseline: no ack before alarm
        assert abs((k["ack_ts"] - a["raised_ts"]).total_seconds() - k["response_sec"]) < 0.001
        assert k["ack_id"] == f"ACK-{k['alarm_event_id']}-01"


def test_floods_exceed_threshold():
    *_, alarms, _, eps = DATA
    assert all(e["alarm_count"] > 10 for e in eps)