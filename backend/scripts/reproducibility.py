"""
Step 10 - Reproducibility proof: generate twice with the same seed, compare
row counts and SHA-256 checksums of every output file.

    cd backend
    python -m scripts.reproducibility                 # full scale, seed 20261022
    python -m scripts.reproducibility --scale starter

Writes database/reports/repro_report.json
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

from generator.config import DEFAULT_OUTPUT_DIR, DEFAULT_SEED
from generator.run import generate

BACKEND_DIR = Path(__file__).resolve().parents[1]
TMP_DIR = BACKEND_DIR / "tmp_repro"


def compare(m1: dict, m2: dict, published: dict | None) -> list[dict]:
    rows = []
    for table, a in m1["tables"].items():
        b = m2["tables"][table]
        row = {"table": table, "rows_run1": a["rows"], "rows_run2": b["rows"],
               "sha256_run1": a["csv_sha256"][:16], "sha256_run2": b["csv_sha256"][:16],
               "identical": a == b}
        if published:
            row["matches_published"] = published["tables"].get(table) == a
        rows.append(row)
    gt_equal = m1["ground_truth"] == m2["ground_truth"]
    rows.append({"table": "ground_truth", "rows_run1": m1["ground_truth"]["rows"],
                 "rows_run2": m2["ground_truth"]["rows"], "sha256_run1": m1["ground_truth"]["csv_sha256"][:16],
                 "sha256_run2": m2["ground_truth"]["csv_sha256"][:16], "identical": gt_equal,
                 **({"matches_published": published["ground_truth"] == m1["ground_truth"]} if published else {})})
    return rows


def main():
    p = argparse.ArgumentParser(description="Generate twice and compare checksums")
    p.add_argument("--scale", default="full", choices=["starter", "full"])
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    a = p.parse_args()

    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    print(f"Run 1 -> {TMP_DIR / 'run1'}")
    m1 = generate(a.scale, a.seed, TMP_DIR / "run1", verbose=False)
    print(f"Run 2 -> {TMP_DIR / 'run2'}")
    m2 = generate(a.scale, a.seed, TMP_DIR / "run2", verbose=False)

    pub_path = Path(DEFAULT_OUTPUT_DIR) / "reports" / "manifest.json"
    published = None
    if pub_path.exists():
        pm = json.loads(pub_path.read_text(encoding="utf-8"))
        if pm.get("scale") == a.scale and pm.get("seed") == a.seed:
            published = pm

    rows = compare(m1, m2, published)
    print(f"\n{'TABLE':<24}{'ROWS 1':>8}{'ROWS 2':>8}  {'SHA256 RUN 1':<18}{'SHA256 RUN 2':<18}SAME")
    for r in rows:
        print(f"{r['table']:<24}{r['rows_run1']:>8}{r['rows_run2']:>8}  {r['sha256_run1']:<18}"
              f"{r['sha256_run2']:<18}{'YES' if r['identical'] else 'NO'}")
    identical = all(r["identical"] for r in rows) and m1["combined_sha256"] == m2["combined_sha256"]
    report = {
        "scale": a.scale, "seed": a.seed, "runs": 2,
        "combined_sha256_run1": m1["combined_sha256"], "combined_sha256_run2": m2["combined_sha256"],
        "identical": identical,
        "matches_published_dataset": (published["combined_sha256"] == m1["combined_sha256"]) if published else None,
        "tables": rows,
    }
    out = Path(DEFAULT_OUTPUT_DIR) / "reports" / "repro_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="\n", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    print(f"\ncombined sha256 run1 = {m1['combined_sha256']}")
    print(f"combined sha256 run2 = {m2['combined_sha256']}")
    if published:
        print(f"matches published dataset in database/: {report['matches_published_dataset']}")
    print(f"REPRODUCIBLE: {'YES' if identical else 'NO'}   (report: {out})")
    shutil.rmtree(TMP_DIR, ignore_errors=True)
    sys.exit(0 if identical else 1)


if __name__ == "__main__":
    main()