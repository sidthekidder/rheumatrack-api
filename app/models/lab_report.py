import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, Date, ForeignKey, Index, func, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class LabReport(Base):
    __tablename__ = "lab_reports"
    __table_args__ = (
        Index("ix_lab_patient_date", "patient_id", "report_date"),
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
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    # results = list of {"testId": str, "value": str}
    results: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, server_default="manual")
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
