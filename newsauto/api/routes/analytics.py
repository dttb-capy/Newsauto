"""Analytics API endpoints."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from newsauto.api.routes.auth import get_current_user
from newsauto.core.database import get_db
from newsauto.models.edition import Edition, EditionStats
from newsauto.models.events import EventType, SubscriberEvent
from newsauto.models.newsletter import Newsletter
from newsauto.models.subscriber import Subscriber
from newsauto.models.user import User

router = APIRouter()


@router.get("/overview")
async def get_overview(
    newsletter_id: Optional[int] = None,
    period: str = Query("week", regex="^(day|week|month|year)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get analytics overview."""
    # Calculate date range
    now = datetime.utcnow()
    if period == "day":
        since = now - timedelta(days=1)
    elif period == "week":
        since = now - timedelta(days=7)
    elif period == "month":
        since = now - timedelta(days=30)
    else:
        since = now - timedelta(days=365)

    # Base query filters
    newsletter_filter = []
    if newsletter_id:
        # Verify ownership
        newsletter = (
            db.query(Newsletter)
            .filter(
                Newsletter.id == newsletter_id, Newsletter.user_id == current_user.id
            )
            .first()
        )
        if newsletter:
            newsletter_filter = [Newsletter.id == newsletter_id]

    # Get subscriber stats
    total_subscribers = (
        db.query(func.count(Subscriber.id))
        .filter(Subscriber.status == "active")
        .scalar()
        or 0
    )

    new_subscribers = (
        db.query(func.count(Subscriber.id))
        .filter(Subscriber.subscribed_at >= since)
        .scalar()
        or 0
    )

    # Get edition stats
    editions_sent = db.query(func.count(Edition.id)).filter(
        Edition.sent_at >= since, ~Edition.test_mode
    )

    if newsletter_filter:
        editions_sent = editions_sent.filter(*newsletter_filter)

    editions_sent = editions_sent.scalar() or 0

    # Get engagement stats
    opens = (
        db.query(func.count(SubscriberEvent.id))
        .filter(
            SubscriberEvent.event_type == EventType.OPEN,
            SubscriberEvent.created_at >= since,
        )
        .scalar()
        or 0
    )

    clicks = (
        db.query(func.count(SubscriberEvent.id))
        .filter(
            SubscriberEvent.event_type == EventType.CLICK,
            SubscriberEvent.created_at >= since,
        )
        .scalar()
        or 0
    )

    return {
        "period": period,
        "subscribers": {
            "total": total_subscribers,
            "new": new_subscribers,
            "growth_rate": (
                new_subscribers / max(total_subscribers - new_subscribers, 1)
            )
            * 100,
        },
        "engagement": {
            "editions_sent": editions_sent,
            "total_opens": opens,
            "total_clicks": clicks,
            "avg_open_rate": _calculate_open_rate(db, since, newsletter_id),
            "avg_click_rate": _calculate_click_rate(db, since, newsletter_id)
        },
    }


@router.get("/growth")
async def get_growth(
    newsletter_id: Optional[int] = None,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get subscriber growth data."""
    since = datetime.utcnow() - timedelta(days=days)

    # Get daily subscriber counts
    growth_data = []

    for i in range(days):
        date = since + timedelta(days=i)
        next_date = date + timedelta(days=1)

        count = (
            db.query(func.count(Subscriber.id))
            .filter(Subscriber.subscribed_at < next_date, Subscriber.status == "active")
            .scalar()
            or 0
        )

        growth_data.append({"date": date.date().isoformat(), "subscribers": count})

    return {"period_days": days, "data": growth_data}


def _calculate_open_rate(db: Session, since: datetime, newsletter_id: Optional[int] = None) -> float:
    """Calculate average open rate.

    Args:
        db: Database session
        since: Start date
        newsletter_id: Optional newsletter filter

    Returns:
        Open rate percentage
    """
    # Get editions sent in period
    editions_query = db.query(Edition).filter(
        Edition.sent_at >= since,
        ~Edition.test_mode
    )

    if newsletter_id:
        editions_query = editions_query.filter(Edition.newsletter_id == newsletter_id)

    edition_ids = [e.id for e in editions_query.all()]

    if not edition_ids:
        return 0.0

    # Get stats for these editions
    stats = db.query(EditionStats).filter(
        EditionStats.edition_id.in_(edition_ids)
    ).all()

    if not stats:
        return 0.0

    total_sent = sum(s.sent_count or 0 for s in stats)
    total_opened = sum(s.opened_count or 0 for s in stats)

    if total_sent == 0:
        return 0.0

    return round((total_opened / total_sent) * 100, 2)


def _calculate_click_rate(db: Session, since: datetime, newsletter_id: Optional[int] = None) -> float:
    """Calculate average click rate.

    Args:
        db: Database session
        since: Start date
        newsletter_id: Optional newsletter filter

    Returns:
        Click rate percentage
    """
    # Get editions sent in period
    editions_query = db.query(Edition).filter(
        Edition.sent_at >= since,
        ~Edition.test_mode
    )

    if newsletter_id:
        editions_query = editions_query.filter(Edition.newsletter_id == newsletter_id)

    edition_ids = [e.id for e in editions_query.all()]

    if not edition_ids:
        return 0.0

    # Get stats for these editions
    stats = db.query(EditionStats).filter(
        EditionStats.edition_id.in_(edition_ids)
    ).all()

    if not stats:
        return 0.0

    total_sent = sum(s.sent_count or 0 for s in stats)
    total_clicked = sum(s.clicked_count or 0 for s in stats)

    if total_sent == 0:
        return 0.0

    return round((total_clicked / total_sent) * 100, 2)


@router.get("/engagement")
async def get_engagement(
    newsletter_id: Optional[int] = None,
    edition_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get engagement metrics."""
    if edition_id:
        # Get specific edition stats
        stats = (
            db.query(EditionStats).filter(EditionStats.edition_id == edition_id).first()
        )

        if stats:
            return {
                "edition_id": edition_id,
                "sent": stats.sent_count,
                "delivered": stats.delivered_count,
                "opened": stats.opened_count,
                "clicked": stats.clicked_count,
                "open_rate": stats.open_rate or 0,
                "click_rate": stats.click_rate or 0,
            }

    # Get overall engagement
    total_sent = db.query(func.sum(EditionStats.sent_count)).scalar() or 0
    total_opened = db.query(func.sum(EditionStats.opened_count)).scalar() or 0
    total_clicked = db.query(func.sum(EditionStats.clicked_count)).scalar() or 0

    return {
        "total_sent": total_sent,
        "total_opened": total_opened,
        "total_clicked": total_clicked,
        "avg_open_rate": (total_opened / max(total_sent, 1)) * 100,
        "avg_click_rate": (total_clicked / max(total_sent, 1)) * 100,
    }
