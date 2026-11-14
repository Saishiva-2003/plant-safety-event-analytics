"""
One command for the whole data pipeline (Tier 2 -> Tier 3):

    1. generate     synthetic data (fixed seed)        -> database/seed, ground_truth, reports/manifest.json
    2. validate     80 checks (PK, FK, enums, ...)     -> reports/validation_summary.json   (stops on FAIL)
    3. reproduce    generate twice, compare SHA-256    -> reports/repro_report.json         (optional)
    4. load         schema.sql + all rows into MySQL   -> safety_db                         (stops on mismatch)
    5. docs         regenerate docs/*.md
    6. tests        pytest                                                                  (optional)
    7. refresh      tell a running API to rebuild its cache
    8. serve        start the API on http://localhost:8000 (reuses it if already running)  (optional)

Usage (from backend/, venv active):
    python run_all.py                       # full pipeline with defaults (full scale, seed 20261022)
    python run_all.py --skip-repro --skip-tests
    python run_all.py --serve               # ... and start the API at the end
    python run_all.py --scale starter       # small dataset (API tests expect the full one -> tests skipped)
"""
import argparse
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
ROOT = BACKEND.parent
PY = sys.executable                     # the venv's python
API_URL = "http://localhost:8000"


def step(n, title, cmd, required=True):
    print(f"\n{'=' * 78}\n[{n}] {title}\n    $ {' '.join(str(c) for c in cmd)}\n{'=' * 78}", flush=True)
    t = time.time()
    rc = subprocess.call(cmd, cwd=BACKEND)
    secs = time.time() - t
    status = "OK" if rc == 0 else "FAILED"
    print(f"--> {title}: {status} ({secs:.1f}s)", flush=True)
    if rc != 0 and required:
        print(f"\nPipeline stopped at step {n} ({title}). Fix the error above and run again.")
        sys.exit(rc)
    return title, status, secs


def api_running() -> bool:
    """True if an API is already listening on port 8000."""
    try:
        urllib.request.urlopen(f"{API_URL}/api/health", timeout=3)
        return True
    except Exception:
        return False


def refresh_api() -> str:
    """Ask a running API to drop its in-memory cache so it shows the freshly loaded data."""
    try:
        req = urllib.request.Request(f"{API_URL}/api/meta/refresh", method="POST")
        urllib.request.urlopen(req, timeout=3)
        return "running API cache refreshed"
    except Exception:
        return "API not running (nothing to refresh)"


def main():
    p = argparse.ArgumentParser(description="Generate -> validate -> reproduce -> load MySQL -> docs -> tests")
    p.add_argument("--scale", default="full", choices=["starter", "full"])
    p.add_argument("--seed", type=int, default=20261022)
    p.add_argument("--skip-repro", action="store_true", help="skip the double-generation checksum proof")
    p.add_argument("--skip-tests", action="store_true", help="skip pytest")
    p.add_argument("--serve", action="store_true", help="start the API after the pipeline")
    a = p.parse_args()

    t0 = time.time()
    results = []
    results.append(step(1, "Generate synthetic data",
                        [PY, "-m", "generator.run", "--scale", a.scale, "--seed", str(a.seed)]))
    results.append(step(2, "Validate dataset (80 checks)", [PY, "-m", "scripts.validate"]))
    if not a.skip_repro:
        results.append(step(3, "Reproducibility proof", [PY, "-m", "scripts.reproducibility",
                                                         "--scale", a.scale, "--seed", str(a.seed)]))
    results.append(step(4, "Load into MySQL (schema + data)", [PY, str(ROOT / "database" / "loader" / "load_mysql.py")]))
    results.append(step(5, "Build documentation", [PY, "-m", "scripts.build_docs"], required=False))
    if not a.skip_tests and a.scale == "full":
        results.append(step(6, "Run tests", [PY, "-m", "pytest", "-q"], required=False))
    print(f"\n[7] {refresh_api()}")

    print(f"\n{'=' * 78}\nPIPELINE SUMMARY  (scale={a.scale}, seed={a.seed})\n{'=' * 78}")
    for title, status, secs in results:
        print(f"  {status:<7} {title:<40} {secs:6.1f}s")
    print(f"  Total {time.time() - t0:.1f}s")
    failed = [t for t, s, _ in results if s != "OK"]
    print("\nAll steps OK." if not failed else f"\nNon-blocking failures: {', '.join(failed)}")
    print("Next: start the UI ->  cd ..\\frontend ; npm run dev   (http://localhost:5173)")

    if a.serve:
        if api_running():
            print(f"\nAPI is already running on {API_URL} - reusing it (cache refreshed).")
        else:
            print(f"\nStarting API on {API_URL}  (Ctrl+C to stop)")
            subprocess.call([PY, "-m", "uvicorn", "app.main:app", "--port", "8000"], cwd=BACKEND)


if __name__ == "__main__":
    main()