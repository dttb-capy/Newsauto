"""Email tracking functionality."""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from newsauto.models.edition import EditionStats
from newsauto.models.events import EventType, SubscriberEvent

logger = logging.getLogger(__name__)


class EmailTracker:
    """Email tracking service."""

    def __init__(self, db: Session):
        """Initialize email tracker.

        Args:
            db: Database session
        """
        self.db = db

    def track_open(
        self,
        tracking_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Track email open.

        Args:
            tracking_id: Tracking identifier
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Success status
        """
        try:
            # Decode tracking ID to get subscriber and edition
            subscriber_id, edition_id = self._decode_tracking_id(tracking_id)

            # Check if already opened
            existing = (
                self.db.query(SubscriberEvent)
                .filter(
                    SubscriberEvent.subscriber_id == subscriber_id,
                    SubscriberEvent.event_type == EventType.OPEN,
                    SubscriberEvent.meta_data["edition_id"].astext == str(edition_id),
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
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "first_open": True,
                    },
                )
                self.db.add(event)

                # Update edition stats
                self._update_edition_stats(edition_id, "opened")

            else:
                # Log repeat open
                event = SubscriberEvent(
                    subscriber_id=subscriber_id,
                    event_type=EventType.OPEN,
                    metadata={
                        "edition_id": edition_id,
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "first_open": False,
                    },
                )
                self.db.add(event)

            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Error tracking open: {e}")
            return False

    def track_click(
        self,
        tracking_id: str,
        url: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """Track link click.

        Args:
            tracking_id: Tracking identifier
            url: Clicked URL
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Success status
        """
        try:
            # Decode tracking ID
            subscriber_id, edition_id = self._decode_tracking_id(tracking_id)

            # Log click event
            event = SubscriberEvent(
                subscriber_id=subscriber_id,
                event_type=EventType.CLICK,
                metadata={
                    "edition_id": edition_id,
                    "url": url,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                },
            )
            self.db.add(event)

            # Track unique clicks
            unique_click = (
                self.db.query(SubscriberEvent)
                .filter(
                    SubscriberEvent.subscriber_id == subscriber_id,
                    SubscriberEvent.event_type == EventType.CLICK,
                    SubscriberEvent.meta_data["edition_id"].astext == str(edition_id),
                )
                .count()
                == 0
            )

            if unique_click:
                self._update_edition_stats(edition_id, "clicked")

            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Error tracking click: {e}")
            return False

    def track_bounce(
        self, email: str, bounce_type: str, bounce_reason: Optional[str] = None
    ) -> bool:
        """Track email bounce.

        Args:
            email: Bounced email address
            bounce_type: Type of bounce (hard/soft)
            bounce_reason: Bounce reason

        Returns:
            Success status
        """
        try:
            from newsauto.models.subscriber import Subscriber

            # Find subscriber
            subscriber = (
                self.db.query(Subscriber).filter(Subscriber.email == email).first()
            )

            if not subscriber:
                logger.warning(f"Subscriber not found for bounce: {email}")
                return False

            # Log bounce event
            event = SubscriberEvent(
                subscriber_id=subscriber.id,
                event_type=EventType.BOUNCE,
                metadata={"bounce_type": bounce_type, "bounce_reason": bounce_reason},
            )
            self.db.add(event)

            # Update subscriber status for hard bounces
            if bounce_type == "hard":
                subscriber.status = "bounced"
                subscriber.bounce_count = (subscriber.bounce_count or 0) + 1

            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Error tracking bounce: {e}")
            return False

    def track_complaint(self, email: str, complaint_type: Optional[str] = None) -> bool:
        """Track spam complaint.

        Args:
            email: Complainer's email address
            complaint_type: Type of complaint

        Returns:
            Success status
        """
        try:
            from newsauto.models.subscriber import Subscriber

            # Find subscriber
            subscriber = (
                self.db.query(Subscriber).filter(Subscriber.email == email).first()
            )

            if not subscriber:
                logger.warning(f"Subscriber not found for complaint: {email}")
                return False

            # Log complaint event
            event = SubscriberEvent(
                subscriber_id=subscriber.id,
                event_type=EventType.COMPLAINT,
                metadata={"complaint_type": complaint_type},
            )
            self.db.add(event)

            # Update subscriber status
            subscriber.status = "complained"
            subscriber.complaint_count = (subscriber.complaint_count or 0) + 1

            self.db.commit()
            return True

        except Exception as e:
            logger.error(f"Error tracking complaint: {e}")
            return False

    def _decode_tracking_id(self, tracking_id: str) -> tuple[int, int]:
        """Decode tracking ID.

        Args:
            tracking_id: Tracking identifier

        Returns:
            Tuple of (subscriber_id, edition_id)
        """
        # TODO: Implement proper decoding with encryption
        # For now, simple placeholder
        parts = tracking_id.split(":")
        if len(parts) >= 2:
            return int(parts[0]), int(parts[1])
        raise ValueError(f"Invalid tracking ID: {tracking_id}")

    def _update_edition_stats(self, edition_id: int, stat_type: str):
        """Update edition statistics.

        Args:
            edition_id: Edition ID
            stat_type: Statistic type (opened, clicked, etc.)
        """
        stats = (
            self.db.query(EditionStats)
            .filter(EditionStats.edition_id == edition_id)
            .first()
        )

        if not stats:
            stats = EditionStats(edition_id=edition_id)
            self.db.add(stats)

        if stat_type == "opened":
            stats.opened_count = (stats.opened_count or 0) + 1
        elif stat_type == "clicked":
            stats.clicked_count = (stats.clicked_count or 0) + 1

        # Calculate rates
        if stats.sent_count > 0:
            stats.open_rate = (stats.opened_count / stats.sent_count) * 100
            stats.click_rate = (stats.clicked_count / stats.sent_count) * 100

    def get_edition_stats(self, edition_id: int) -> Dict[str, Any]:
        """Get edition statistics.

        Args:
            edition_id: Edition ID

        Returns:
            Statistics dictionary
        """
        stats = (
            self.db.query(EditionStats)
            .filter(EditionStats.edition_id == edition_id)
            .first()
        )

        if not stats:
            return {
                "sent": 0,
                "delivered": 0,
                "opened": 0,
                "clicked": 0,
                "bounced": 0,
                "complained": 0,
                "open_rate": 0,
                "click_rate": 0,
            }

        # Get additional stats from events
        bounce_count = (
            self.db.query(func.count(SubscriberEvent.id))
            .filter(
                SubscriberEvent.event_type == EventType.BOUNCE,
                SubscriberEvent.meta_data["edition_id"].astext == str(edition_id),
            )
            .scalar()
            or 0
        )

        complaint_count = (
            self.db.query(func.count(SubscriberEvent.id))
            .filter(
                SubscriberEvent.event_type == EventType.COMPLAINT,
                SubscriberEvent.meta_data["edition_id"].astext == str(edition_id),
            )
            .scalar()
            or 0
        )

        return {
            "sent": stats.sent_count,
            "delivered": stats.delivered_count,
            "opened": stats.opened_count,
            "clicked": stats.clicked_count,
            "bounced": bounce_count,
            "complained": complaint_count,
            "open_rate": stats.open_rate or 0,
            "click_rate": stats.click_rate or 0,
        }

    def get_subscriber_engagement(
        self, subscriber_id: int, days: int = 90
    ) -> Dict[str, Any]:
        """Get subscriber engagement metrics.

        Args:
            subscriber_id: Subscriber ID
            days: Number of days to analyze

        Returns:
            Engagement metrics
        """
        from datetime import timedelta

        since = datetime.utcnow() - timedelta(days=days)

        # Count events by type
        events = (
            self.db.query(
                SubscriberEvent.event_type,
                func.count(SubscriberEvent.id).label("count"),
            )
            .filter(
                SubscriberEvent.subscriber_id == subscriber_id,
                SubscriberEvent.created_at >= since,
            )
            .group_by(SubscriberEvent.event_type)
            .all()
        )

        event_counts = {event.event_type: event.count for event in events}

        # Calculate engagement score
        opens = event_counts.get(EventType.OPEN, 0)
        clicks = event_counts.get(EventType.CLICK, 0)
        bounces = event_counts.get(EventType.BOUNCE, 0)
        complaints = event_counts.get(EventType.COMPLAINT, 0)

        score = (opens * 1 + clicks * 3) - (bounces * 5 + complaints * 10)
        score = max(0, score)  # Don't go negative

        return {
            "opens": opens,
            "clicks": clicks,
            "bounces": bounces,
            "complaints": complaints,
            "engagement_score": score,
            "is_engaged": score > 5,
            "is_at_risk": score <= 1,
        }
