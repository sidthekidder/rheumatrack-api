import uuid
from datetime import datetime, date
from typing import Literal
from pydantic import BaseModel, ConfigDict


Slot = Literal["morning", "afternoon", "evening", "night"]


class MedicationLogUpsert(BaseModel):
    medicine_id: uuid.UUID
    log_date: date
    slot: Slot
    taken: bool


class MedicationLogResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    medicine_id: uuid.UUID
    log_date: date
    slot: str
    taken: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
