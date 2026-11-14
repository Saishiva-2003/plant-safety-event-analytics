"""
Step 2a - Master (parent) data, generated FIRST:
    plant, safety_zone, machine, machine_zone (bridge N:M), interlock,
    alarm_definition, staff (operators/engineers), operator_shift
"""
from datetime import date, datetime, timedelta

from generator import id_factory as ids
from generator.config import ScaleConfig
from generator.rules import ACK_SLA_SEC, SHIFTS

PLANT_INFO = [
    ("Pune Stamping Plant", "Pune", "Maharashtra"),
    ("Chennai Assembly Plant", "Chennai", "Tamil Nadu"),
    ("Hosur Machining Plant", "Hosur", "Tamil Nadu"),
    ("Sanand Moulding Plant", "Sanand", "Gujarat"),
]

MACHINE_TYPES = ["HYDRAULIC_PRESS", "ROBOT_CELL", "CONVEYOR", "CNC_MILL", "INJECTION_MOLDER", "WELDING_STATION"]
TYPE_LABEL = {
    "HYDRAULIC_PRESS": "Hydraulic Press", "ROBOT_CELL": "Robot Cell", "CONVEYOR": "Conveyor",
    "CNC_MILL": "CNC Mill", "INJECTION_MOLDER": "Injection Molder", "WELDING_STATION": "Welding Station",
}
TYPE_ABBR = {
    "HYDRAULIC_PRESS": "HP", "ROBOT_CELL": "RC", "CONVEYOR": "CV",
    "CNC_MILL": "CN", "INJECTION_MOLDER": "IM", "WELDING_STATION": "WS",
}
TYPE_CRITICALITY = {
    "HYDRAULIC_PRESS": "A", "ROBOT_CELL": "A", "WELDING_STATION": "B",
    "CNC_MILL": "B", "INJECTION_MOLDER": "B", "CONVEYOR": "C",
}
MANUFACTURERS = ["Siemens", "ABB", "Fanuc", "Schuler", "Haas", "Engel", "KUKA"]

# (name, zone_type, hazard_level 1..5)
ZONE_TEMPLATES = [
    ("Press Line", "PRESS_AREA", 5),
    ("Robot Cell Area", "ROBOT_CELL", 4),
    ("Machining Bay", "MACHINING", 3),
    ("Assembly Line", "ASSEMBLY", 2),
    ("Material Handling", "LOGISTICS", 2),
]
TYPE_ZONE = {
    "HYDRAULIC_PRESS": "PRESS_AREA", "ROBOT_CELL": "ROBOT_CELL", "WELDING_STATION": "ROBOT_CELL",
    "CNC_MILL": "MACHINING", "INJECTION_MOLDER": "MACHINING", "CONVEYOR": "LOGISTICS",
}
INTERLOCKS_BY_TYPE = {
    "HYDRAULIC_PRESS": ["GUARD_DOOR", "LIGHT_CURTAIN", "E_STOP", "PRESSURE"],
    "ROBOT_CELL": ["GUARD_DOOR", "LIGHT_CURTAIN", "E_STOP"],
    "WELDING_STATION": ["GUARD_DOOR", "LIGHT_CURTAIN", "E_STOP"],
    "CNC_MILL": ["GUARD_DOOR", "E_STOP"],
    "INJECTION_MOLDER": ["GUARD_DOOR", "E_STOP", "PRESSURE"],
    "CONVEYOR": ["GUARD_DOOR", "E_STOP"],
}
INTERLOCK_LABEL = {
    "GUARD_DOOR": "Guard door switch", "LIGHT_CURTAIN": "Light curtain",
    "E_STOP": "Emergency stop circuit", "PRESSURE": "Pressure relief interlock",
}

