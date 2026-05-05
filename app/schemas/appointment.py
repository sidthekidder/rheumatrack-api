import uuid
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict


class AppointmentCreate(BaseModel):
    appointment_date: date
    appointment_time: str | None = None
    doctor_name: str
    clinic: str | None = None
    visit_type: str = "Routine Follow-up"
    pre_notes: str | None = None
    post_notes: str | None = None
    completed: bool = False


class AppointmentUpdate(BaseModel):
    appointment_date: date | None = None
    appointment_time: str | None = None
    doctor_name: str | None = None
    clinic: str | None = None
    visit_type: str | None = None
    pre_notes: str | None = None
    post_notes: str | None = None
    completed: bool | None = None


class AppointmentResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    appointment_date: date
    appointment_time: str | None
    doctor_name: str
    clinic: str | None
    visit_type: str
    pre_notes: str | None
    post_notes: str | None
    completed: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
