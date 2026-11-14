"""
Generator configuration: fixed seed, simulation window and scale presets.

The SAME generator code produces both datasets - only the preset changes:
    starter -> small, fast (tests / demos)
    full    -> 4 plants, 60 machines, 200 alarm definitions, 50,000 alarm events
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

GENERATOR_VERSION = "1.0.0"
DEFAULT_SEED = 20261022

# Simulation window: 30 days starting 1-Oct-2026 00:00 (plant local time, IST)
START_TS = datetime(2026, 10, 1, 0, 0, 0)

# Default output = Tier-3 database folder  (backend/generator/config.py -> parents[2] = project root)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "database"


@dataclass(frozen=True)
class ScaleConfig:
    name: str
    plants: int
    machines: int
    alarm_definitions: int
    alarm_events: int            # TOTAL alarm events incl. injected replay duplicates
    days: int
    zones_per_plant: int
    operators_per_plant: int
    engineers_per_plant: int
    problem_machines: int        # machines with elevated unsafe behaviour (repeat offenders)
    flood_share: float           # share of alarm events that belong to alarm floods
    chatter_share: float         # share of alarm events that are chattering / nuisance alarms
    bad_actor_pairs: int         # (machine, alarm definition) pairs that chatter
    manual_reports: int          # operator near-miss reports (incidents with context, no trigger)
    # ---- labelled edge cases (Step 5) ----
    n_ack_before_alarm: int
    n_impossible_interlock: int
    n_incident_no_trigger: int
    n_replay_rows: int
    n_action_no_verification: int

    @property
    def start_ts(self) -> datetime:
        return START_TS

    @property
    def end_ts(self) -> datetime:
        return START_TS + timedelta(days=self.days)


SCALES = {
    "starter": ScaleConfig(
        name="starter", plants=1, machines=6, alarm_definitions=60, alarm_events=3000,
        days=30, zones_per_plant=4, operators_per_plant=6, engineers_per_plant=2,
        problem_machines=1, flood_share=0.16, chatter_share=0.06, bad_actor_pairs=3,
        manual_reports=3,
        n_ack_before_alarm=5, n_impossible_interlock=3, n_incident_no_trigger=2,
        n_replay_rows=60, n_action_no_verification=2,
    ),
    "full": ScaleConfig(
        name="full", plants=4, machines=60, alarm_definitions=200, alarm_events=50000,
        days=30, zones_per_plant=5, operators_per_plant=8, engineers_per_plant=3,
        problem_machines=5, flood_share=0.16, chatter_share=0.06, bad_actor_pairs=20,
        manual_reports=15,
        n_ack_before_alarm=50, n_impossible_interlock=30, n_incident_no_trigger=10,
        n_replay_rows=500, n_action_no_verification=15,
    ),
}


def get_scale(name: str) -> ScaleConfig:
    if name not in SCALES:
        raise ValueError(f"Unknown scale '{name}'. Choose one of: {', '.join(SCALES)}")
    return SCALES[name]


# ---------------------------------------------------------------------------
# Timestamp helpers (millisecond precision, deterministic string format)
# ---------------------------------------------------------------------------
def add_seconds(ts: datetime, seconds: float) -> datetime:
    """Add seconds, rounded to whole milliseconds (keeps output deterministic)."""
    return ts + timedelta(milliseconds=round(seconds * 1000))


def fmt_ts(ts) -> str:
    """'2026-10-01 06:00:00.000'  (None -> '')."""
    if ts is None:
        return ""
    return ts.strftime("%Y-%m-%d %H:%M:%S.") + f"{ts.microsecond // 1000:03d}"