# Safety alarms: (code, name, severity, required interlock type or None)
SAFETY_TEMPLATES = [
    ("GRD-OPEN", "Guard door opened during operation", "HIGH", "GUARD_DOOR"),
    ("LC-BREAK", "Light curtain interrupted", "HIGH", "LIGHT_CURTAIN"),
    ("ESTOP-PB", "Emergency stop push-button activated", "CRITICAL", "E_STOP"),
    ("BYPASS-RUN", "Safety interlock bypassed during operation", "CRITICAL", None),
    ("PRS-OVER", "Hydraulic overpressure", "CRITICAL", "PRESSURE"),
]
# Non-safety alarms: (code, name, category, severity)
OTHER_TEMPLATES = [
    ("TEMP-HIGH", "Process temperature high", "PROCESS", "MEDIUM"),
    ("MOTOR-OVL", "Motor overload", "EQUIPMENT", "HIGH"),
    ("PLC-COMM", "PLC communication loss", "SYSTEM", "HIGH"),
    ("PART-JAM", "Part jam detected", "PROCESS", "MEDIUM"),
    ("VIB-HIGH", "Vibration high", "EQUIPMENT", "MEDIUM"),
    ("HMI-TOUT", "HMI response timeout", "SYSTEM", "LOW"),
    ("PRS-LOW", "Supply pressure low", "PROCESS", "MEDIUM"),
    ("LUBE-LOW", "Lubrication level low", "EQUIPMENT", "LOW"),
    ("NET-LAT", "Network latency high", "SYSTEM", "LOW"),
    ("CYCLE-SLOW", "Cycle time exceeded", "PROCESS", "LOW"),
    ("ENC-FLT", "Encoder fault", "EQUIPMENT", "MEDIUM"),
    ("PWR-DIP", "Supply voltage dip", "SYSTEM", "MEDIUM"),
    ("QUAL-REJ", "Quality reject rate high", "PROCESS", "LOW"),
    ("BRG-TEMP", "Bearing temperature high", "EQUIPMENT", "MEDIUM"),
    ("SENS-DRIFT", "Sensor drift detected", "SYSTEM", "LOW"),
    ("FEED-STRV", "Material feed starved", "PROCESS", "LOW"),
    ("DRV-FLT", "Drive fault", "EQUIPMENT", "HIGH"),
    ("AIR-LOW", "Compressed air pressure low", "SYSTEM", "MEDIUM"),
    ("COOL-LOW", "Coolant level low", "PROCESS", "MEDIUM"),
    ("SERVO-ERR", "Servo following error", "EQUIPMENT", "MEDIUM"),
    ("UPS-BATT", "UPS running on battery", "SYSTEM", "MEDIUM"),
    ("TORQ-HIGH", "Torque high", "PROCESS", "HIGH"),
    ("FILT-CLOG", "Filter clogged", "EQUIPMENT", "LOW"),
    ("CLK-SYNC", "Controller clock out of sync", "SYSTEM", "LOW"),
    ("SPEED-DEV", "Speed deviation", "PROCESS", "LOW"),
    ("TOOL-WEAR", "Tool wear limit reached", "EQUIPMENT", "LOW"),
    ("LEVEL-HIGH", "Hopper level high", "PROCESS", "MEDIUM"),
    ("BELT-SLIP", "Belt slip detected", "EQUIPMENT", "MEDIUM"),
    ("FLOW-LOW", "Hydraulic flow low", "PROCESS", "MEDIUM"),
    ("HYD-TEMP", "Hydraulic oil temperature high", "EQUIPMENT", "MEDIUM"),
]


def build_plants(cfg: ScaleConfig) -> list[dict]:
    rows = []
    for i in range(1, cfg.plants + 1):
        name, city, state = PLANT_INFO[(i - 1) % len(PLANT_INFO)]
        rows.append({
            "plant_id": ids.plant_id(i), "plant_name": name, "city": city, "state": state,
            "country": "IN", "timezone": "Asia/Kolkata", "status": "ACTIVE",
            "opened_date": date(2010 + i, 4, 1),
        })
    return rows


def build_zones(cfg: ScaleConfig, plants: list[dict]) -> list[dict]:
    rows = []
    for p in plants:
        for n, (name, ztype, hazard) in enumerate(ZONE_TEMPLATES[: cfg.zones_per_plant], start=1):
            rows.append({
                "zone_id": ids.zone_id(p["plant_id"], n), "plant_id": p["plant_id"],
                "zone_name": f"{name} {n}", "zone_type": ztype, "hazard_level": hazard,
                "effective_from": date(2024, 1, 1), "effective_to": None, "status": "ACTIVE",
            })
    return rows


def build_machines(cfg: ScaleConfig, rng, plants, zones):
    """Returns machines + machine_zone bridge rows (each machine: 1 primary + optional secondary zone)."""
    machines, bridge = [], []
    per_plant = cfg.machines // cfg.plants
    zones_by_plant = {}
    for z in zones:
        zones_by_plant.setdefault(z["plant_id"], []).append(z)

    for p in plants:
        pz = zones_by_plant[p["plant_id"]]
        for n in range(1, per_plant + 1):
            mtype = MACHINE_TYPES[(n - 1) % len(MACHINE_TYPES)]
            mid = ids.machine_id(p["plant_id"], n)
            machines.append({
                "machine_id": mid, "plant_id": p["plant_id"],
                "machine_name": f"{TYPE_LABEL[mtype]} {n:02d}", "machine_type": mtype,
                "manufacturer": rng.choice(MANUFACTURERS), "criticality": TYPE_CRITICALITY[mtype],
                "commissioned_date": date(rng.randint(2015, 2024), rng.randint(1, 12), 1),
                "status": "ACTIVE",
            })
            # primary zone by machine type (fallback to Assembly / last zone)
            primary = next((z for z in pz if z["zone_type"] == TYPE_ZONE[mtype]), None)
            if primary is None:
                primary = next((z for z in pz if z["zone_type"] == "ASSEMBLY"), pz[-1])
            bridge.append({"machine_id": mid, "zone_id": primary["zone_id"], "is_primary": True,
                           "effective_from": date(2024, 1, 1), "effective_to": None})
            if rng.random() < 0.3:
                others = [z for z in pz if z["zone_id"] != primary["zone_id"]]
                sec = rng.choice(others)
                bridge.append({"machine_id": mid, "zone_id": sec["zone_id"], "is_primary": False,
                               "effective_from": date(2024, 1, 1), "effective_to": None})
    return machines, bridge


