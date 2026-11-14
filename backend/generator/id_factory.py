"""
Deterministic ID factory - the ONLY place IDs are formatted.

Conventions (from the problem statement):
    SafetyZone        SAFE-<plant-id>-001
    AlarmEvent        ALM-<machine-id>-000001
    Incident          INC-2026-000001
    Acknowledgement   ACK-<alarm-id>-01
    CorrectiveAction  ACT-<incident-id>-01
Counters are zero-padded and IDs are never changed once assigned.
"""
from datetime import date


def plant_id(n: int) -> str:                       # P01
    return f"P{n:02d}"


def machine_id(plant: str, n: int) -> str:         # P01-M001
    return f"{plant}-M{n:03d}"


def zone_id(plant: str, n: int) -> str:            # SAFE-P01-001
    return f"SAFE-{plant}-{n:03d}"


def interlock_id(machine: str, n: int) -> str:     # ILK-P01-M001-01
    return f"ILK-{machine}-{n:02d}"


def alarm_def_id(n: int) -> str:                   # AD-0001
    return f"AD-{n:04d}"


def operator_id(plant: str, n: int) -> str:        # OP-P01-01
    return f"OP-{plant}-{n:02d}"


def engineer_id(plant: str, n: int) -> str:        # QE-P01-01
    return f"QE-{plant}-{n:02d}"


def shift_id(plant: str, shift_date: date, code: str) -> str:   # SHF-P01-20261001-A
    return f"SHF-{plant}-{shift_date.strftime('%Y%m%d')}-{code}"


def machine_state_event_id(machine: str, n: int) -> str:        # MSE-P01-M001-000001
    return f"MSE-{machine}-{n:06d}"


def interlock_event_id(interlock: str, n: int) -> str:          # ISE-ILK-P01-M001-01-0001
    return f"ISE-{interlock}-{n:04d}"


def alarm_event_id(machine: str, n: int) -> str:   # ALM-P01-M001-000001
    return f"ALM-{machine}-{n:06d}"


def ack_id(alarm_id: str, n: int = 1) -> str:      # ACK-ALM-P01-M001-000001-01
    return f"ACK-{alarm_id}-{n:02d}"


def incident_id(n: int, year: int = 2026) -> str:  # INC-2026-000001
    return f"INC-{year}-{n:06d}"


def action_id(incident: str, n: int) -> str:       # ACT-INC-2026-000001-01
    return f"ACT-{incident}-{n:02d}"


def ground_truth_id(n: int) -> str:                # GT-000001
    return f"GT-{n:06d}"