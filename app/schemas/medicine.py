import uuid
from datetime import datetime, date
from typing import Literal
from pydantic import BaseModel, ConfigDict


class DoseSchedule(BaseModel):
    morning: float = 0
    afternoon: float = 0
    evening: float = 0
    night: float = 0


class TaperingPhase(BaseModel):
    days: int
    dose_schedule: DoseSchedule


ScheduleType = Literal["daily", "weekly", "alternate", "tapering"]


class MedicineCreate(BaseModel):
    drug_name: str
    brand_name: str
    dose: str
    schedule_type: ScheduleType
    dose_schedule: DoseSchedule
    week_day: int | None = None
    exclude_days: list[int] | None = None
    tapering_phases: list[TaperingPhase] | None = None
    start_date: date
    duration_days: int | None = None
    food_timing_id: str | None = None
    food_timing_label: str | None = None
    reminder_time: str | None = None
    route: str | None = None
    tip: str | None = None
    notes: str | None = None
    color: str | None = None


class MedicineUpdate(BaseModel):
    drug_name: str | None = None
    brand_name: str | None = None
    dose: str | None = None
    schedule_type: ScheduleType | None = None
    dose_schedule: DoseSchedule | None = None
    week_day: int | None = None
    exclude_days: list[int] | None = None
    tapering_phases: list[TaperingPhase] | None = None
    start_date: date | None = None
    duration_days: int | None = None
    food_timing_id: str | None = None
    food_timing_label: str | None = None
    reminder_time: str | None = None
    route: str | None = None
    tip: str | None = None
    notes: str | None = None
    color: str | None = None


class MedicineResponse(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    drug_name: str
    brand_name: str
    dose: str
    schedule_type: str
    dose_schedule: DoseSchedule
    week_day: int | None
    exclude_days: list[int] | None
    tapering_phases: list[TaperingPhase] | None
    start_date: date
    duration_days: int | None
    food_timing_id: str | None
    food_timing_label: str | None
    reminder_time: str | None
    route: str | None
    tip: str | None
    notes: str | None
    color: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