def build_interlocks(machines, bridge) -> list[dict]:
    primary_zone = {b["machine_id"]: b["zone_id"] for b in bridge if b["is_primary"]}
    rows = []
    for m in machines:
        for n, itype in enumerate(INTERLOCKS_BY_TYPE[m["machine_type"]], start=1):
            rows.append({
                "interlock_id": ids.interlock_id(m["machine_id"], n), "machine_id": m["machine_id"],
                "zone_id": primary_zone[m["machine_id"]], "interlock_type": itype,
                "description": f"{INTERLOCK_LABEL[itype]} - {m['machine_name']}",
                "sil_level": 3 if itype in ("E_STOP", "LIGHT_CURTAIN") else 2,
                "initial_state": "ENGAGED", "installed_date": m["commissioned_date"],
                "status": "ACTIVE",
            })
    return rows


def build_alarm_definitions(cfg: ScaleConfig) -> list[dict]:
    """Safety definitions for every machine type first, then non-safety ones, truncated to N."""
    candidates = []
    for mtype in MACHINE_TYPES:
        for code, name, sev, itype in SAFETY_TEMPLATES:
            if itype is not None and itype not in INTERLOCKS_BY_TYPE[mtype]:
                continue
            candidates.append((f"{TYPE_ABBR[mtype]}-{code}", code, name, "SAFETY", sev, mtype, itype))
    for code, name, cat, sev in OTHER_TEMPLATES:
        for mtype in MACHINE_TYPES:
            candidates.append((f"{TYPE_ABBR[mtype]}-{code}", code, name, cat, sev, mtype, None))

    if cfg.alarm_definitions > len(candidates):
        raise ValueError(f"max {len(candidates)} alarm definitions available")
    rows = []
    for n, (full_code, code, name, cat, sev, mtype, itype) in enumerate(candidates[: cfg.alarm_definitions], 1):
        rows.append({
            "alarm_def_id": ids.alarm_def_id(n), "alarm_code": full_code, "base_code": code,
            "alarm_name": f"{name} ({TYPE_LABEL[mtype]})", "category": cat, "severity": sev,
            "machine_type": mtype, "interlock_type": itype,
            "ack_required": sev != "LOW", "ack_sla_sec": ACK_SLA_SEC[sev],
            "effective_from": date(2024, 1, 1), "status": "ACTIVE",
        })
    return rows


def build_staff(cfg: ScaleConfig, plants) -> list[dict]:
    rows = []
    for p in plants:
        for n in range(1, cfg.operators_per_plant + 1):
            rows.append({"staff_id": ids.operator_id(p["plant_id"], n), "plant_id": p["plant_id"],
                         "role": "OPERATOR", "display_name": f"Operator {p['plant_id']}-{n:02d}"})
        for n in range(1, cfg.engineers_per_plant + 1):
            rows.append({"staff_id": ids.engineer_id(p["plant_id"], n), "plant_id": p["plant_id"],
                         "role": "ENGINEER", "display_name": f"Engineer {p['plant_id']}-{n:02d}"})
    return rows


def build_shifts(cfg: ScaleConfig, rng, plants, staff) -> list[dict]:
    """3 shifts/day/plant. Starts the day before the window so 00:00-06:00 is covered by shift C."""
    rows = []
    first_day = (cfg.start_ts - timedelta(days=1)).date()
    for p in plants:
        ops = [s["staff_id"] for s in staff if s["plant_id"] == p["plant_id"] and s["role"] == "OPERATOR"]
        for d in range(cfg.days + 1):
            day = first_day + timedelta(days=d)
            crew = rng.sample(ops, 3)               # 3 different operators per day
            for (code, (h_start, h_end)), op in zip(SHIFTS.items(), crew):
                start = datetime(day.year, day.month, day.day, h_start)
                end = start + timedelta(hours=(h_end - h_start) % 24)
                if end <= cfg.start_ts or start >= cfg.end_ts:
                    continue
                rows.append({
                    "shift_id": ids.shift_id(p["plant_id"], day, code), "plant_id": p["plant_id"],
                    "shift_code": code, "shift_date": day, "start_ts": start, "end_ts": end,
                    "operator_id": op,
                })
    return rows


def shift_key(ts: datetime) -> tuple[date, str]:
    """Which shift (date, code) covers a timestamp."""
    h = ts.hour
    if 6 <= h < 14:
        return ts.date(), "A"
    if 14 <= h < 22:
        return ts.date(), "B"
    if h >= 22:
        return ts.date(), "C"
    return (ts - timedelta(days=1)).date(), "C"