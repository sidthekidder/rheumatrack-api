"""add admin_users, is_admin() helper, admin-aware RLS, admin_access_log

Revision ID: b7e1c92a4f8d
Revises: e90f33692a07
Create Date: 2026-05-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = 'b7e1c92a4f8d'
down_revision: Union[str, None] = 'e90f33692a07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, owner_column) for every patient-owned table whose RLS policy needs
# to be widened to "owner OR admin" on reads. Writes stay owner-only.
RLS_TABLES = [
    ("patients", "id"),
    ("medicines", "patient_id"),
    ("medication_log", "patient_id"),
    ("prescriptions", "patient_id"),
    ("lab_reports", "patient_id"),
    ("flare_entries", "patient_id"),
    ("appointments", "patient_id"),
    ("medication_log_history", "patient_id"),
]


def upgrade() -> None:
    # ── admin_users ───────────────────────────────────────────────────────────
    op.create_table(
        "admin_users",
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column("role", sa.String, nullable=False, server_default="admin"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.execute("ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY")
    # Admins can only see their own row (used by middleware to verify membership).
    op.execute(
        "CREATE POLICY admin_users_self ON admin_users "
        "FOR SELECT USING (user_id = auth.uid())"
    )

    # ── is_admin() helper ────────────────────────────────────────────────────
    # SECURITY DEFINER so policy evaluation can read admin_users without the
    # caller needing direct SELECT grant. STABLE so PG memoises within a query.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.is_admin()
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public
        AS $$
          SELECT EXISTS (
            SELECT 1 FROM public.admin_users WHERE user_id = auth.uid()
          );
        $$;
        """
    )
    op.execute("GRANT EXECUTE ON FUNCTION public.is_admin() TO authenticated")

    # ── widen existing owner policies ────────────────────────────────────────
    # Old shape: single `_owner` policy FOR ALL (owner == auth.uid()).
    # New shape: split into read (owner OR admin) and write (owner only) so
    # admins can browse all patient data but cannot mutate it via RLS.
    for table, col in RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_owner ON {table}")
        op.execute(
            f"CREATE POLICY {table}_read ON {table} "
            f"FOR SELECT USING ({col} = auth.uid() OR public.is_admin())"
        )
        op.execute(
            f"CREATE POLICY {table}_insert ON {table} "
            f"FOR INSERT WITH CHECK ({col} = auth.uid())"
        )
        op.execute(
            f"CREATE POLICY {table}_update ON {table} "
            f"FOR UPDATE USING ({col} = auth.uid()) "
            f"WITH CHECK ({col} = auth.uid())"
        )
        op.execute(
            f"CREATE POLICY {table}_delete ON {table} "
            f"FOR DELETE USING ({col} = auth.uid())"
        )

    # ── admin_access_log ─────────────────────────────────────────────────────
    # Server-side audit trail of every admin read. Inserted by the Next.js app
    # using the service-role key (bypasses RLS); read-restricted to admins.
    op.create_table(
        "admin_access_log",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("admin_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "patient_id",
            UUID(as_uuid=True),
            sa.ForeignKey("patients.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_admin_access_log_admin_created",
        "admin_access_log",
        ["admin_user_id", "created_at"],
    )
    op.create_index(
        "ix_admin_access_log_patient_created",
        "admin_access_log",
        ["patient_id", "created_at"],
    )
    op.execute("ALTER TABLE admin_access_log ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY admin_access_log_admins_read ON admin_access_log "
        "FOR SELECT USING (public.is_admin())"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS admin_access_log_admins_read ON admin_access_log"
    )
    op.execute("ALTER TABLE admin_access_log DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_admin_access_log_patient_created", table_name="admin_access_log"
    )
    op.drop_index(
        "ix_admin_access_log_admin_created", table_name="admin_access_log"
    )
    op.drop_table("admin_access_log")

    # Restore the original single _owner policy on each patient-owned table.
    for table, col in RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_delete ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_update ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_insert ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_read ON {table}")
        op.execute(
            f"CREATE POLICY {table}_owner ON {table} "
            f"FOR ALL USING ({col} = auth.uid()) "
            f"WITH CHECK ({col} = auth.uid())"
        )

    op.execute("REVOKE EXECUTE ON FUNCTION public.is_admin() FROM authenticated")
    op.execute("DROP FUNCTION IF EXISTS public.is_admin()")

    op.execute("DROP POLICY IF EXISTS admin_users_self ON admin_users")
    op.execute("ALTER TABLE admin_users DISABLE ROW LEVEL SECURITY")
    op.drop_table("admin_users")
