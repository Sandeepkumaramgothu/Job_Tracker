"""add_user_id_for_supabase_auth

Revision ID: 8a1c4f2d9b7e
Revises: 4ff2de07a8f6
Create Date: 2026-06-14 06:00:00.000000

Adds user_id (Supabase auth.users.id) to applications and notification_settings
so the tracker is multi-tenant. Existing rows are deleted in the migration
because the pre-auth single-tenant data has no owner to assign.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "8a1c4f2d9b7e"
down_revision: Union[str, None] = "4ff2de07a8f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # WARN: deletes existing pre-auth rows. They have no owner under the new
    # multi-tenant model, so we drop them rather than backfill with a fake user.
    op.execute("DELETE FROM timeline_events")
    op.execute("DELETE FROM applications")
    op.execute("DELETE FROM notification_settings")

    op.add_column(
        "applications",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index(
        "ix_applications_user_id", "applications", ["user_id"], unique=False
    )

    op.add_column(
        "notification_settings",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index(
        "ix_notification_settings_user_id",
        "notification_settings",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_notification_settings_user_id", table_name="notification_settings")
    op.drop_column("notification_settings", "user_id")
    op.drop_index("ix_applications_user_id", table_name="applications")
    op.drop_column("applications", "user_id")
