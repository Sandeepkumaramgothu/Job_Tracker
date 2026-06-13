"""create_initial_tables

Revision ID: 4ff2de07a8f6
Revises: 
Create Date: 2026-06-13 11:38:15.935989

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4ff2de07a8f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Shared enum type — created once, reused by both tables.
applicationstatus = postgresql.ENUM(
    "applied",
    "interview",
    "followup",
    "offer",
    "rejected",
    name="applicationstatus",
    create_type=False,
)


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Create the shared ENUM type first
    # ------------------------------------------------------------------
    applicationstatus.create(op.get_bind(), checkfirst=True)

    # ------------------------------------------------------------------
    # Table: applications
    # ------------------------------------------------------------------
    op.create_table(
        "applications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("job_title", sa.String(), nullable=False),
        sa.Column("company", sa.String(), nullable=False),
        sa.Column("date_applied", sa.Date(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("salary_range", sa.String(), nullable=True),
        sa.Column("job_description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            applicationstatus,
            nullable=False,
        ),
        sa.Column("resume_path", sa.String(), nullable=True),
        sa.Column("cover_path", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------
    # Table: timeline_events
    # ------------------------------------------------------------------
    op.create_table(
        "timeline_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            applicationstatus,
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("interview_date", sa.Date(), nullable=True),
        sa.Column("interview_type", sa.String(), nullable=True),
        sa.Column("interviewer", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_timeline_events_application_id",
        "timeline_events",
        ["application_id"],
    )

    # ------------------------------------------------------------------
    # Table: notification_settings
    # ------------------------------------------------------------------
    op.create_table(
        "notification_settings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column(
            "notify_interview",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "notify_followup",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "notify_stale",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "weekly_summary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "followup_freq_days",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("7"),
        ),
    )


def downgrade() -> None:
    op.drop_table("notification_settings")
    op.drop_index("ix_timeline_events_application_id", table_name="timeline_events")
    op.drop_table("timeline_events")
    op.drop_table("applications")
    applicationstatus.drop(op.get_bind(), checkfirst=True)
