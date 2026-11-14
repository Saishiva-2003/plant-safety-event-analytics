"""Data-quality / evaluation DTOs."""
from pydantic import BaseModel


class EvaluationRowDTO(BaseModel):
    issue_type: str
    category: str
    labelled: int
    detected: int
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float


class EvaluationDTO(BaseModel):
    note: str
    macro_f1_anomalies: float
    macro_f1_all: float
    items: list[EvaluationRowDTO]