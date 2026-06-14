# backend/routers/analytics.py

"""
Analytics summary endpoint.

Routes:
  GET /api/analytics/summary   — returns aggregated stats across all applications

Metrics returned:
  - count_by_status             : { applied: N, interview: N, ... }
  - interview_conversion_rate   : (interview+offer count / total) × 100
  - applications_this_month     : count of applications with date_applied in current month
  - top_companies               : top 5 companies by application count (alphabetical tiebreak)
  - avg_days_to_first_response  : avg days from date_applied to first status change away from 'applied'
                                  None when no applications have progressed yet

Design decision: all aggregation is done in Python after fetching rows, rather
than writing complex SQL. This keeps the logic readable and testable without a
live DB. For datasets > ~10k applications, push aggregation into the DB layer
with GROUP BY queries. The trade-off is noted here so it can be changed later.
"""

import logging
import uuid
from collections import Counter
from datetime import date
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import get_current_user_id
from backend.database import get_db
from backend.models.application import Application, ApplicationStatus, TimelineEvent
from backend.schemas.application import AnalyticsSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# ---------------------------------------------------------------------------
# GET /api/analytics/summary
# ---------------------------------------------------------------------------

@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    summary="Aggregated stats across all job applications",
)
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> AnalyticsSummary:
    """
    Returns a full analytics summary. All metrics default to 0 / None so
    the response shape is always consistent even on an empty tracker.
    """
    # Fetch this user's applications in a single query
    apps: List[Application] = (
        await db.execute(
            select(Application).where(Application.user_id == user_id)
        )
    ).scalars().all()

    total = len(apps)

    # ------------------------------------------------------------------
    # 1. Count by status
    # ------------------------------------------------------------------
    count_by_status: Dict[str, int] = {s.value: 0 for s in ApplicationStatus}
    for app in apps:
        count_by_status[app.status.value] += 1

    # ------------------------------------------------------------------
    # 2. Interview conversion rate
    #    = (interview + offer) / total × 100
    #    WARN: includes offers in the numerator — an offer implies an interview
    #    was completed. Rejected-after-interview are also counted as conversions.
    # ------------------------------------------------------------------
    progressed = count_by_status["interview"] + count_by_status["offer"]
    interview_conversion_rate: float = (
        round((progressed / total) * 100, 1) if total > 0 else 0.0
    )

    # ------------------------------------------------------------------
    # 3. Applications this month
    # ------------------------------------------------------------------
    today = date.today()
    applications_this_month: int = sum(
        1
        for app in apps
        if app.date_applied.year == today.year
        and app.date_applied.month == today.month
    )

    # ------------------------------------------------------------------
    # 4. Top 5 companies by application count
    #    Tiebreak: alphabetical order so the list is deterministic
    # ------------------------------------------------------------------
    company_counts = Counter(app.company for app in apps)
    top_companies: List[str] = [
        company
        for company, _ in sorted(
            company_counts.most_common(5),
            key=lambda x: (-x[1], x[0]),  # desc count, asc name
        )
    ]

    # ------------------------------------------------------------------
    # 5. Average days to first response
    #    First response = first TimelineEvent where status != 'applied'
    #    WARN: applications still in 'applied' status with only their
    #    initial event are excluded — they haven't received a response yet.
    # ------------------------------------------------------------------
    avg_days_to_first_response: Optional[float] = None

    if apps:
        app_ids = [app.id for app in apps]
        app_map = {app.id: app for app in apps}

        # Fetch all timeline events for all applications in one query
        all_events: List[TimelineEvent] = (
            await db.execute(
                select(TimelineEvent)
                .where(TimelineEvent.application_id.in_(app_ids))
                .order_by(TimelineEvent.application_id, TimelineEvent.created_at)
            )
        ).scalars().all()

        # Group events by application_id
        events_by_app: Dict = {}
        for event in all_events:
            events_by_app.setdefault(str(event.application_id), []).append(event)

        days_to_response: List[float] = []
        for app in apps:
            events = events_by_app.get(str(app.id), [])
            # Find first event that is NOT 'applied' (the initial submission)
            first_response = next(
                (e for e in events if e.status != ApplicationStatus.applied),
                None,
            )
            if first_response is not None:
                delta = (first_response.event_date - app.date_applied).days
                if delta >= 0:  # WARN: guard against bad data with negative delta
                    days_to_response.append(float(delta))

        if days_to_response:
            avg_days_to_first_response = round(
                sum(days_to_response) / len(days_to_response), 1
            )

    logger.info(
        "Analytics summary: total=%d, this_month=%d, conversion=%.1f%%",
        total, applications_this_month, interview_conversion_rate,
    )

    return AnalyticsSummary(
        count_by_status=count_by_status,
        interview_conversion_rate=interview_conversion_rate,
        applications_this_month=applications_this_month,
        top_companies=top_companies,
        avg_days_to_first_response=avg_days_to_first_response,
    )
