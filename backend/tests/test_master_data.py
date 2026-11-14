"""Master data tests (full scale, fixed seed)."""
import random
from collections import Counter

from generator import master_data as md
from generator.config import DEFAULT_SEED, get_scale


def build():
    cfg = get_scale("full")
    rng = random.Random(DEFAULT_SEED)
    p = md.build_plants(cfg)
    z = md.build_zones(cfg, p)
    m, b = md.build_machines(cfg, rng, p, z)
    i = md.build_interlocks(m, b)
    d = md.build_alarm_definitions(cfg)
    s = md.build_staff(cfg, p)
    sh = md.build_shifts(cfg, rng, p, s)
    return p, z, m, b, i, d, s, sh


def test_volumes_match_problem_statement():
    p, z, m, b, i, d, s, sh = build()
    assert len(p) == 4 and len(m) == 60 and len(d) == 200
    print(f"\nplants={len(p)} zones={len(z)} machines={len(m)} bridge={len(b)} "
          f"interlocks={len(i)} defs={len(d)} staff={len(s)} shifts={len(sh)}")
    print("def categories:", dict(Counter(x["category"] for x in d)))


def test_ids_unique_and_formatted():
    p, z, m, b, i, d, s, sh = build()
    for rows, key in ((p, "plant_id"), (z, "zone_id"), (m, "machine_id"), (i, "interlock_id"),
                      (d, "alarm_def_id"), (s, "staff_id"), (sh, "shift_id")):
        values = [r[key] for r in rows]
        assert len(values) == len(set(values)), f"duplicate {key}"
    assert z[0]["zone_id"] == "SAFE-P01-001"
    assert m[0]["machine_id"] == "P01-M001"


def test_foreign_keys_valid():
    p, z, m, b, i, d, s, sh = build()
    plant_ids = {x["plant_id"] for x in p}
    zone_ids = {x["zone_id"] for x in z}
    machine_ids = {x["machine_id"] for x in m}
    staff_ids = {x["staff_id"] for x in s}
    assert all(x["plant_id"] in plant_ids for x in m + z + sh)
    assert all(x["machine_id"] in machine_ids and x["zone_id"] in zone_ids for x in b + i)
    assert all(x["operator_id"] in staff_ids for x in sh)
    # every machine has exactly one primary zone
    assert Counter(x["machine_id"] for x in b if x["is_primary"]) == Counter({mid: 1 for mid in machine_ids})


def test_every_machine_type_has_guard_trip_and_bypass_alarm():
    *_, d, _, _ = build()
    codes = {(x["machine_type"], x["base_code"]) for x in d}
    for mtype in md.MACHINE_TYPES:
        assert (mtype, "GRD-OPEN") in codes and (mtype, "BYPASS-RUN") in codes


def test_shifts_cover_whole_window():
    *_, sh = build()
    cfg = get_scale("full")
    p01 = sorted((x for x in sh if x["plant_id"] == "P01"), key=lambda x: x["start_ts"])
    assert p01[0]["start_ts"] <= cfg.start_ts and p01[-1]["end_ts"] >= cfg.end_ts
    assert all(a["end_ts"] == b["start_ts"] for a, b in zip(p01, p01[1:]))   # no gaps