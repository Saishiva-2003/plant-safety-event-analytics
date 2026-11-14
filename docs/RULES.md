# Business Rules

Single source of truth: `backend/generator/rules.py`. The **same rules generate the data and analyse it**, so outcomes and labels are derived from documented rules - never assigned at random.

## 1. Severity, priority weight and acknowledgement SLA

| Severity | Priority weight | Ack SLA (s) |
|---|---|---|
| CRITICAL | 100 | 60 |
| HIGH | 50 | 300 |
| MEDIUM | 20 | 900 |
| LOW | 5 | 1800 |

**Priority score** = `severity_weight x zone_hazard_level x interlock_factor + 2 x repeats_in_24h`  
Interlock factor: BYPASSED ×2.0, TRIPPED ×1.5, ENGAGED ×1.0.  
A delayed acknowledgement is `response_sec > ack SLA`; `response_sec = ack_ts − raised_ts` (derived).

## 2. Incident rules (incidents are derived from the data)

| Rule | Condition | Severity |
|---|---|---|
| `R1_BYPASS_CRITICAL` | CRITICAL safety alarm raised while an interlock is BYPASSED and machine is RUNNING | CRITICAL |
| `R2_GUARD_TRIP_ESTOP` | Guard door / light curtain alarm while RUNNING followed by E_STOP within 60 s | HIGH |
| `R3_CRITICAL_UNACKED` | CRITICAL alarm not acknowledged within 300 s | CRITICAL |
| `MANUAL_REPORT` | Near-miss reported by an operator (linked to context alarms) | from alarm |

**Repeated unsafe condition:** the same machine and the same rule at least 3 times within a rolling 7 days.

## 3. Alarm management (ISA-18.2 inspired)

* **Alarm flood:** > 10 alarms within 10 minutes per plant (replay duplicates and chattering alarms excluded first).
* **Chattering:** ≥ 3 activations of the same alarm on the same machine within 60 s = one chatter episode.
* **Nuisance alarm (bad actor):** ≥ 5 chatter episodes.
* **Fleeting alarm:** cleared within 5 s.
* **Replay duplicate:** same `(machine_id, alarm_def_id, source_seq)` - the later-received copy is the replay.

## 4. State machines and lifecycles

**Machine**

| From | Allowed next states |
|---|---|
| OFF | STARTING |
| STARTING | FAULTED, RUNNING |
| RUNNING | E_STOP, FAULTED, IDLE, OFF |
| IDLE | E_STOP, FAULTED, OFF, RUNNING |
| FAULTED | MAINTENANCE |
| E_STOP | OFF |
| MAINTENANCE | OFF |

**Interlock**

| From | Allowed next states |
|---|---|
| ENGAGED | BYPASSED, TRIPPED |
| TRIPPED | ENGAGED |
| BYPASSED | ENGAGED |

A TRIPPED interlock must stop the machine: an interlock trip recorded while the machine is RUNNING is an *impossible state*.

**Incident lifecycle:** OPEN → INVESTIGATING → ACTION_PENDING → CLOSED (status derived from its corrective actions)  
**Corrective-action lifecycle:** OPEN → IN_PROGRESS → PENDING_VERIFICATION → VERIFIED → CLOSED (an action may only be CLOSED after it is VERIFIED)

**Shifts:** A 06:00-14:00, B 14:00-22:00, C 22:00-06:00

## 5. Labelled edge cases and expected decisions

| Issue / pattern | Expected decision |
|---|---|
| `ACK_BEFORE_ALARM` | `REJECT_ACK_FLAG_CLOCK_SKEW` |
| `IMPOSSIBLE_INTERLOCK_STATE` | `FLAG_SENSOR_FAULT_QUARANTINE` |
| `INCIDENT_NO_TRIGGER` | `REQUIRE_CONTEXT_BEFORE_CLOSURE` |
| `REPLAY_DUPLICATE_FLOOD` | `DEDUPLICATE_EXCLUDE_FROM_KPIS` |
| `ACTION_CLOSED_NO_VERIFICATION` | `REOPEN_ACTION_REQUIRE_VERIFICATION` |
| `ALARM_FLOOD` | `SUPPRESS_LOW_PRIORITY_DURING_FLOOD` |
| `NUISANCE_ALARM` | `REVIEW_SETPOINT_DEADBAND` |
| `REPEATED_UNSAFE_CONDITION` | `ESCALATE_ROOT_CAUSE_REVIEW` |

## 6. Generator

* Seed: `20261022`
* Command: `python -m generator.run --scale full --seed 20261022`

| Scale | Plants | Machines | Alarm definitions | Alarm events | Days |
|---|---|---|---|---|---|
| starter | 1 | 6 | 60 | 3000 | 30 |
| full | 4 | 60 | 200 | 50000 | 30 |
