# Entity-Relationship Diagram

Generated from the foreign keys in `database/schema/schema.sql`. GitHub renders the Mermaid diagram below.

* `||--o{` one-to-many · `||--o|` one-to-zero-or-one · `|o--o{` optional parent
* Many-to-many relationships use bridge tables: **machine_zone** (machine ↔ safety_zone) and **incident_alarm** (incident ↔ alarm_event, role TRIGGER / CONTEXT)
* History tables (`machine_state_event`, `interlock_state_event`) are append-only - state is never overwritten

```mermaid
erDiagram
    plant ||--o{ safety_zone : "plant_id"
    plant ||--o{ machine : "plant_id"
    machine ||--o{ machine_zone : "machine_id"
    safety_zone ||--o{ machine_zone : "zone_id"
    machine ||--o{ interlock : "machine_id"
    safety_zone ||--o{ interlock : "zone_id"
    plant ||--o{ staff : "plant_id"
    plant ||--o{ operator_shift : "plant_id"
    staff ||--o{ operator_shift : "operator_id"
    machine ||--o{ machine_state_event : "machine_id"
    interlock ||--o{ interlock_state_event : "interlock_id"
    machine ||--o{ alarm_event : "machine_id"
    alarm_definition ||--o{ alarm_event : "alarm_def_id"
    operator_shift ||--o{ alarm_event : "shift_id"
    interlock |o--o{ alarm_event : "interlock_id"
    alarm_event ||--o| acknowledgement : "alarm_event_id"
    operator_shift ||--o{ acknowledgement : "shift_id"
    staff ||--o{ acknowledgement : "operator_id"
    machine ||--o{ incident : "machine_id"
    safety_zone ||--o{ incident : "zone_id"
    alarm_event |o--o{ incident : "trigger_alarm_id"
    incident ||--o{ incident_alarm : "incident_id"
    alarm_event ||--o{ incident_alarm : "alarm_event_id"
    incident ||--o{ corrective_action : "incident_id"
    staff ||--o{ corrective_action : "owner_id"
    staff |o--o{ corrective_action : "verified_by"
    plant {
        VARCHAR plant_id PK
        VARCHAR plant_name
        VARCHAR city
        VARCHAR state
        CHAR country
        VARCHAR timezone
        VARCHAR status
        DATE opened_date
    }
    safety_zone {
        VARCHAR zone_id PK
        VARCHAR plant_id FK
        VARCHAR zone_name
        VARCHAR zone_type
        TINYINT hazard_level
        DATE effective_from
        DATE effective_to
        VARCHAR status
    }
    machine {
        VARCHAR machine_id PK
        VARCHAR plant_id FK
        VARCHAR machine_name
        VARCHAR machine_type
        VARCHAR manufacturer
        CHAR criticality
        DATE commissioned_date
        VARCHAR status
    }
    machine_zone {
        VARCHAR machine_id PK,FK
        VARCHAR zone_id PK,FK
        TINYINT is_primary
        DATE effective_from
        DATE effective_to
    }
    interlock {
        VARCHAR interlock_id PK
        VARCHAR machine_id FK
        VARCHAR zone_id FK
        VARCHAR interlock_type
        VARCHAR description
        TINYINT sil_level
        VARCHAR initial_state
        DATE installed_date
        VARCHAR status
    }
    alarm_definition {
        VARCHAR alarm_def_id PK
        VARCHAR alarm_code UK
        VARCHAR base_code
        VARCHAR alarm_name
        VARCHAR category
        VARCHAR severity
        VARCHAR machine_type
        VARCHAR interlock_type
        TINYINT ack_required
        INT ack_sla_sec
        DATE effective_from
        VARCHAR status
    }
    staff {
        VARCHAR staff_id PK
        VARCHAR plant_id FK
        VARCHAR role
        VARCHAR display_name
    }
    operator_shift {
        VARCHAR shift_id PK
        VARCHAR plant_id FK
        CHAR shift_code
        DATE shift_date
        DATETIME start_ts
        DATETIME end_ts
        VARCHAR operator_id FK
    }
    machine_state_event {
        VARCHAR state_event_id PK
        VARCHAR machine_id FK
        DATETIME event_ts
        VARCHAR from_state
        VARCHAR to_state
        VARCHAR reason
    }
    interlock_state_event {
        VARCHAR interlock_event_id PK
        VARCHAR interlock_id FK
        DATETIME event_ts
        VARCHAR from_state
        VARCHAR to_state
        VARCHAR machine_state_snapshot
        VARCHAR reason
        VARCHAR actor
    }
    alarm_event {
        VARCHAR alarm_event_id PK
        VARCHAR machine_id FK
        VARCHAR alarm_def_id FK
        VARCHAR shift_id FK
        VARCHAR interlock_id FK
        DATETIME raised_ts
        DATETIME cleared_ts
        DATETIME received_ts
        INT source_seq
        VARCHAR machine_state
    }
    acknowledgement {
        VARCHAR ack_id PK
        VARCHAR alarm_event_id FK,UK
        VARCHAR shift_id FK
        VARCHAR operator_id FK
        DATETIME ack_ts
        DECIMAL response_sec
        VARCHAR ack_method
    }
    incident {
        VARCHAR incident_id PK
        VARCHAR machine_id FK
        VARCHAR zone_id FK
        VARCHAR trigger_alarm_id FK
        VARCHAR rule_code
        VARCHAR severity
        DATETIME opened_ts
        VARCHAR status
        DATETIME closed_ts
        VARCHAR reported_by
        VARCHAR description
    }
    incident_alarm {
        VARCHAR incident_id PK,FK
        VARCHAR alarm_event_id PK,FK
        VARCHAR link_role
    }
    corrective_action {
        VARCHAR action_id PK
        VARCHAR incident_id FK
        VARCHAR action_type
        VARCHAR description
        VARCHAR owner_id FK
        DATETIME created_ts
        DATETIME due_ts
        VARCHAR status
        DATETIME started_ts
        DATETIME completed_ts
        DATETIME verified_ts
        VARCHAR verified_by FK
        DATETIME closed_ts
    }
    ground_truth {
        VARCHAR gt_id PK
        VARCHAR category
        VARCHAR issue_type
        VARCHAR record_type
        VARCHAR record_id
        VARCHAR related_id
        DATETIME event_ts
        VARCHAR detail
        VARCHAR expected_decision
    }
```

