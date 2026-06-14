# backend/routers/applications.py

"""
Full CRUD for job applications.

Routes:
  GET    /api/applications          — list all; optional ?status= and ?search= filters
  POST   /api/applications          — create a new application (201)
  GET    /api/applications/{id}     — get a single application with full timeline (200)
  PATCH  /api/applications/{id}     — update fields + optionally append a timeline event (200)
  DELETE /api/applications/{id}     — hard delete application and cascade timeline events (204)
"""

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.auth import get_current_user_id
from backend.database import get_db
from backend.models.application import Application, ApplicationStatus, TimelineEvent
from backend.schemas.application import (
    ApplicationCreate,
    ApplicationDetail,
    ApplicationResponse,
    ApplicationUpdate,
    TimelineEventCreate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/applications", tags=["applications"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_application_or_404(
    app_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
    *,
    load_timeline: bool = False,
) -> Application:
    """
    Fetch an Application owned by the given user.
    Returns 404 — never 403 — for someone else's application so we don't
    leak the existence of records to other users.
    """
    query = select(Application).where(
        Application.id == app_id,
        Application.user_id == user_id,
    )
    if load_timeline:
        query = query.options(selectinload(Application.timeline_events))

    result = await db.execute(query)
    app = result.scalar_one_or_none()
    if app is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application {app_id} not found.",
        )
    return app


def _append_timeline_event(
    app: Application,
    event_data: TimelineEventCreate,
) -> TimelineEvent:
    """
    Build and attach a new TimelineEvent to the given Application instance.
    The caller is responsible for flushing / committing the session.

    WARN: interview_date is required when status == 'interview'.
    We validate this here and raise 422 if it is missing.
    """
    if (
        event_data.status == ApplicationStatus.interview
        and event_data.interview_date is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="interview_date is required when status is 'interview'.",
        )

    event = TimelineEvent(
        application_id=app.id,
        event_date=event_data.event_date,
        status=event_data.status,
        note=event_data.note,
        interview_date=event_data.interview_date,
        interview_type=event_data.interview_type,
        interviewer=event_data.interviewer,
    )
    app.timeline_events.append(event)
    return event


# ---------------------------------------------------------------------------
# GET /api/applications
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=List[ApplicationResponse],
    summary="List all applications",
)
async def list_applications(
    status_filter: Optional[ApplicationStatus] = Query(
        default=None,
        alias="status",
        description="Filter by application status",
    ),
    search: Optional[str] = Query(
        default=None,
        description="Case-insensitive search across job_title and company",
    ),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> List[Application]:
    """
    Returns the caller's applications ordered by date_applied descending.
    Supports optional ?status= and ?search= query parameters.
    """
    query = (
        select(Application)
        .where(Application.user_id == user_id)
        .order_by(Application.date_applied.desc())
    )

    if status_filter is not None:
        query = query.where(Application.status == status_filter)

    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Application.job_title.ilike(pattern),
                Application.company.ilike(pattern),
            )
        )

    result = await db.execute(query)
    return result.scalars().all()


# ---------------------------------------------------------------------------
# POST /api/applications
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=ApplicationDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new application",
)
async def create_application(
    body: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Application:
    """
    Creates a new Application and an initial TimelineEvent
    recording the date_applied with the supplied status.
    Returns the full ApplicationDetail (with timeline).

    WARN: Creating an application with status='interview' is rejected because
    the initial event would lack an interview_date. Callers should create the
    application with status='applied', then PATCH with a timeline_event
    carrying the interview_date.
    """
    if body.status == ApplicationStatus.interview:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Cannot create an application directly in 'interview' status. "
                "Create it as 'applied', then update with an interview_date."
            ),
        )

    app = Application(
        user_id=user_id,
        job_title=body.job_title,
        company=body.company,
        date_applied=body.date_applied,
        source=body.source,
        location=body.location,
        salary_range=body.salary_range,
        job_description=body.job_description,
        notes=body.notes,
        status=body.status,
    )
    db.add(app)
    # Flush to get the auto-generated UUID before creating the FK row.
    await db.flush()

    # Automatically record the initial status in the timeline.
    initial_event = TimelineEvent(
        application_id=app.id,
        event_date=body.date_applied,
        status=body.status,
        note="Application submitted.",
    )
    db.add(initial_event)
    await db.flush()

    # Reload with timeline so the response schema is fully populated.
    await db.refresh(app, ["timeline_events"])
    logger.info("Created application %s for %s at %s", app.id, app.company, app.job_title)
    return app


# ---------------------------------------------------------------------------
# GET /api/applications/{id}
# ---------------------------------------------------------------------------

@router.get(
    "/{app_id}",
    response_model=ApplicationDetail,
    summary="Get a single application with full timeline",
)
async def get_application(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Application:
    return await _get_application_or_404(app_id, user_id, db, load_timeline=True)


# ---------------------------------------------------------------------------
# PATCH /api/applications/{id}
# ---------------------------------------------------------------------------

@router.patch(
    "/{app_id}",
    response_model=ApplicationDetail,
    summary="Update application fields; optionally append a timeline event",
)
async def update_application(
    app_id: uuid.UUID,
    body: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Application:
    """
    Partial update — only fields explicitly set in the request body are modified.
    If `timeline_event` is provided, a new TimelineEvent row is appended in
    the same transaction and the application status is set to match.

    WARN: If both `status` and `timeline_event.status` are supplied and differ,
    `timeline_event.status` wins (it is more specific — it carries interview
    metadata and a note). This is intentional — document the trade-off here
    so future maintainers don't change it blindly.
    """
    app = await _get_application_or_404(app_id, user_id, db, load_timeline=True)

    # Apply scalar field updates (only fields that were actually sent).
    update_data = body.model_dump(exclude_unset=True, exclude={"timeline_event"})
    for field, value in update_data.items():
        setattr(app, field, value)

    # Append timeline event and sync status if provided.
    if body.timeline_event is not None:
        _append_timeline_event(app, body.timeline_event)
        # Status always follows the most recent timeline event.
        app.status = body.timeline_event.status

    await db.flush()
    await db.refresh(app, ["timeline_events"])
    logger.info("Updated application %s — status=%s", app.id, app.status)
    return app


# ---------------------------------------------------------------------------
# DELETE /api/applications/{id}
# ---------------------------------------------------------------------------

@router.delete(
    "/{app_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Hard-delete an application and all its timeline events",
)
async def delete_application(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """
    Permanently deletes the application.
    Timeline events are removed by the DB-level CASCADE on the FK.
    File paths stored in resume_path / cover_path are NOT deleted here —
    file cleanup is handled by file_service.py.

    WARN: This is a hard delete with no soft-delete fallback.
    If undo / audit trail is needed in the future, add a deleted_at column
    and switch to a soft-delete pattern instead.
    """
    app = await _get_application_or_404(app_id, user_id, db)
    await db.delete(app)
    logger.info("Deleted application %s", app_id)
