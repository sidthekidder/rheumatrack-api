"""add lab_reports flare_entries appointments

Revision ID: af479dbb3c17
Revises: 90d739914277
Create Date: 2026-05-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY


# revision identifiers, used by Alembic.
revision: str = 'af479dbb3c17'
down_revision: Union[str, None] = '90d739914277'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RLS_TABLES = [
    ("lab_reports", "patient_id"),
    ("flare_entries", "patient_id"),
    ("appointments", "patient_id"),
]


def upgrade() -> None:
    op.create_table(
        "lab_reports",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "patient_id",
            UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("report_date", sa.Date, nullable=False),
        sa.Column("results", JSONB, nullable=False),
        sa.Column("source", sa.String, nullable=False, server_default="manual"),
        sa.Column("notes", sa.String, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_lab_patient_date",
        "lab_reports",
        ["patient_id", "report_date"],
    )

    op.create_table(
        "flare_entries",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "patient_id",
            UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entry_date", sa.Date, nullable=False),
        sa.Column("pain", sa.Integer, nullable=False, server_default="0"),
        sa.Column("stiffness_min", sa.Integer, nullable=False, server_default="0"),
        sa.Column("fatigue", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "joints",
            ARRAY(sa.String),
            nullable=True,
            server_default="{}",
        ),
        sa.Column("notes", sa.String, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "patient_id",
            "entry_date",
            name="uq_flare_per_day",
        ),
    )
    op.create_index(
        "ix_flare_patient_date",
        "flare_entries",
        ["patient_id", "entry_date"],
    )

    op.create_table(
        "appointments",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "patient_id",
            UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("appointment_date", sa.Date, nullable=False),
        sa.Column("appointment_time", sa.String, nullable=True),
        sa.Column("doctor_name", sa.String, nullable=False),
        sa.Column("clinic", sa.String, nullable=True),
        sa.Column(
            "visit_type",
            sa.String,
            nullable=False,
            server_default="Routine Follow-up",
        ),
        sa.Column("pre_notes", sa.String, nullable=True),
        sa.Column("post_notes", sa.String, nullable=True),
        sa.Column(
            "completed",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_appt_patient_date",
        "appointments",
        ["patient_id", "appointment_date"],
    )

    # RLS — same pattern as patients/medicines/medication_log/prescriptions.
    for table, col in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_owner ON {table} "
            f"FOR ALL USING ({col} = auth.uid()) "
            f"WITH CHECK ({col} = auth.uid())"
        )


def downgrade() -> None:
    for table, _ in RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_owner ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_index("ix_appt_patient_date", table_name="appointments")
    op.drop_table("appointments")
    op.drop_index("ix_flare_patient_date", table_name="flare_entries")
    op.drop_table("flare_entries")
    op.drop_index("ix_lab_patient_date", table_name="lab_reports")
    op.drop_table("lab_reports")
