# backend/models/application.py

import enum
import uuid
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

# ---------------------------------------------------------------------------
# Status enum — single source of truth; used in both tables.
# Use these exact string values everywhere: DB, API, frontend.
# ---------------------------------------------------------------------------
class ApplicationStatus(str, enum.Enum):
    applied   = "applied"    # just submitted the application
    interview = "interview"  # interview has been scheduled
    followup  = "followup"   # follow-up email has been sent
    offer     = "offer"      # offer received
    rejected  = "rejected"   # application rejected


# ---------------------------------------------------------------------------
# Table: applications
# ---------------------------------------------------------------------------
class Application(Base):
    __tablename__ = "applications"
    # eager_defaults=True makes SQLAlchemy fetch server-computed values
    # (created_at, updated_at) via RETURNING in the same INSERT/UPDATE.
    # Without this, updated_at is expired after UPDATE and the next access
    # triggers a lazy SELECT — which fails (MissingGreenlet) during async
    # response serialization after the session closes, producing an
    # uncaught 500 with no CORS headers (the "Network Error" symptom).
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # user_id is the Supabase Auth user.id (auth.users.id). We don't add a
    # cross-schema FK because the auth.users table lives in Supabase's
    # managed schema; the app layer guarantees consistency by always setting
    # this from the verified JWT subject.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    job_title: Mapped[str] = mapped_column(String, nullable=False)
    company: Mapped[str] = mapped_column(String, nullable=False)
    date_applied: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    salary_range: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    job_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="applicationstatus"),
        nullable=False,
        default=ApplicationStatus.applied,
    )
    # WARN: resume_path / cover_path store local disk paths or S3 keys.
    # If a file is deleted from storage but the DB record remains, the path
    # becomes stale. Always verify file existence before serving downloads.
    resume_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cover_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    timeline_events: Mapped[List["TimelineEvent"]] = relationship(
        "TimelineEvent",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="TimelineEvent.event_date",
    )

    def __repr__(self) -> str:
        return f"<Application id={self.id} company={self.company!r} status={self.status}>"


# ---------------------------------------------------------------------------
# Table: timeline_events
# ---------------------------------------------------------------------------
class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="applicationstatus"),
        nullable=False,
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # WARN: interview_date can be None when status != interview.
    # Reminder tasks must guard against this before computing a 24h window.
    interview_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    interview_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # phone / technical / panel / final
    interviewer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    application: Mapped["Application"] = relationship(
        "Application", back_populates="timeline_events"
    )

    def __repr__(self) -> str:
        return (
            f"<TimelineEvent id={self.id} application_id={self.application_id}"
            f" status={self.status} event_date={self.event_date}>"
        )


# ---------------------------------------------------------------------------
# Table: notification_settings
# ---------------------------------------------------------------------------
class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # One settings row per Supabase Auth user. Unique so PUT can upsert by user.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True, index=True
    )
    email: Mapped[str] = mapped_column(String, nullable=False)
    notify_interview: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    notify_followup: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    notify_stale: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    weekly_summary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    followup_freq_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=7
    )
    # AI extraction settings — user pastes their own LLM API key. We store
    # it as-is (Supabase encrypts at rest); the backend never returns the
    # full key in API responses.
    ai_provider: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ai_api_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ai_model: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    def __repr__(self) -> str:
        return f"<NotificationSettings id={self.id} email={self.email!r}>"
