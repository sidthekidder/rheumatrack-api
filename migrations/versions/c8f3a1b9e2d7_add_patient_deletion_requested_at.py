"""add patients.deletion_requested_at

Revision ID: c8f3a1b9e2d7
Revises: b7e1c92a4f8d
Create Date: 2026-06-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c8f3a1b9e2d7'
down_revision: Union[str, None] = 'b7e1c92a4f8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column(
            "deletion_requested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_patients_deletion_requested_at",
        "patients",
        ["deletion_requested_at"],
        postgresql_where=sa.text("deletion_requested_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_patients_deletion_requested_at", table_name="patients"
    )
    op.drop_column("patients", "deletion_requested_at")
