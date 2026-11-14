"""Incident rule engine + corrective action lifecycle tests."""
import random
from collections import Counter

from generator import events, incidents, master_data as md
from generator.config import DEFAULT_SEED, get_scale
from generator.rules import find_repeated_unsafe


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
    primary_zone = {b["machine_id"]: b["zone_id"] for b in bridge if b["is_primary"]}
    defs_by_type = {}
    for d in defs:
        if d["category"] != "SAFETY":
            defs_by_type.setdefault(d["machine_type"], []).append(d)
    problem = {m["machine_id"] for m in rng.sample(machines, cfg.problem_machines)}
    se, ie, scen = events.build_timelines(cfg, rng, machines, interlocks, defs, problem, staff)
    events.finalize_state_events(se, ie)
    sidx = events.StateIndex(se, "machine_id", "OFF")
    iidx = events.StateIndex(ie, "interlock_id", "ENGAGED")
    floods, eps = events.build_floods(cfg, rng, machines, defs_by_type, round(cfg.alarm_events * cfg.flood_share))
    chat, pairs = events.build_chatter(cfg, rng, machines, defs_by_type, cfg.bad_actor_pairs,
                                       round(cfg.alarm_events * cfg.chatter_share))
    remaining = cfg.alarm_events - cfg.n_replay_rows - len(scen) - len(floods) - len(chat)
    base = events.build_baseline(cfg, rng, machines, defs_by_type, sidx, remaining)
    alarms = scen + floods + chat + base
    events.finalize_alarms(cfg, rng, alarms, sidx, {s["shift_id"] for s in shifts})
    acks = events.build_acknowledgements(cfg, rng, alarms, shifts)
    cands = incidents.derive_incidents(cfg, rng, alarms, acks, defs, se, iidx, interlocks, primary_zone)
    taken = {c["trigger_alarm_id"] for c in cands}
    cands += incidents.manual_reports(cfg, rng, alarms, acks, shifts, primary_zone, taken, cfg.manual_reports)
    inc, links, actions = incidents.finalize_incidents(cfg, rng, cands, alarms, staff)
    return cfg, alarms, inc, links, actions, problem


DATA = build()


def test_incidents_derived_from_rules():
    cfg, alarms, inc, links, actions, problem = DATA
    rules = Counter(i["rule_code"] for i in inc)
    print(f"\nincidents={len(inc)} rules={dict(rules)} links={len(links)} actions={len(actions)}")
    print("incident status:", dict(Counter(i["status"] for i in inc)))
    print("action status  :", dict(Counter(a["status"] for a in actions)))
    assert rules["R1_BYPASS_CRITICAL"] > 0 and rules["R2_GUARD_TRIP_ESTOP"] > 0


def test_ids_sequential_and_formatted():
    _, _, inc, _, actions, _ = DATA
    assert inc[0]["incident_id"] == "INC-2026-000001"
    assert [i["incident_id"] for i in inc] == [f"INC-2026-{n:06d}" for n in range(1, len(inc) + 1)]
    assert all(a["action_id"].startswith(f"ACT-{a['incident_id']}-") for a in actions)


def test_every_rule_incident_traceable_to_trigger_alarm():
    _, alarms, inc, links, _, _ = DATA
    alarm_ids = {a["alarm_event_id"] for a in alarms}
    linked = {(l["incident_id"], l["link_role"]) for l in links}
    for i in inc:
        if i["rule_code"] != "MANUAL_REPORT":
            assert i["trigger_alarm_id"] in alarm_ids
            assert (i["incident_id"], "TRIGGER") in linked
        else:
            assert (i["incident_id"], "CONTEXT") in linked


def test_action_lifecycle_ordered_and_closed_only_after_verification():
    *_, actions, _ = DATA
    for a in actions:
        seq = [a["created_ts"], a["started_ts"], a["completed_ts"], a["verified_ts"], a["closed_ts"]]
        present = [t for t in seq if t is not None]
        assert present == sorted(present)
        if a["status"] == "CLOSED":
            assert a["verified_ts"] is not None and a["verified_by"] is not None


def test_problem_machines_show_repeated_unsafe_conditions():
    _, _, inc, _, _, problem = DATA
    rep = find_repeated_unsafe(inc)
    flagged = {r["machine_id"] for r in rep}
    print(f"repeated unsafe (machine, rule) pairs={len(rep)}; problem machines flagged="
          f"{len(flagged & problem)}/{len(problem)}")
    assert len(flagged & problem) >= len(problem) - 1