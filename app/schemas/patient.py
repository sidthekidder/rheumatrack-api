import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PatientCreate(BaseModel):
    name: str
    age: int | None = None
    patient_id: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    doctor_name: str | None = None
    doctor_specialty: str | None = None
    doctor_phone: str | None = None
    doctor_hospital: str | None = None
    diagnosis: str | None = None
    theme: str | None = None
    doctor_website_url: str | None = None
    doctor_instagram_url: str | None = None
    doctor_youtube_url: str | None = None
    language: str | None = None


class PatientUpdate(BaseModel):
    name: str | None = None
    age: int | None = None
    patient_id: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    doctor_name: str | None = None
    doctor_specialty: str | None = None
    doctor_phone: str | None = None
    doctor_hospital: str | None = None
    diagnosis: str | None = None
    theme: str | None = None
    doctor_website_url: str | None = None
    doctor_instagram_url: str | None = None
    doctor_youtube_url: str | None = None
    language: str | None = None


class PatientResponse(BaseModel):
    id: uuid.UUID
    name: str
    age: int | None
    patient_id: str | None
    city: str | None
    state: str | None
    country: str | None
    doctor_name: str | None
    doctor_specialty: str | None
    doctor_phone: str | None
    doctor_hospital: str | None
    diagnosis: str | None
    theme: str | None
    doctor_website_url: str | None
    doctor_instagram_url: str | None
    doctor_youtube_url: str | None
    language: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
