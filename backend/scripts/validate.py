"""
Step 8 - Validate the generated dataset (reads the CSV files, no database needed).

    cd backend
    python -m scripts.validate                 # validates database/seed/csv
    python -m scripts.validate --base tmp_repro/run1

Checks: primary keys, foreign keys, enums, date ordering, arithmetic reconciliation,
lifecycle transitions and duplicates.  Violations that are exactly the LABELLED
anomalies in ground_truth.csv are reported as EXPECTED (the edge cases we injected);
anything else is a FAIL.  Writes database/reports/validation_summary.json.
"""
import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from generator.config import DEFAULT_OUTPUT_DIR
from generator.rules import (
    ACK_METHODS, ACK_SLA_SEC, ACTION_STATUSES, ACTION_TYPES, ALARM_CATEGORIES, INCIDENT_RULES,
    INCIDENT_STATUSES, INTERLOCK_STATES, INTERLOCK_TYPES, MACHINE_STATES, SEVERITIES,
    STATES_IMPOSSIBLE_WHEN_TRIPPED, is_valid_interlock_transition, is_valid_machine_transition,
)

PRIMARY_KEYS = {
    "plant": ["plant_id"], "safety_zone": ["zone_id"], "machine": ["machine_id"],
    "machine_zone": ["machine_id", "zone_id"], "interlock": ["interlock_id"],
    "alarm_definition": ["alarm_def_id"], "staff": ["staff_id"], "operator_shift": ["shift_id"],
    "machine_state_event": ["state_event_id"], "interlock_state_event": ["interlock_event_id"],
    "alarm_event": ["alarm_event_id"], "acknowledgement": ["ack_id"], "incident": ["incident_id"],
    "incident_alarm": ["incident_id", "alarm_event_id"], "corrective_action": ["action_id"],
}
# (child table, child column, parent table, parent column, nullable)
FOREIGN_KEYS = [
    ("safety_zone", "plant_id", "plant", "plant_id", False),
    ("machine", "plant_id", "plant", "plant_id", False),
    ("machine_zone", "machine_id", "machine", "machine_id", False),
    ("machine_zone", "zone_id", "safety_zone", "zone_id", False),
    ("interlock", "machine_id", "machine", "machine_id", False),
    ("interlock", "zone_id", "safety_zone", "zone_id", False),
    ("staff", "plant_id", "plant", "plant_id", False),
    ("operator_shift", "plant_id", "plant", "plant_id", False),
    ("operator_shift", "operator_id", "staff", "staff_id", False),
    ("machine_state_event", "machine_id", "machine", "machine_id", False),
    ("interlock_state_event", "interlock_id", "interlock", "interlock_id", False),
    ("alarm_event", "machine_id", "machine", "machine_id", False),
    ("alarm_event", "alarm_def_id", "alarm_definition", "alarm_def_id", False),
    ("alarm_event", "shift_id", "operator_shift", "shift_id", False),
    ("alarm_event", "interlock_id", "interlock", "interlock_id", True),
    ("acknowledgement", "alarm_event_id", "alarm_event", "alarm_event_id", False),
    ("acknowledgement", "shift_id", "operator_shift", "shift_id", False),
    ("acknowledgement", "operator_id", "staff", "staff_id", False),
    ("incident", "machine_id", "machine", "machine_id", False),
    ("incident", "zone_id", "safety_zone", "zone_id", False),
    ("incident", "trigger_alarm_id", "alarm_event", "alarm_event_id", True),
    ("incident_alarm", "incident_id", "incident", "incident_id", False),
    ("incident_alarm", "alarm_event_id", "alarm_event", "alarm_event_id", False),
    ("corrective_action", "incident_id", "incident", "incident_id", False),
    ("corrective_action", "owner_id", "staff", "staff_id", False),
    ("corrective_action", "verified_by", "staff", "staff_id", True),
]
ENUMS = [
    ("alarm_definition", "severity", SEVERITIES), ("alarm_definition", "category", ALARM_CATEGORIES),
    ("alarm_definition", "interlock_type", INTERLOCK_TYPES + [""]),
    ("interlock", "interlock_type", INTERLOCK_TYPES), ("staff", "role", ["OPERATOR", "ENGINEER"]),
    ("operator_shift", "shift_code", ["A", "B", "C"]),
    ("machine_state_event", "from_state", MACHINE_STATES), ("machine_state_event", "to_state", MACHINE_STATES),
    ("interlock_state_event", "from_state", INTERLOCK_STATES), ("interlock_state_event", "to_state", INTERLOCK_STATES),
    ("interlock_state_event", "machine_state_snapshot", MACHINE_STATES),
    ("alarm_event", "machine_state", MACHINE_STATES), ("acknowledgement", "ack_method", ACK_METHODS),
    ("incident", "rule_code", list(INCIDENT_RULES)), ("incident", "severity", SEVERITIES),
    ("incident", "status", INCIDENT_STATUSES), ("incident_alarm", "link_role", ["TRIGGER", "CONTEXT"]),
    ("corrective_action", "status", ACTION_STATUSES), ("corrective_action", "action_type", ACTION_TYPES),
    ("safety_zone", "hazard_level", ["1", "2", "3", "4", "5"]),
]


