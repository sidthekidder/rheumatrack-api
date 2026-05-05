import uuid
from datetime import datetime, date
from sqlalchemy import String, Integer, DateTime, Date, ForeignKey, UniqueConstraint, Index, func, text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class FlareEntry(Base):
    __tablename__ = "flare_entries"
    __table_args__ = (
        UniqueConstraint("patient_id", "entry_date", name="uq_flare_per_day"),
        Index("ix_flare_patient_date", "patient_id", "entry_date"),
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
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    pain: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    stiffness_min: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    fatigue: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    joints: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True, server_default="{}"
    )
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
