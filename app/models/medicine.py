import uuid
from datetime import datetime, date
from sqlalchemy import String, Integer, DateTime, Date, ForeignKey, func, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class Medicine(Base):
    __tablename__ = "medicines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    drug_name: Mapped[str] = mapped_column(String, nullable=False)
    brand_name: Mapped[str] = mapped_column(String, nullable=False)
    dose: Mapped[str] = mapped_column(String, nullable=False)
    schedule_type: Mapped[str] = mapped_column(String, nullable=False)
    dose_schedule: Mapped[dict] = mapped_column(JSONB, nullable=False)
    week_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exclude_days: Mapped[list[int] | None] = mapped_column(
        ARRAY(Integer), nullable=True, server_default="{}"
    )
    tapering_phases: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    food_timing_id: Mapped[str | None] = mapped_column(String, nullable=True)
    food_timing_label: Mapped[str | None] = mapped_column(String, nullable=True)
    reminder_time: Mapped[str | None] = mapped_column(String, nullable=True)
    route: Mapped[str | None] = mapped_column(String, nullable=True)
    tip: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    color: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
