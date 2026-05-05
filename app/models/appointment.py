import uuid
from datetime import datetime, date
from sqlalchemy import String, Boolean, DateTime, Date, ForeignKey, Index, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index("ix_appt_patient_date", "patient_id", "appointment_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False)
    appointment_time: Mapped[str | None] = mapped_column(String, nullable=True)
    doctor_name: Mapped[str] = mapped_column(String, nullable=False)
    clinic: Mapped[str | None] = mapped_column(String, nullable=True)
    visit_type: Mapped[str] = mapped_column(
        String, nullable=False, server_default="Routine Follow-up"
    )
    pre_notes: Mapped[str | None] = mapped_column(String, nullable=True)
    post_notes: Mapped[str | None] = mapped_column(String, nullable=True)
    completed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
