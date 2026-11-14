"""
Step 9 - Export CSV / JSON / SQL seed + ground truth + manifest (row counts, SHA-256).

Only the columns listed in TABLES are written: internal helper fields (prefixed '_')
such as the generation source never reach the input files -> no label leakage.
"""
import csv
import hashlib
import json
from datetime import date, datetime
from pathlib import Path

from generator.config import fmt_ts

# Parent tables first, children after (FK-safe load order)
TABLES = {
    "plant": ["plant_id", "plant_name", "city", "state", "country", "timezone", "status", "opened_date"],
    "safety_zone": ["zone_id", "plant_id", "zone_name", "zone_type", "hazard_level", "effective_from",
                    "effective_to", "status"],
    "machine": ["machine_id", "plant_id", "machine_name", "machine_type", "manufacturer", "criticality",
                "commissioned_date", "status"],
    "machine_zone": ["machine_id", "zone_id", "is_primary", "effective_from", "effective_to"],
    "interlock": ["interlock_id", "machine_id", "zone_id", "interlock_type", "description", "sil_level",
                  "initial_state", "installed_date", "status"],
    "alarm_definition": ["alarm_def_id", "alarm_code", "base_code", "alarm_name", "category", "severity",
                         "machine_type", "interlock_type", "ack_required", "ack_sla_sec", "effective_from", "status"],
    "staff": ["staff_id", "plant_id", "role", "display_name"],
    "operator_shift": ["shift_id", "plant_id", "shift_code", "shift_date", "start_ts", "end_ts", "operator_id"],
    "machine_state_event": ["state_event_id", "machine_id", "event_ts", "from_state", "to_state", "reason"],
    "interlock_state_event": ["interlock_event_id", "interlock_id", "event_ts", "from_state", "to_state",
                              "machine_state_snapshot", "reason", "actor"],
    "alarm_event": ["alarm_event_id", "machine_id", "alarm_def_id", "shift_id", "interlock_id", "raised_ts",
                    "cleared_ts", "received_ts", "source_seq", "machine_state"],
    "acknowledgement": ["ack_id", "alarm_event_id", "shift_id", "operator_id", "ack_ts", "response_sec", "ack_method"],
    "incident": ["incident_id", "machine_id", "zone_id", "trigger_alarm_id", "rule_code", "severity", "opened_ts",
                 "status", "closed_ts", "reported_by", "description"],
    "incident_alarm": ["incident_id", "alarm_event_id", "link_role"],
    "corrective_action": ["action_id", "incident_id", "action_type", "description", "owner_id", "created_ts",
                          "due_ts", "status", "started_ts", "completed_ts", "verified_ts", "verified_by", "closed_ts"],
}
GROUND_TRUTH_COLUMNS = ["gt_id", "category", "issue_type", "record_type", "record_id", "related_id",
                        "event_ts", "detail", "expected_decision"]


def _text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, datetime):
        return fmt_ts(v)
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def _json_value(v):
    if v is None or isinstance(v, (bool, int)):
        return v
    if isinstance(v, float):
        return round(v, 3)
    return _text(v)


def _sql_value(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return f"{v:.3f}"
    s = _text(v).replace("\\", "\\\\").replace("'", "''")
    return f"'{s}'"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, columns, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(columns)
        for r in rows:
            w.writerow([_text(r.get(c)) for c in columns])


def write_json(path: Path, columns, rows):
    data = [{c: _json_value(r.get(c)) for c in columns} for r in rows]
    with open(path, "w", newline="\n", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")


def write_sql(path: Path, tables: dict, batch: int = 500):
    with open(path, "w", newline="\n", encoding="utf-8") as f:
        f.write("-- Synthetic seed data (generated). Load AFTER database/schema/schema.sql\n")
        f.write("SET FOREIGN_KEY_CHECKS = 0;\n")
        for name, columns in TABLES.items():
            rows = tables[name]
            cols = ", ".join(f"`{c}`" for c in columns)
            for i in range(0, len(rows), batch):
                values = ",\n".join("(" + ", ".join(_sql_value(r.get(c)) for c in columns) + ")"
                                    for r in rows[i:i + batch])
                f.write(f"INSERT INTO `{name}` ({cols}) VALUES\n{values};\n")
        f.write("SET FOREIGN_KEY_CHECKS = 1;\n")


def export_all(out_dir: Path, tables: dict, ground_truth: list, meta: dict) -> dict:
    out_dir = Path(out_dir)
    csv_dir, json_dir, sql_dir = out_dir / "seed" / "csv", out_dir / "seed" / "json", out_dir / "seed" / "sql"
    gt_dir, rep_dir = out_dir / "ground_truth", out_dir / "reports"
    for d in (csv_dir, json_dir, sql_dir, gt_dir, rep_dir):
        d.mkdir(parents=True, exist_ok=True)

    manifest_tables = {}
    for name, columns in TABLES.items():
        rows = tables[name]
        write_csv(csv_dir / f"{name}.csv", columns, rows)
        write_json(json_dir / f"{name}.json", columns, rows)
        manifest_tables[name] = {
            "rows": len(rows),
            "csv_sha256": sha256_file(csv_dir / f"{name}.csv"),
            "json_sha256": sha256_file(json_dir / f"{name}.json"),
        }
    write_sql(sql_dir / "seed.sql", tables)
    write_csv(gt_dir / "ground_truth.csv", GROUND_TRUTH_COLUMNS, ground_truth)
    write_json(gt_dir / "ground_truth.json", GROUND_TRUTH_COLUMNS, ground_truth)

    combined = hashlib.sha256()
    for name in TABLES:
        combined.update(manifest_tables[name]["csv_sha256"].encode())
    gt_hash = sha256_file(gt_dir / "ground_truth.csv")
    combined.update(gt_hash.encode())

    manifest = {
        **meta,
        "provenance": "100% synthetic data produced by this generator; no external or personal data used.",
        "tables": manifest_tables,
        "ground_truth": {"rows": len(ground_truth), "csv_sha256": gt_hash},
        "seed_sql_sha256": sha256_file(sql_dir / "seed.sql"),
        "combined_sha256": combined.hexdigest(),
    }
    with open(rep_dir / "manifest.json", "w", newline="\n", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    return manifest