"""Email tracking endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, Response, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_

from newsauto.core.database import get_db
from newsauto.models.events import SubscriberEvent, EventType
from newsauto.models.edition import EditionStats

router = APIRouter(prefix="/track", tags=["tracking"])

# 1x1 transparent pixel GIF
PIXEL_GIF = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"


@router.get("/open/{tracking_id}")
async def track_open(
    tracking_id: str,
    db: Session = Depends(get_db)
) -> Response:
    """Track email open.

    Args:
        tracking_id: Tracking ID
        db: Database session

    Returns:
        1x1 transparent pixel
    """
    # Look up tracking record
    tracking = _get_tracking_record(db, tracking_id)

    if tracking:
        edition_id = tracking["edition_id"]
        subscriber_id = tracking["subscriber_id"]

        # Check if already tracked
        existing = (
            db.query(SubscriberEvent)
            .filter(
                and_(
                    SubscriberEvent.subscriber_id == subscriber_id,
                    SubscriberEvent.event_type == EventType.OPEN,
                    SubscriberEvent.metadata["edition_id"].astext == str(edition_id)
                )
            )
            .first()
        )

        if not existing:
            # Log open event
            event = SubscriberEvent(
                subscriber_id=subscriber_id,
                event_type=EventType.OPEN,
                metadata={
                    "edition_id": edition_id,
                    "tracking_id": tracking_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            db.add(event)

            # Update edition stats
            stats = (
                db.query(EditionStats)
                .filter(EditionStats.edition_id == edition_id)
                .first()
            )

            if stats:
                stats.opened_count = (stats.opened_count or 0) + 1
                stats.open_rate = (stats.opened_count / max(stats.sent_count, 1)) * 100
                stats.last_updated = datetime.utcnow()

            db.commit()

    # Return tracking pixel
    return Response(content=PIXEL_GIF, media_type="image/gif", headers={
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    })


@router.get("/click/{tracking_id}")
async def track_click(
    tracking_id: str,
    url: str = Query(..., description="Destination URL"),
    db: Session = Depends(get_db)
) -> Response:
    """Track link click.

    Args:
        tracking_id: Tracking ID
        url: Destination URL
        db: Database session

    Returns:
        Redirect to destination
    """
    # Look up tracking record
    tracking = _get_tracking_record(db, tracking_id)

    if tracking:
        edition_id = tracking["edition_id"]
        subscriber_id = tracking["subscriber_id"]

        # Log click event
        event = SubscriberEvent(
            subscriber_id=subscriber_id,
            event_type=EventType.CLICK,
            metadata={
                "edition_id": edition_id,
                "tracking_id": tracking_id,
                "url": url,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        db.add(event)

        # Update edition stats
        stats = (
            db.query(EditionStats)
            .filter(EditionStats.edition_id == edition_id)
            .first()
        )

        if stats:
            # Check if this is the first click from this subscriber
            existing_click = (
                db.query(SubscriberEvent)
                .filter(
                    and_(
                        SubscriberEvent.subscriber_id == subscriber_id,
                        SubscriberEvent.event_type == EventType.CLICK,
                        SubscriberEvent.metadata["edition_id"].astext == str(edition_id),
                        SubscriberEvent.id != event.id
                    )
                )
                .first()
            )

            if not existing_click:
                stats.clicked_count = (stats.clicked_count or 0) + 1
                stats.click_rate = (stats.clicked_count / max(stats.sent_count, 1)) * 100

            stats.last_updated = datetime.utcnow()

        db.commit()

    # Redirect to destination
    return Response(
        status_code=302,
        headers={"Location": url}
    )


def _get_tracking_record(db: Session, tracking_id: str) -> Optional[dict]:
    """Get tracking record from database.

    For now, we'll create a simple tracking table.
    In production, this could be Redis or a dedicated tracking service.

    Args:
        db: Database session
        tracking_id: Tracking ID

    Returns:
        Tracking data or None
    """
    # For MVP, we'll store tracking IDs in events table
    # In production, use a dedicated tracking table or Redis

    # Try to find the most recent SENT event with this tracking_id
    event = (
        db.query(SubscriberEvent)
        .filter(
            and_(
                SubscriberEvent.event_type == EventType.SENT,
                SubscriberEvent.metadata["tracking_id"].astext == tracking_id
            )
        )
        .order_by(SubscriberEvent.created_at.desc())
        .first()
    )

    if event:
        return {
            "edition_id": int(event.metadata.get("edition_id", 0)),
            "subscriber_id": event.subscriber_id
        }

    return None