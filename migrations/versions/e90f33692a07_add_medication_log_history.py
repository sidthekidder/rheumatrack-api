"""add medication_log_history

Revision ID: e90f33692a07
Revises: 757845e3ed10
Create Date: 2026-05-09 00:50:45.937700

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'e90f33692a07'
down_revision: Union[str, None] = '757845e3ed10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "medication_log_history",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "log_id",
            UUID(as_uuid=True),
            sa.ForeignKey("medication_log.id", ondelete="CASCADE"),
            nullable=False,
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
        sa.Column("prior_taken", sa.Boolean, nullable=True),
        sa.Column("new_taken", sa.Boolean, nullable=False),
        sa.Column("edited_by_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "edited_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_log_hist_patient_date",
        "medication_log_history",
        ["patient_id", "edited_at"],
    )
    op.create_index(
        "ix_log_hist_log_id",
        "medication_log_history",
        ["log_id", "edited_at"],
    )

    # RLS — same pattern as medication_log: only the owner can read their history.
    op.execute("ALTER TABLE medication_log_history ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY medication_log_history_owner ON medication_log_history "
        "FOR ALL USING (patient_id = auth.uid()) "
        "WITH CHECK (patient_id = auth.uid())"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS medication_log_history_owner ON medication_log_history"
    )
    op.execute("ALTER TABLE medication_log_history DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_log_hist_log_id", table_name="medication_log_history"
    )
    op.drop_index(
        "ix_log_hist_patient_date", table_name="medication_log_history"
    )
    op.drop_table("medication_log_history")
