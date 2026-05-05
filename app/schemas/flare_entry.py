import uuid
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict, Field


class FlareEntryUpsert(BaseModel):
    entry_date: date
    pain: int = Field(ge=0, le=10, default=0)
    stiffness_min: int = Field(ge=0, le=600, default=0)
    fatigue: int = Field(ge=0, le=10, default=0)
    joints: list[str] = Field(default_factory=list)
    notes: str | None = None


class FlareEntryResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    entry_date: date
    pain: int
    stiffness_min: int
    fatigue: int
    joints: list[str]
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