## Cardinality summary

| Parent | Cardinality | Child | Via |
|---|---|---|---|
| `plant` | **1:N** | `safety_zone` | `safety_zone.plant_id` |
| `plant` | **1:N** | `machine` | `machine.plant_id` |
| `machine` | **N:M** | `safety_zone` | `bridge machine_zone` |
| `machine` | **1:N** | `interlock` | `interlock.machine_id` |
| `safety_zone` | **1:N** | `interlock` | `interlock.zone_id` |
| `plant` | **1:N** | `staff` | `staff.plant_id` |
| `plant` | **1:N** | `operator_shift` | `operator_shift.plant_id` |
| `staff` | **1:N** | `operator_shift` | `operator_shift.operator_id` |
| `machine` | **1:N** | `machine_state_event` | `machine_state_event.machine_id` |
| `interlock` | **1:N** | `interlock_state_event` | `interlock_state_event.interlock_id` |
| `machine` | **1:N** | `alarm_event` | `alarm_event.machine_id` |
| `alarm_definition` | **1:N** | `alarm_event` | `alarm_event.alarm_def_id` |
| `operator_shift` | **1:N** | `alarm_event` | `alarm_event.shift_id` |
| `interlock` | **1:N (optional)** | `alarm_event` | `alarm_event.interlock_id` |
| `alarm_event` | **1:0..1** | `acknowledgement` | `acknowledgement.alarm_event_id (UNIQUE)` |
| `staff` | **1:N** | `acknowledgement` | `acknowledgement.operator_id` |
| `machine` | **1:N** | `incident` | `incident.machine_id` |
| `alarm_event` | **1:0..N (trigger, optional)** | `incident` | `incident.trigger_alarm_id` |
| `incident` | **N:M** | `alarm_event` | `bridge incident_alarm (TRIGGER / CONTEXT)` |
| `incident` | **1:N** | `corrective_action` | `corrective_action.incident_id` |
| `staff` | **1:N (owner, verifier)** | `corrective_action` | `corrective_action.owner_id / verified_by` |
