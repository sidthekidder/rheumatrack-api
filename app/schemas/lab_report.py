import uuid
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict


class LabResult(BaseModel):
    test_id: str
    value: str


class LabReportCreate(BaseModel):
    report_date: date
    results: list[LabResult]
    source: str = "manual"
    notes: str | None = None


class LabReportResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    report_date: date
    results: list[dict]
    source: str
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
