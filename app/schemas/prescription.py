import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PrescriptionResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    storage_path: str | None
    mime_type: str
    scanned_at: datetime
    raw_response: dict | None

    model_config = ConfigDict(from_attributes=True)


class ScanResponse(BaseModel):
    prescription_id: uuid.UUID
    parsed: dict
