from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dto.quality_dto import EvaluationDTO
from app.services import detection_service
from app.services.context import get_context

router = APIRouter(prefix="/api/quality", tags=["data quality"])


@router.get("/anomalies")
def anomalies(db: Session = Depends(get_db)):
    """The 5 edge cases found by the detectors (ground truth NOT used)."""
    return detection_service.anomaly_summary(get_context(db))


@router.get("/evaluation", response_model=EvaluationDTO)
def evaluation(db: Session = Depends(get_db)):
    """Detector results scored against ground_truth: precision / recall / F1."""
    return detection_service.evaluate(get_context(db), db)