# REST API

Base URL: `http://localhost:8000` · Interactive docs (Swagger): `http://localhost:8000/docs`

All errors use one JSON shape: `{"error": {"code", "message", "path", "details"}}` with codes `BAD_REQUEST` (400), `NOT_FOUND` (404), `VALIDATION_ERROR` (422), `DATABASE_UNAVAILABLE` (503), `INTERNAL_ERROR` (500).

| Method | Path | Description | Query / path parameters |
|---|---|---|---|
| GET | `/api/alarms` | Alarm explorer - default sort = priority score (severe alarms first). | `plant`, `machine`, `severity` (CRITICAL/HIGH/MEDIUM/LOW), `category` (SAFETY/PROCESS/EQUIPMENT/SYSTEM), `ack_status` (ON_TIME/DELAYED/UNACKED/INVALID), `flood_only`, `include_replays`, `search`, `date_from`, `date_to`, `sort`, `page`, `size` |
| GET | `/api/analytics/floods` | Alarm-flood episodes (> 10 alarms / 10 min / plant). | - |
| GET | `/api/analytics/nuisance` | Chattering / fleeting bad-actor alarms (nuisance clusters). | `limit` |
| GET | `/api/analytics/repeated-unsafe` | Repeated unsafe conditions: same machine + rule >= 3 times in 7 days. | - |
| GET | `/api/dashboard/kpis` | Overview KPIs (replay duplicates excluded). | - |
| GET | `/api/health` | Health | - |
| GET | `/api/incidents` | List Incidents | `plant`, `machine`, `rule` (R1_BYPASS_CRITICAL/R2_GUARD_TRIP_ESTOP/R3_CRITICAL_UNACKED/MANUAL_REPORT), `status` (OPEN/INVESTIGATING/ACTION_PENDING/CLOSED), `severity` (CRITICAL/HIGH/MEDIUM/LOW) |
| GET | `/api/incidents/{incident_id}/trace` | Ordered timeline: machine states, interlocks, alarms, acknowledgements, corrective actions. | `incident_id` |
| GET | `/api/master/alarm-definitions` | Alarm Definitions | - |
| GET | `/api/master/machines` | Machines | `plant` |
| GET | `/api/master/plants` | Plants | - |
| GET | `/api/master/zones` | Zones | - |
| GET | `/api/meta/checklist` | Checklist | - |
| GET | `/api/meta/data-dictionary` | Data Dictionary | - |
| GET | `/api/meta/db-counts` | Live row counts in MySQL (proves the data is loaded in Tier 3). | - |
| GET | `/api/meta/manifest` | Manifest | - |
| POST | `/api/meta/refresh` | Drop the in-memory analytics cache (after re-loading the database). | - |
| GET | `/api/meta/reproducibility` | Reproducibility | - |
| GET | `/api/meta/rules` | Rules | - |
| GET | `/api/meta/validation` | Validation | - |
| GET | `/api/quality/anomalies` | The 5 edge cases found by the detectors (ground truth NOT used). | - |
| GET | `/api/quality/evaluation` | Detector results scored against ground_truth: precision / recall / F1. | - |
