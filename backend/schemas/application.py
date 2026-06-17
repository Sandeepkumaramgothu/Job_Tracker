# backend/schemas/application.py

"""
Pydantic v2 schemas for all request/response shapes in the Job Tracker API.

Schema hierarchy:
  Application
    ApplicationCreate   — POST /api/applications body
    ApplicationUpdate   — PATCH /api/applications/{id} body
    ApplicationResponse — single application, without timeline
    ApplicationDetail   — single application, with full timeline

  TimelineEvent
    TimelineEventCreate   — embedded in ApplicationUpdate
    TimelineEventResponse — read model returned in lists / details

  NotificationSettings
    NotificationSettingsUpdate   — PUT /api/notifications/settings body
    NotificationSettingsResponse — GET /api/notifications/settings response

  Analytics
    AnalyticsSummary — GET /api/analytics/summary response
"""

import uuid
from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.models.application import ApplicationStatus

# ---------------------------------------------------------------------------
# Shared config — applied to all read (response) models
# ---------------------------------------------------------------------------
_orm_config = ConfigDict(from_attributes=True)


# ===========================================================================
# TimelineEvent schemas
# ===========================================================================

class TimelineEventCreate(BaseModel):
    """Embedded in ApplicationUpdate when appending a new timeline entry."""
    event_date: date
    status: ApplicationStatus
    note: Optional[str] = None
    # WARN: interview_date is required when status == "interview".
    # The router must validate this before persisting.
    interview_date: Optional[date] = None
    interview_type: Optional[str] = Field(
        default=None,
        description="One of: phone / technical / panel / final",
    )
    interviewer: Optional[str] = None


class TimelineEventResponse(BaseModel):
    """Read model for a single timeline event row."""
    model_config = _orm_config

    id: uuid.UUID
    application_id: uuid.UUID
    event_date: date
    status: ApplicationStatus
    note: Optional[str] = None
    interview_date: Optional[date] = None
    interview_type: Optional[str] = None
    interviewer: Optional[str] = None
    created_at: datetime


# ===========================================================================
# Application schemas
# ===========================================================================

class ApplicationCreate(BaseModel):
    """Body for POST /api/applications — all required fields must be present."""
    job_title: str = Field(..., min_length=1, max_length=255)
    company: str = Field(..., min_length=1, max_length=255)
    date_applied: date
    source: Optional[str] = Field(
        default=None,
        description="e.g. LinkedIn / Indeed / Glassdoor / Company site",
    )
    location: Optional[str] = None
    salary_range: Optional[str] = None
    job_description: Optional[str] = None
    notes: Optional[str] = None
    status: ApplicationStatus = ApplicationStatus.applied


class ApplicationUpdate(BaseModel):
    """
    Body for PATCH /api/applications/{id}.
    All fields are optional — only provided fields are updated.
    If timeline_event is supplied, a new TimelineEvent row is appended
    AND the application status is updated to match.
    """
    job_title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    company: Optional[str] = Field(default=None, min_length=1, max_length=255)
    date_applied: Optional[date] = None
    source: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    job_description: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[ApplicationStatus] = None
    resume_path: Optional[str] = None
    cover_path: Optional[str] = None
    # Supplying this field appends a timeline event in the same transaction.
    timeline_event: Optional[TimelineEventCreate] = None


class ApplicationResponse(BaseModel):
    """
    Lightweight read model — returned in list views.
    Does NOT embed the full timeline to keep list payloads small.
    """
    model_config = _orm_config

    id: uuid.UUID
    job_title: str
    company: str
    date_applied: date
    source: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    status: ApplicationStatus
    resume_path: Optional[str] = None
    cover_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ApplicationDetail(ApplicationResponse):
    """
    Full read model — returned by GET /api/applications/{id}.
    Extends ApplicationResponse with the complete timeline and hidden fields.
    """
    job_description: Optional[str] = None
    notes: Optional[str] = None
    timeline_events: List[TimelineEventResponse] = []


# ===========================================================================
# Notification settings schemas
# ===========================================================================

class NotificationSettingsUpdate(BaseModel):
    """Body for PUT /api/notifications/settings."""
    email: EmailStr
    notify_interview: bool = True
    notify_followup: bool = True
    notify_stale: bool = True
    weekly_summary: bool = False
    followup_freq_days: int = Field(
        default=7,
        ge=1,
        le=365,
        description="Days between follow-up reminders",
    )
    # AI settings — all optional. Sending an empty string for ai_api_key
    # explicitly clears the stored key; omitting the field leaves it as-is.
    ai_provider: Optional[str] = Field(default=None, description="e.g. 'openai'")
    ai_api_key: Optional[str] = Field(default=None, description="User-supplied LLM API key")
    ai_model: Optional[str] = Field(default=None, description="e.g. 'gpt-4o-mini'")


class NotificationSettingsResponse(BaseModel):
    """
    Read model for GET /api/notifications/settings.
    The actual ai_api_key is NEVER returned — only a redacted hint
    (last 4 chars) so the UI can show "configured" without exposing it.
    """
    model_config = _orm_config

    id: uuid.UUID
    email: str
    notify_interview: bool
    notify_followup: bool
    notify_stale: bool
    weekly_summary: bool
    followup_freq_days: int
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    ai_key_hint: Optional[str] = Field(
        default=None,
        description="Last 4 chars of the stored AI key, or None if unset",
    )


# ===========================================================================
# AI extraction schemas
# ===========================================================================

class AIExtractRequest(BaseModel):
    """Body for POST /api/ai/extract."""
    job_description: str = Field(
        ...,
        min_length=20,
        description="Pasted job description text to be parsed",
    )


class AIExtractResponse(BaseModel):
    """
    Result of parsing a JD. All fields are optional because the LLM might
    not find a clear value for everything; the frontend fills what it gets
    and leaves the rest blank for the user to fill in.
    """
    job_title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None


# ===========================================================================
# File schemas
# ===========================================================================

class FileUploadResponse(BaseModel):
    """Returned by POST /api/files/upload."""
    filename: str
    path: str


# ===========================================================================
# Analytics schemas
# ===========================================================================

class AnalyticsSummary(BaseModel):
    """
    Returned by GET /api/analytics/summary.
    All counts default to 0 so the response is always fully populated
    even when the tracker is new and has no applications.
    """
    count_by_status: Dict[str, int] = Field(
        default_factory=dict,
        description="Keys are ApplicationStatus values; values are counts.",
    )
    interview_conversion_rate: float = Field(
        default=0.0,
        description="(interviews / total applications) × 100, as a percentage.",
    )
    applications_this_month: int = 0
    top_companies: List[str] = Field(
        default_factory=list,
        description="Top 5 companies by application count.",
    )
    avg_days_to_first_response: Optional[float] = Field(
        default=None,
        description="Average days from date_applied to first status change away from 'applied'.",
    )
