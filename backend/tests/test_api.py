"""API tests (need MySQL loaded: python ../database/loader/load_mysql.py)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_50000_alarms():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["alarm_events"] == 50000


def test_dashboard_kpis_exclude_replays():
    t = client.get("/api/dashboard/kpis").json()["totals"]
    assert t["plants"] == 4 and t["machines"] == 60
    assert t["alarm_events_raw"] == 50000
    assert t["replay_duplicates_removed"] == 500


def test_alarms_sorted_by_priority_severe_first():
    items = client.get("/api/alarms?size=20").json()["items"]
    scores = [a["priority_score"] for a in items]
    assert scores == sorted(scores, reverse=True)
    assert items[0]["severity"] == "CRITICAL"


def test_alarm_filters():
    r = client.get("/api/alarms?severity=LOW&plant=P02&size=5").json()
    assert r["total"] > 0 and all(a["severity"] == "LOW" and a["plant_id"] == "P02" for a in r["items"])


def test_floods_and_nuisance_detected():
    f = client.get("/api/analytics/floods").json()
    n = client.get("/api/analytics/nuisance").json()
    assert f["episodes"] >= 40
    assert n["nuisance_pairs"] >= 15


def test_repeated_unsafe_conditions_found():
    r = client.get("/api/analytics/repeated-unsafe").json()
    assert r["conditions"] > 0 and r["items"][0]["max_count_in_window"] >= 3


def test_incident_trace_has_states_alarms_and_actions():
    inc = client.get("/api/incidents?rule=R1_BYPASS_CRITICAL").json()["items"][0]
    tr = client.get(f"/api/incidents/{inc['incident_id']}/trace").json()
    types = {e["type"] for e in tr["timeline"]}
    assert {"STATE", "INTERLOCK", "ALARM", "INCIDENT"} <= types
    assert tr["traceable"] is True


def test_trace_404():
    assert client.get("/api/incidents/INC-2026-999999/trace").status_code == 404


def test_detectors_match_ground_truth_exactly():
    ev = client.get("/api/quality/evaluation").json()
    anomalies = [r for r in ev["items"] if r["category"] == "ANOMALY"]
    assert len(anomalies) == 5
    assert all(r["f1"] == 1.0 for r in anomalies)


def test_meta_endpoints():
    assert client.get("/api/meta/data-dictionary").json()["tables"]
    assert client.get("/api/meta/rules").json()["incident_rules"]
    c = client.get("/api/meta/checklist").json()
    assert c["done"] == c["total"]


# ------------------------- exception handling -------------------------
def test_invalid_enum_returns_422_with_standard_shape():
    r = client.get("/api/alarms?severity=EXTREME")
    assert r.status_code == 422
    body = r.json()["error"]
    assert body["code"] == "VALIDATION_ERROR" and body["details"][0]["field"] == "severity"


def test_bad_date_range_returns_400():
    r = client.get("/api/alarms?date_from=2026-10-20&date_to=2026-10-01")
    assert r.status_code == 400 and r.json()["error"]["code"] == "BAD_REQUEST"


def test_bad_incident_id_format_returns_422():
    assert client.get("/api/incidents/abc/trace").status_code == 422


def test_unknown_route_returns_404_json():
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"


def test_page_size_limit_returns_422():
    assert client.get("/api/alarms?size=10000").status_code == 422