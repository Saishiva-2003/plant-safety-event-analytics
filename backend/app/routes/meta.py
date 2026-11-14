from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import master_repo
from app.services import detection_service, meta_service
from app.services.context import get_context, reset_context
from generator.exporter import TABLES

router = APIRouter(prefix="/api/meta", tags=["proof & documentation"])


def _need(data, name):
    if data is None:
        raise HTTPException(404, f"{name} not found - run the generator / validator / reproducibility scripts")
    return data


@router.get("/manifest")
def manifest():
    return _need(meta_service.manifest(), "manifest.json")


@router.get("/validation")
def validation():
    return _need(meta_service.validation(), "validation_summary.json")


@router.get("/reproducibility")
def reproducibility():
    return _need(meta_service.reproducibility(), "repro_report.json")


@router.get("/data-dictionary")
def data_dictionary():
    return meta_service.data_dictionary()


@router.get("/rules")
def rules():
    return meta_service.business_rules()


@router.get("/checklist")
def checklist(db: Session = Depends(get_db)):
    ctx = get_context(db)
    counts = master_repo.table_counts(db, list(TABLES))
    return meta_service.checklist(ctx, detection_service.evaluate(ctx, db), counts)


@router.get("/db-counts")
def db_counts(db: Session = Depends(get_db)):
    """Live row counts in MySQL (proves the data is loaded in Tier 3)."""
    return master_repo.table_counts(db, list(TABLES) + ["ground_truth"])


@router.post("/refresh")
def refresh():
    """Drop the in-memory analytics cache (after re-loading the database)."""
    reset_context()
    return {"message": "analytics context will be rebuilt on next request"}