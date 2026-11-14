"""Ground-truth queries. ONLY used by the evaluation service - never by detectors."""
from sqlalchemy import text
from sqlalchemy.orm import Session


def ground_truth(db: Session) -> list[dict]:
    sql = """SELECT gt_id, category, issue_type, record_type, record_id, related_id, event_ts, detail,
                    expected_decision FROM ground_truth ORDER BY gt_id"""
    return [dict(r) for r in db.execute(text(sql)).mappings()]