def ts(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f") if s else None


def load(csv_dir: Path) -> dict:
    data = {}
    for name in PRIMARY_KEYS:
        with open(csv_dir / f"{name}.csv", encoding="utf-8", newline="") as f:
            data[name] = list(csv.DictReader(f))
    return data


def load_ground_truth(gt_file: Path) -> dict:
    gt = defaultdict(set)
    with open(gt_file, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            gt[r["issue_type"]].add(r["record_id"])
    return gt


class Report:
    def __init__(self, gt):
        self.gt, self.results = gt, []

    def add(self, category, name, violations, expected_issue=None):
        ids = sorted(set(violations))
        labelled = self.gt.get(expected_issue, set()) if expected_issue else set()
        if not ids:
            status = "PASS" if not labelled else "FAIL"     # labelled anomaly not visible -> FAIL
        elif expected_issue and set(ids) == labelled:
            status = "EXPECTED"                              # only the injected, labelled edge cases
        else:
            status = "FAIL"
        self.results.append({"category": category, "check": name, "violations": len(ids),
                             "expected_issue": expected_issue, "labelled": len(labelled),
                             "status": status, "sample": ids[:5]})


def run_checks(d: dict, gt: dict, manifest: dict | None) -> Report:
    r = Report(gt)

    # ---- 1. primary keys ---------------------------------------------------
    for t, cols in PRIMARY_KEYS.items():
        keys = Counter(tuple(row[c] for c in cols) for row in d[t])
        r.add("primary_key", f"{t} PK unique", ["|".join(k) for k, n in keys.items() if n > 1])

    # ---- 2. foreign keys ---------------------------------------------------
    for child, col, parent, pcol, nullable in FOREIGN_KEYS:
        valid = {row[pcol] for row in d[parent]}
        bad = [row[col] for row in d[child] if not (row[col] == "" and nullable) and row[col] not in valid]
        r.add("foreign_key", f"{child}.{col} -> {parent}", bad)
    staff = {s["staff_id"] for s in d["staff"]}
    r.add("foreign_key", "incident.reported_by -> staff|SYSTEM",
          [i["incident_id"] for i in d["incident"] if i["reported_by"] not in staff | {"SYSTEM"}])

    # ---- 3. enums ----------------------------------------------------------
    for t, col, allowed in ENUMS:
        bad = [f"{row[col]}" for row in d[t] if row[col] not in allowed and not (row[col] == "" and col == "from_state")]
        r.add("enum", f"{t}.{col} allowed values", bad)

    # ---- 4. date ordering --------------------------------------------------
    alarms = {a["alarm_event_id"]: a for a in d["alarm_event"]}
    r.add("date_order", "alarm cleared_ts >= raised_ts",
          [a["alarm_event_id"] for a in d["alarm_event"] if a["cleared_ts"] and a["cleared_ts"] < a["raised_ts"]])
    r.add("date_order", "alarm received_ts >= raised_ts",
          [a["alarm_event_id"] for a in d["alarm_event"] if a["received_ts"] < a["raised_ts"]])
    r.add("date_order", "acknowledgement after alarm raise",
          [k["ack_id"] for k in d["acknowledgement"] if k["ack_ts"] < alarms[k["alarm_event_id"]]["raised_ts"]],
          "ACK_BEFORE_ALARM")
    r.add("date_order", "shift start < end",
          [s["shift_id"] for s in d["operator_shift"] if not s["start_ts"] < s["end_ts"]])
    r.add("date_order", "incident closed_ts >= opened_ts",
          [i["incident_id"] for i in d["incident"] if i["closed_ts"] and i["closed_ts"] < i["opened_ts"]])
    seq = ["created_ts", "started_ts", "completed_ts", "verified_ts", "closed_ts"]
    bad = []
    for a in d["corrective_action"]:
        present = [a[c] for c in seq if a[c]]
        if present != sorted(present):
            bad.append(a["action_id"])
    r.add("date_order", "corrective action timeline ordered", bad)
    shifts = {s["shift_id"]: s for s in d["operator_shift"]}
    r.add("date_order", "alarm raised inside its shift",
          [a["alarm_event_id"] for a in d["alarm_event"]
           if not shifts[a["shift_id"]]["start_ts"] <= a["raised_ts"] < shifts[a["shift_id"]]["end_ts"]])

    # ---- 5. arithmetic reconciliation -------------------------------------
    r.add("reconciliation", "response_sec = ack_ts - raised_ts",
          [k["ack_id"] for k in d["acknowledgement"]
           if abs((ts(k["ack_ts"]) - ts(alarms[k["alarm_event_id"]]["raised_ts"])).total_seconds()
                  - float(k["response_sec"])) > 0.001])
    r.add("reconciliation", "ack_sla_sec matches severity rule",
          [x["alarm_def_id"] for x in d["alarm_definition"] if int(x["ack_sla_sec"]) != ACK_SLA_SEC[x["severity"]]])
    acts = defaultdict(list)
    for a in d["corrective_action"]:
        acts[a["incident_id"]].append(a)
    bad = []
    for i in d["incident"]:
        a = acts[i["incident_id"]]
        exp = ("OPEN" if not a else "CLOSED" if all(x["status"] == "CLOSED" for x in a)
               else "INVESTIGATING" if all(x["status"] == "OPEN" for x in a) else "ACTION_PENDING")
        if exp != i["status"]:
            bad.append(i["incident_id"])
    r.add("reconciliation", "incident status derived from actions", bad)
    if manifest:
        r.add("reconciliation", "row counts match manifest",
              [t for t in PRIMARY_KEYS if manifest["tables"][t]["rows"] != len(d[t])])

    # ---- 6. lifecycle transitions -----------------------------------------
    bad, last = [], {}
    for e in sorted(d["machine_state_event"], key=lambda x: (x["machine_id"], x["event_ts"], x["state_event_id"])):
        prev = last.get(e["machine_id"], "OFF")
        if e["from_state"] != prev or not is_valid_machine_transition(e["from_state"], e["to_state"]):
            bad.append(e["state_event_id"])
        last[e["machine_id"]] = e["to_state"]
    r.add("lifecycle", "machine state transitions valid", bad)
    bad, last = [], {}
    for e in sorted(d["interlock_state_event"], key=lambda x: (x["interlock_id"], x["event_ts"], x["interlock_event_id"])):
        prev = last.get(e["interlock_id"], "ENGAGED")
        if e["from_state"] != prev or not is_valid_interlock_transition(e["from_state"], e["to_state"]):
            bad.append(e["interlock_event_id"])
        last[e["interlock_id"]] = e["to_state"]
    r.add("lifecycle", "interlock state transitions valid", bad)
    r.add("lifecycle", "machine not RUNNING while interlock TRIPPED",
          [e["interlock_event_id"] for e in d["interlock_state_event"]
           if e["to_state"] == "TRIPPED" and e["machine_state_snapshot"] in STATES_IMPOSSIBLE_WHEN_TRIPPED],
          "IMPOSSIBLE_INTERLOCK_STATE")
    r.add("lifecycle", "action CLOSED only after verification",
          [a["action_id"] for a in d["corrective_action"]
           if a["status"] == "CLOSED" and (not a["verified_ts"] or not a["verified_by"])],
          "ACTION_CLOSED_NO_VERIFICATION")
    linked = {l["incident_id"] for l in d["incident_alarm"]}
    r.add("lifecycle", "incident has triggering context (trigger or linked alarms)",
          [i["incident_id"] for i in d["incident"] if not i["trigger_alarm_id"] and i["incident_id"] not in linked],
          "INCIDENT_NO_TRIGGER")

    # ---- 7. duplicates -----------------------------------------------------
    first = {}
    dups = []
    for a in sorted(d["alarm_event"], key=lambda x: (x["received_ts"], x["alarm_event_id"])):
        key = (a["machine_id"], a["alarm_def_id"], a["source_seq"])
        if key in first:
            dups.append(a["alarm_event_id"])          # later-received copy = replay
        else:
            first[key] = a["alarm_event_id"]
    r.add("duplicate", "alarm (machine, definition, source_seq) unique", dups, "REPLAY_DUPLICATE_FLOOD")
    r.add("duplicate", "one acknowledgement per alarm",
          [k for k, n in Counter(x["alarm_event_id"] for x in d["acknowledgement"]).items() if n > 1])
    return r


def validate(base=DEFAULT_OUTPUT_DIR, write=True, verbose=True) -> dict:
    base = Path(base)
    d = load(base / "seed" / "csv")
    gt = load_ground_truth(base / "ground_truth" / "ground_truth.csv")
    mpath = base / "reports" / "manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else None
    rep = run_checks(d, gt, manifest)
    counts = Counter(x["status"] for x in rep.results)
    summary = {
        "dataset": str(base), "total_checks": len(rep.results),
        "passed": counts["PASS"], "expected_anomalies": counts["EXPECTED"], "failed": counts["FAIL"],
        "overall": "PASS" if counts["FAIL"] == 0 else "FAIL",
        "row_counts": {t: len(v) for t, v in d.items()},
        "checks": rep.results,
    }
    if write:
        (base / "reports").mkdir(parents=True, exist_ok=True)
        with open(base / "reports" / "validation_summary.json", "w", newline="\n", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
            f.write("\n")
    if verbose:
        print(f"{'STATUS':<9}{'CATEGORY':<16}{'VIOLATIONS':>10}  CHECK")
        for x in rep.results:
            extra = f"  (labelled {x['expected_issue']}={x['labelled']})" if x["expected_issue"] else ""
            print(f"{x['status']:<9}{x['category']:<16}{x['violations']:>10}  {x['check']}{extra}")
        print(f"\nTOTAL {summary['total_checks']} checks | PASS {summary['passed']} | "
              f"EXPECTED {summary['expected_anomalies']} | FAIL {summary['failed']}  ->  {summary['overall']}")
    return summary


def main():
    p = argparse.ArgumentParser(description="Validate generated safety dataset")
    p.add_argument("--base", default=str(DEFAULT_OUTPUT_DIR))
    a = p.parse_args()
    s = validate(a.base)
    sys.exit(0 if s["overall"] == "PASS" else 1)


if __name__ == "__main__":
    main()