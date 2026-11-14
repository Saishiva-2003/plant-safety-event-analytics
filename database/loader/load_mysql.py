"""
Tier-3 loader: create the schema and bulk-load the generated CSVs into MySQL.

    cd backend                                   (venv active, backend/.env filled in)
    python ..\\database\\loader\\load_mysql.py       # Windows
    python ../database/loader/load_mysql.py      # Linux / macOS

Steps
  1. run database/schema/schema.sql  (drops + recreates all tables)
  2. load every CSV in FK-safe order (parents first) in batches
  3. load ground_truth (kept in its own table, never used by detection)
  4. verify row counts in MySQL == manifest.json
"""
import csv
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))          # reuse backend config + engine

from app.core.database import engine  # noqa: E402
from generator.exporter import GROUND_TRUTH_COLUMNS, TABLES  # noqa: E402

SCHEMA_FILE = ROOT / "database" / "schema" / "schema.sql"
CSV_DIR = ROOT / "database" / "seed" / "csv"
GT_FILE = ROOT / "database" / "ground_truth" / "ground_truth.csv"
MANIFEST = ROOT / "database" / "reports" / "manifest.json"
BATCH = 5000


def sql_statements(path: Path) -> list[str]:
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if not ln.strip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def read_rows(path: Path, columns: list[str]):
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            yield tuple((r[c] if r[c] != "" else None) for c in columns)


def load_table(cur, table: str, columns: list[str], path: Path) -> int:
    cols = ", ".join(f"`{c}`" for c in columns)
    marks = ", ".join(["%s"] * len(columns))
    sql = f"INSERT INTO `{table}` ({cols}) VALUES ({marks})"
    batch, total = [], 0
    for row in read_rows(path, columns):
        batch.append(row)
        if len(batch) >= BATCH:
            cur.executemany(sql, batch)
            total += len(batch)
            batch = []
    if batch:
        cur.executemany(sql, batch)
        total += len(batch)
    return total


def main():
    t0 = time.time()
    raw = engine.raw_connection()
    try:
        cur = raw.cursor()
        print(f"[1] creating schema from {SCHEMA_FILE.name}")
        for stmt in sql_statements(SCHEMA_FILE):
            cur.execute(stmt)
        raw.commit()

        print("[2] loading tables (parents first)")
        loaded = {}
        for table, columns in TABLES.items():
            t = time.time()
            loaded[table] = load_table(cur, table, columns, CSV_DIR / f"{table}.csv")
            raw.commit()
            print(f"    {table:<24}{loaded[table]:>8} rows  ({time.time() - t:.1f}s)")
        loaded["ground_truth"] = load_table(cur, "ground_truth", GROUND_TRUTH_COLUMNS, GT_FILE)
        raw.commit()
        print(f"[3] {'ground_truth':<24}{loaded['ground_truth']:>8} rows")

        print("[4] verifying row counts against manifest.json")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        expected = {t: v["rows"] for t, v in manifest["tables"].items()}
        expected["ground_truth"] = manifest["ground_truth"]["rows"]
        ok = True
        for table, exp in expected.items():
            cur.execute(f"SELECT COUNT(*) FROM `{table}`")
            n = cur.fetchone()[0]
            flag = "OK" if n == exp else "MISMATCH"
            ok &= n == exp
            if flag != "OK":
                print(f"    {table}: db={n} manifest={exp} {flag}")
        cur.close()
    finally:
        raw.close()
    print(f"\n{'LOAD OK' if ok else 'LOAD FAILED'} - {sum(loaded.values())} rows in {time.time() - t0:.1f}s")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()