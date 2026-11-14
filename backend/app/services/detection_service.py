"""
Data-quality detectors + evaluation against ground truth.

The 5 detectors use ONLY the operational data (alarms, acks, interlock events, incidents, actions).
Ground truth is read only in evaluate(), to score the detectors (precision / recall / F1).
"""
from datetime import timedelta

from sqlalchemy.orm import Session

from app.repositories import quality_repo
from generator.anomalies import EXPECTED_DECISION
from generator.rules import find_repeated_unsafe

ISSUE_INFO = {
    "ACK_BEFORE_ALARM": ("acknowledgement", "Acknowledgement timestamp earlier than alarm raise (clock skew)"),
    "IMPOSSIBLE_INTERLOCK_STATE": ("interlock_state_event", "Interlock TRIPPED while machine reported RUNNING"),
    "INCIDENT_NO_TRIGGER": ("incident", "Incident has no trigger alarm and no linked alarm context"),
    "REPLAY_DUPLICATE_FLOOD": ("alarm_event", "Alarm re-ingested by replay (same machine/definition/source_seq)"),
    "ACTION_CLOSED_NO_VERIFICATION": ("corrective_action", "Corrective action CLOSED without verification"),
}


def detect_anomalies(ctx) -> dict[str, list[dict]]:
    found = {k: [] for k in ISSUE_INFO}
    for a in ctx.alarms:
        if a["response_sec"] is not None and a["response_sec"] < 0:
            found["ACK_BEFORE_ALARM"].append({"record_id": a["ack_id"], "related_id": a["alarm_event_id"],
                                              "machine_id": a["machine_id"], "event_ts": a["ack_ts"],
                                              "detail": f"ack {a['response_sec']:.1f}s before alarm raise"})
        if a["is_replay"]:
            found["REPLAY_DUPLICATE_FLOOD"].append({"record_id": a["alarm_event_id"], "related_id": a["replay_of"],
                                                    "machine_id": a["machine_id"], "event_ts": a["raised_ts"],
                                                    "detail": f"duplicate of {a['replay_of']} received "
                                                              f"{(a['received_ts'] - a['raised_ts']).total_seconds() / 3600:.1f} h late"})
    for e in ctx.ilk_events:
        if e["to_state"] == "TRIPPED" and e["machine_state_snapshot"] == "RUNNING":
            found["IMPOSSIBLE_INTERLOCK_STATE"].append({
                "record_id": e["interlock_event_id"], "related_id": e["interlock_id"], "machine_id": e["machine_id"],
                "event_ts": e["event_ts"], "detail": f"{e['interlock_type']} TRIPPED but machine RUNNING"})
    for i in ctx.incidents:
        if not i["trigger_alarm_id"] and i["linked_alarms"] == 0:
            found["INCIDENT_NO_TRIGGER"].append({"record_id": i["incident_id"], "related_id": None,
                                                 "machine_id": i["machine_id"], "event_ts": i["opened_ts"],
                                                 "detail": f"{i['rule_code']} without trigger/context"})
    inc_machine = {i["incident_id"]: i["machine_id"] for i in ctx.incidents}
    for a in ctx.actions:
        if a["status"] == "CLOSED" and (a["verified_ts"] is None or a["verified_by"] is None):
            found["ACTION_CLOSED_NO_VERIFICATION"].append({
                "record_id": a["action_id"], "related_id": a["incident_id"],
                "machine_id": inc_machine.get(a["incident_id"]), "event_ts": a["closed_ts"],
                "detail": "closed without verified_ts / verified_by"})
    return found


def anomaly_summary(ctx) -> dict:
    found = detect_anomalies(ctx)
    return {
        "issues": [{"issue_type": k, "record_type": ISSUE_INFO[k][0], "description": ISSUE_INFO[k][1],
                    "detected": len(v), "expected_decision": EXPECTED_DECISION[k],
                    "items": sorted(v, key=lambda x: x["record_id"])} for k, v in found.items()],
        "total_detected": sum(len(v) for v in found.values()),
    }


def _score(detected: set, truth: set) -> dict:
    tp = len(detected & truth)
    fp = len(detected - truth)
    fn = len(truth - detected)
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(p, 3), "recall": round(r, 3), "f1": round(f1, 3)}


def evaluate(ctx, db: Session) -> dict:
    gt = quality_repo.ground_truth(db)
    truth = {}
    for g in gt:
        truth.setdefault(g["issue_type"], []).append(g)
    rows = []
    found = detect_anomalies(ctx)
    for issue, items in found.items():
        rows.append({"issue_type": issue, "category": "ANOMALY", "labelled": len(truth.get(issue, [])),
                     "detected": len(items),
                     **_score({x["record_id"] for x in items}, {g["record_id"] for g in truth.get(issue, [])})})

    # pattern: alarm floods (episode matches if same plant and time windows overlap)
    gt_floods = [(g["record_id"], g["event_ts"], g["event_ts"] + timedelta(minutes=10)) for g in truth.get("ALARM_FLOOD", [])]
    det = ctx.floods
    tp_det = sum(1 for e in det if any(p == e["plant_id"] and s <= e["end_ts"] and e["start_ts"] <= t for p, s, t in gt_floods))
    tp_gt = sum(1 for p, s, t in gt_floods if any(p == e["plant_id"] and s <= e["end_ts"] and e["start_ts"] <= t for e in det))
    prec = tp_det / len(det) if det else 1.0
    rec = tp_gt / len(gt_floods) if gt_floods else 1.0
    rows.append({"issue_type": "ALARM_FLOOD", "category": "PATTERN", "labelled": len(gt_floods), "detected": len(det),
                 "tp": tp_gt, "fp": len(det) - tp_det, "fn": len(gt_floods) - tp_gt, "precision": round(prec, 3),
                 "recall": round(rec, 3), "f1": round(2 * prec * rec / (prec + rec), 3) if prec + rec else 0.0})

    # pattern: nuisance alarms (machine, definition) pairs
    det_n = {(p["alarm_def_id"], p["machine_id"]) for p in ctx.chatter_pairs if p["is_nuisance"]}
    gt_n = {(g["record_id"], g["related_id"]) for g in truth.get("NUISANCE_ALARM", [])}
    rows.append({"issue_type": "NUISANCE_ALARM", "category": "PATTERN", "labelled": len(gt_n),
                 "detected": len(det_n), **_score(det_n, gt_n)})

    # pattern: repeated unsafe conditions (machine, rule) pairs - incidents without context excluded
    clean = [i for i in ctx.incidents if i["trigger_alarm_id"] or i["linked_alarms"] > 0]
    det_r = {(r["machine_id"], r["rule_code"]) for r in find_repeated_unsafe(clean)}
    gt_r = {(g["record_id"], g["related_id"]) for g in truth.get("REPEATED_UNSAFE_CONDITION", [])}
    rows.append({"issue_type": "REPEATED_UNSAFE_CONDITION", "category": "PATTERN", "labelled": len(gt_r),
                 "detected": len(det_r), **_score(det_r, gt_r)})

    anomalies = [r for r in rows if r["category"] == "ANOMALY"]
    return {
        "note": "Detectors never read ground_truth; it is used here only to score them.",
        "macro_f1_anomalies": round(sum(r["f1"] for r in anomalies) / len(anomalies), 3),
        "macro_f1_all": round(sum(r["f1"] for r in rows) / len(rows), 3),
        "items": rows,
    }