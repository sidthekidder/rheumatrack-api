"""add patients medicines medication_log prescriptions

Revision ID: 90d739914277
Revises: 320cac34d03f
Create Date: 2026-05-04 01:17:17.993563

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY


# revision identifiers, used by Alembic.
revision: str = '90d739914277'
down_revision: Union[str, None] = '320cac34d03f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


RLS_TABLES = [
    ("patients", "id"),
    ("medicines", "patient_id"),
    ("medication_log", "patient_id"),
    ("prescriptions", "patient_id"),
]


def upgrade() -> None:
    # pgcrypto is preinstalled on Supabase (extensions schema) — gen_random_uuid()
    # is resolvable via search_path. Belt-and-suspenders:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # patients — 1:1 with auth.users; id = auth.uid() (set explicitly by API, no default)
    op.create_table(
        "patients",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("age", sa.Integer, nullable=True),
        sa.Column("patient_id", sa.String, nullable=True),
        sa.Column("city", sa.String, nullable=True),
        sa.Column("state", sa.String, nullable=True),
        sa.Column("country", sa.String, nullable=True, server_default="India"),
        sa.Column("doctor_name", sa.String, nullable=True),
        sa.Column("doctor_specialty", sa.String, nullable=True),
        sa.Column("doctor_phone", sa.String, nullable=True),
        sa.Column("doctor_hospital", sa.String, nullable=True),
        sa.Column("diagnosis", sa.String, nullable=True),
        sa.Column("theme", sa.String, nullable=True, server_default="system"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "medicines",
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
            index=True,
        ),
        sa.Column("drug_name", sa.String, nullable=False),
        sa.Column("brand_name", sa.String, nullable=False),
        sa.Column("dose", sa.String, nullable=False),
        sa.Column("schedule_type", sa.String, nullable=False),
        sa.Column("dose_schedule", JSONB, nullable=False),
        sa.Column("week_day", sa.Integer, nullable=True),
        sa.Column(
            "exclude_days",
            ARRAY(sa.Integer),
            nullable=True,
            server_default="{}",
        ),
        sa.Column("tapering_phases", JSONB, nullable=True),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("duration_days", sa.Integer, nullable=True),
        sa.Column("food_timing_id", sa.String, nullable=True),
        sa.Column("food_timing_label", sa.String, nullable=True),
        sa.Column("reminder_time", sa.String, nullable=True),
        sa.Column("route", sa.String, nullable=True),
        sa.Column("tip", sa.String, nullable=True),
        sa.Column("notes", sa.String, nullable=True),
        sa.Column("color", sa.String, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "medication_log",
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
        sa.Column(
            "medicine_id",
            UUID(as_uuid=True),
            sa.ForeignKey("medicines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("log_date", sa.Date, nullable=False),
        sa.Column("slot", sa.String, nullable=False),
        sa.Column(
            "taken",
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
        sa.UniqueConstraint(
            "patient_id",
            "medicine_id",
            "log_date",
            "slot",
            name="uq_log_unique",
        ),
    )
    op.create_index(
        "ix_log_patient_date",
        "medication_log",
        ["patient_id", "log_date"],
    )

    op.create_table(
        "prescriptions",
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
            index=True,
        ),
        sa.Column("storage_path", sa.String, nullable=True),
        sa.Column("mime_type", sa.String, nullable=False),
        sa.Column(
            "scanned_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("raw_response", JSONB, nullable=True),
    )

    # Auto-refresh patients.updated_at on UPDATE — reuses the set_updated_at()
    # function defined by the users-table migration.
    op.execute(
        """
        CREATE TRIGGER patients_set_updated_at
        BEFORE UPDATE ON patients
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at();
        """
    )

    # RLS — enable + permissive owner policy keyed off auth.uid().
    # Backend uses postgres role (bypasses RLS); these guard direct frontend reads.
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

    op.execute("DROP TRIGGER IF EXISTS patients_set_updated_at ON patients;")

    op.drop_table("prescriptions")
    op.drop_index("ix_log_patient_date", table_name="medication_log")
    op.drop_table("medication_log")
    op.drop_table("medicines")
    op.drop_table("patients")
