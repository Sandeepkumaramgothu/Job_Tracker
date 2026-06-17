"""add_ai_keys_to_settings

Revision ID: c2f5a1e9b3d4
Revises: 8a1c4f2d9b7e
Create Date: 2026-06-16 09:00:00.000000

Adds nullable ai_provider / ai_api_key / ai_model columns to
notification_settings so users can paste their own LLM key for the
AI job-description extractor.

Strictly additive — does NOT touch any existing rows.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c2f5a1e9b3d4"
down_revision: Union[str, None] = "8a1c4f2d9b7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notification_settings",
        sa.Column("ai_provider", sa.String(), nullable=True),
    )
    op.add_column(
        "notification_settings",
        sa.Column("ai_api_key", sa.String(), nullable=True),
    )
    op.add_column(
        "notification_settings",
        sa.Column("ai_model", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("notification_settings", "ai_model")
    op.drop_column("notification_settings", "ai_api_key")
    op.drop_column("notification_settings", "ai_provider")
