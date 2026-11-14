"""
Generator entry point.

    cd backend
    python -m generator.run --scale full    --seed 20261022
    python -m generator.run --scale starter --out tmp_repro/run1

Pipeline: master data -> timelines -> alarms -> acks -> incidents -> actions
          -> labelled edge cases -> ground truth -> export + manifest
"""
import argparse
import random
import time
from collections import Counter

from generator import anomalies, events, incidents, master_data
from generator.config import DEFAULT_OUTPUT_DIR, DEFAULT_SEED, GENERATOR_VERSION, fmt_ts, get_scale
from generator.exporter import export_all
from generator.rules import find_repeated_unsafe


def generate(scale: str = "full", seed: int = DEFAULT_SEED, out_dir=DEFAULT_OUTPUT_DIR, verbose: bool = True):
    cfg = get_scale(scale)
    rng = random.Random(seed)
    log = print if verbose else (lambda *a, **k: None)

    # ---- 1. master data -------------------------------------------------
    plants = master_data.build_plants(cfg)
    zones = master_data.build_zones(cfg, plants)
    machines, machine_zone = master_data.build_machines(cfg, rng, plants, zones)
    interlocks = master_data.build_interlocks(machines, machine_zone)
    defs = master_data.build_alarm_definitions(cfg)
    staff = master_data.build_staff(cfg, plants)
    shifts = master_data.build_shifts(cfg, rng, plants, staff)
    primary_zone = {b["machine_id"]: b["zone_id"] for b in machine_zone if b["is_primary"]}
    defs_by_type = {}
    for d in defs:
        if d["category"] != "SAFETY":
            defs_by_type.setdefault(d["machine_type"], []).append(d)
    log(f"[1] master: {len(plants)} plants, {len(machines)} machines, {len(zones)} zones, "
        f"{len(interlocks)} interlocks, {len(defs)} alarm defs, {len(shifts)} shifts")

    # ---- 2. timelines + genuine safety scenarios ---------------------------
    problem_ids = {m["machine_id"] for m in rng.sample(machines, cfg.problem_machines)}
    state_events, ilk_events, scenario_alarms = events.build_timelines(
        cfg, rng, machines, interlocks, defs, problem_ids, staff)
    events.finalize_state_events(state_events, ilk_events)
    state_index = events.StateIndex(state_events, "machine_id", "OFF")
    ilk_index = events.StateIndex(ilk_events, "interlock_id", "ENGAGED")
    log(f"[2] timelines: {len(state_events)} machine state events, {len(ilk_events)} interlock events, "
        f"{len(scenario_alarms)} scenario alarms")

    # ---- 3. alarms (floods, chatter, baseline) -----------------------------
    base_total = cfg.alarm_events - cfg.n_replay_rows
    flood_alarms, flood_eps = events.build_floods(cfg, rng, machines, defs_by_type,
                                                  round(cfg.alarm_events * cfg.flood_share))
    chatter_alarms, nuisance_pairs = events.build_chatter(cfg, rng, machines, defs_by_type, cfg.bad_actor_pairs,
                                                          round(cfg.alarm_events * cfg.chatter_share))
    remaining = base_total - len(scenario_alarms) - len(flood_alarms) - len(chatter_alarms)
    baseline = events.build_baseline(cfg, rng, machines, defs_by_type, state_index, remaining)
    alarms = scenario_alarms + flood_alarms + chatter_alarms + baseline
    events.finalize_alarms(cfg, rng, alarms, state_index, {s["shift_id"] for s in shifts})
    acks = events.build_acknowledgements(cfg, rng, alarms, shifts)
    log(f"[3] alarms: {len(alarms)} (floods {len(flood_alarms)} in {len(flood_eps)} episodes, "
        f"chatter {len(chatter_alarms)}, baseline {len(baseline)}), acks {len(acks)}")

    # ---- 4. incidents (rule-derived) + actions -----------------------------
    cands = incidents.derive_incidents(cfg, rng, alarms, acks, defs, state_events, ilk_index,
                                       interlocks, primary_zone)
    taken = {c["trigger_alarm_id"] for c in cands}
    cands += incidents.manual_reports(cfg, rng, alarms, acks, shifts, primary_zone, taken, cfg.manual_reports)
    cands += anomalies.contextless_incident_candidates(cfg, rng, machines, primary_zone, cfg.n_incident_no_trigger)
    inc_rows, inc_links, actions = incidents.finalize_incidents(cfg, rng, cands, alarms, staff)
    log(f"[4] incidents: {len(inc_rows)} {dict(Counter(i['rule_code'] for i in inc_rows))}, "
        f"links {len(inc_links)}, actions {len(actions)}")

    # ---- 5. labelled edge cases --------------------------------------------
    linked = {l["alarm_event_id"] for l in inc_links}
    labels = []
    labels += anomalies.inject_ack_before_alarm(cfg, rng, alarms, acks, linked, cfg.n_ack_before_alarm)
    labels += anomalies.inject_impossible_interlock(rng, ilk_events, cfg.n_impossible_interlock)
    dups, dup_labels = anomalies.inject_replay_floods(rng, alarms, flood_eps, cfg.n_replay_rows)
    labels += dup_labels
    alarms.extend(dups)
    alarms.sort(key=lambda a: (a["raised_ts"], a["alarm_event_id"]))
    labels += anomalies.inject_action_no_verification(rng, actions, cfg.n_action_no_verification)

    # ---- 6. ground truth (expected decisions from the documented rules) ----
    repeated = find_repeated_unsafe([i for i in inc_rows if not i.get("_gt")])
    gt = anomalies.build_ground_truth(labels, inc_rows, flood_eps, nuisance_pairs, repeated)
    log(f"[5] ground truth rows: {len(gt)} {dict(Counter(g['issue_type'] for g in gt))}")

    # ---- 7. export -----------------------------------------------------------
    state_events.sort(key=lambda e: (e["event_ts"], e["state_event_id"]))
    ilk_events.sort(key=lambda e: (e["event_ts"], e["interlock_event_id"]))
    acks.sort(key=lambda a: (a["ack_ts"], a["ack_id"]))
    tables = {
        "plant": plants, "safety_zone": zones, "machine": machines, "machine_zone": machine_zone,
        "interlock": interlocks, "alarm_definition": defs, "staff": staff, "operator_shift": shifts,
        "machine_state_event": state_events, "interlock_state_event": ilk_events, "alarm_event": alarms,
        "acknowledgement": acks, "incident": inc_rows, "incident_alarm": inc_links, "corrective_action": actions,
    }
    meta = {
        "generator": "plant-safety-event-analytics synthetic generator",
        "generator_version": GENERATOR_VERSION, "seed": seed, "scale": scale,
        "command": f"python -m generator.run --scale {scale} --seed {seed}",
        "window_start": fmt_ts(cfg.start_ts), "window_end": fmt_ts(cfg.end_ts),
    }
    t0 = time.time()
    manifest = export_all(out_dir, tables, gt, meta)
    log(f"[6] exported to {out_dir} in {time.time() - t0:.1f}s  combined_sha256={manifest['combined_sha256'][:16]}...")
    return manifest


def main():
    p = argparse.ArgumentParser(description="Synthetic plant safety event generator")
    p.add_argument("--scale", default="full", choices=["starter", "full"])
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--out", default=str(DEFAULT_OUTPUT_DIR), help="output base folder (default: database/)")
    a = p.parse_args()
    t = time.time()
    m = generate(a.scale, a.seed, a.out)
    print("\nRow counts:")
    for name, info in m["tables"].items():
        print(f"  {name:<24}{info['rows']:>8}")
    print(f"  {'ground_truth':<24}{m['ground_truth']['rows']:>8}")
    print(f"\nDone in {time.time() - t:.1f}s")


if __name__ == "__main__":
    main()
    