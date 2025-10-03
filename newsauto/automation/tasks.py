"""Automation tasks for newsletter system."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from newsauto.llm.ollama_client import OllamaClient
from newsauto.models.content import ContentItem
from newsauto.models.edition import Edition
from newsauto.models.events import EventType, SubscriberEvent
from newsauto.models.newsletter import Newsletter
from newsauto.models.subscriber import Subscriber, SubscriberStatus
from newsauto.scrapers.aggregator import ContentAggregator

logger = logging.getLogger(__name__)


class AutomationTasks:
    """Automated tasks for newsletter system."""

    def __init__(self, db: Session):
        """Initialize automation tasks.

        Args:
            db: Database session
        """
        self.db = db
        self.aggregator = ContentAggregator(db)
        self.llm_client = OllamaClient()

    async def fetch_content_all_sources(self):
        """Fetch content from all configured sources."""
        logger.info("Starting content fetch from all sources")

        try:
            # Fetch and process content
            content = await self.aggregator.fetch_and_process(process_with_llm=True)

            logger.info(f"Fetched {len(content)} content items")

            # Clean up old content
            await self.cleanup_old_content()

            return content

        except Exception as e:
            logger.error(f"Error fetching content: {e}")
            return []

    async def cleanup_old_content(self, days: int = 7):
        """Clean up old content items.

        Args:
            days: Number of days to keep content
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Delete old content
        deleted = (
            self.db.query(ContentItem)
            .filter(ContentItem.fetched_at < cutoff_date)
            .delete()
        )

        self.db.commit()
        logger.info(f"Deleted {deleted} old content items")

    async def process_subscriber_events(self):
        """Process subscriber events and update statuses."""

        # Find inactive subscribers
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        sixty_days_ago = datetime.utcnow() - timedelta(days=60)

        # Get subscribers with no recent opens
        inactive_subscribers = (
            self.db.query(Subscriber)
            .filter(
                Subscriber.status == SubscriberStatus.ACTIVE,
                ~Subscriber.id.in_(
                    self.db.query(SubscriberEvent.subscriber_id).filter(
                        SubscriberEvent.event_type == EventType.OPEN,
                        SubscriberEvent.created_at >= sixty_days_ago,
                    )
                ),
            )
            .all()
        )

        # Update status
        for subscriber in inactive_subscribers:
            subscriber.status = SubscriberStatus.INACTIVE
            logger.info(f"Marked subscriber {subscriber.email} as inactive")

        # Find at-risk subscribers
        at_risk_subscribers = (
            self.db.query(Subscriber)
            .filter(
                Subscriber.status == SubscriberStatus.ACTIVE,
                ~Subscriber.id.in_(
                    self.db.query(SubscriberEvent.subscriber_id).filter(
                        SubscriberEvent.event_type == EventType.OPEN,
                        SubscriberEvent.created_at >= thirty_days_ago,
                    )
                ),
            )
            .all()
        )

        # Add to at-risk segment
        for subscriber in at_risk_subscribers:
            if "at_risk" not in subscriber.segments:
                subscriber.segments.append("at_risk")
                logger.info(f"Added subscriber {subscriber.email} to at-risk segment")

        self.db.commit()

    async def reactivation_campaign(self):
        """Run reactivation campaign for inactive subscribers."""
        # Get inactive subscribers
        inactive = (
            self.db.query(Subscriber)
            .filter(
                Subscriber.status == SubscriberStatus.INACTIVE,
                Subscriber.last_reactivation_attempt is None,
            )
            .limit(100)
            .all()
        )

        if not inactive:
            return

        logger.info(f"Starting reactivation campaign for {len(inactive)} subscribers")

        # TODO: Create special reactivation edition
        # TODO: Send reactivation emails

        # Update last attempt
        for subscriber in inactive:
            subscriber.last_reactivation_attempt = datetime.utcnow()

        self.db.commit()

    async def update_content_scores(self):
        """Update content scores based on engagement."""

        # Get recent content
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        content_items = (
            self.db.query(ContentItem)
            .filter(ContentItem.fetched_at >= seven_days_ago)
            .all()
        )

        for item in content_items:
            # Count clicks on this content
            # TODO: Fix JSON field access for SQLite
            clicks = 0  # Placeholder for SQLite compatibility

            # Update score based on engagement
            if clicks > 0:
                item.score = min(100, item.score + (clicks * 2))
                logger.debug(f"Updated score for {item.id}: {item.score}")

        self.db.commit()

    async def generate_analytics_report(
        self, newsletter_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate analytics report.

        Args:
            newsletter_id: Optional newsletter ID for specific report

        Returns:
            Analytics report
        """

        from newsauto.models.edition import Edition, EditionStats
        from newsauto.models.events import EventType, SubscriberEvent

        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "period": "last_30_days",
        }

        # Base filters
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        # Subscriber metrics
        total_subscribers = (
            self.db.query(func.count(Subscriber.id))
            .filter(Subscriber.status == SubscriberStatus.ACTIVE)
            .scalar()
            or 0
        )

        new_subscribers = (
            self.db.query(func.count(Subscriber.id))
            .filter(Subscriber.subscribed_at >= thirty_days_ago)
            .scalar()
            or 0
        )

        # Edition metrics
        editions_query = self.db.query(Edition).filter(
            Edition.sent_at >= thirty_days_ago, not Edition.test_mode
        )

        if newsletter_id:
            editions_query = editions_query.filter(
                Edition.newsletter_id == newsletter_id
            )

        editions_sent = editions_query.count()

        # Engagement metrics
        total_opens = (
            self.db.query(func.count(SubscriberEvent.id))
            .filter(
                SubscriberEvent.event_type == EventType.OPEN,
                SubscriberEvent.created_at >= thirty_days_ago,
            )
            .scalar()
            or 0
        )

        total_clicks = (
            self.db.query(func.count(SubscriberEvent.id))
            .filter(
                SubscriberEvent.event_type == EventType.CLICK,
                SubscriberEvent.created_at >= thirty_days_ago,
            )
            .scalar()
            or 0
        )

        # Average rates
        avg_open_rate = (
            self.db.query(func.avg(EditionStats.open_rate))
            .filter(EditionStats.created_at >= thirty_days_ago)
            .scalar()
            or 0
        )

        avg_click_rate = (
            self.db.query(func.avg(EditionStats.click_rate))
            .filter(EditionStats.created_at >= thirty_days_ago)
            .scalar()
            or 0
        )

        report.update(
            {
                "subscribers": {
                    "total": total_subscribers,
                    "new": new_subscribers,
                    "growth_rate": (
                        new_subscribers / max(total_subscribers - new_subscribers, 1)
                    )
                    * 100,
                },
                "editions": {
                    "sent": editions_sent,
                    "frequency": "daily" if editions_sent >= 25 else "weekly",
                },
                "engagement": {
                    "total_opens": total_opens,
                    "total_clicks": total_clicks,
                    "avg_open_rate": round(avg_open_rate, 2),
                    "avg_click_rate": round(avg_click_rate, 2),
                },
            }
        )

        return report

    async def optimize_send_times(self):
        """Optimize newsletter send times based on engagement."""

        from newsauto.models.events import EventType, SubscriberEvent

        newsletters = (
            self.db.query(Newsletter).filter(Newsletter.status == "active").all()
        )

        for newsletter in newsletters:
            # Analyze open times for this newsletter's editions
            opens = (
                self.db.query(
                    func.extract("hour", SubscriberEvent.created_at).label("hour"),
                    func.count(SubscriberEvent.id).label("count"),
                )
                .select_from(SubscriberEvent)
                .join(Edition, SubscriberEvent.edition_id == Edition.id)
                .filter(
                    Edition.newsletter_id == newsletter.id,
                    SubscriberEvent.event_type == EventType.OPEN,
                )
                .group_by("hour")
                .order_by("count")
                .all()
            )

            if opens and opens[0].count > 10:  # Minimum threshold
                optimal_hour = opens[0].hour
                newsletter.send_time = datetime.strptime(
                    f"{optimal_hour:02d}:00", "%H:%M"
                ).time()
                logger.info(
                    f"Updated send time for newsletter {newsletter.id} to {optimal_hour}:00"
                )

        self.db.commit()

    async def validate_subscriber_emails(self):
        """Validate subscriber email addresses."""
        from newsauto.email.email_sender import EmailValidator

        # Get unverified subscribers
        unverified = (
            self.db.query(Subscriber)
            .filter(
                Subscriber.verified_at is None,
                Subscriber.status == SubscriberStatus.PENDING,
            )
            .all()
        )

        for subscriber in unverified:
            if not EmailValidator.is_valid_email(subscriber.email):
                subscriber.status = SubscriberStatus.INVALID
                logger.warning(f"Invalid email format: {subscriber.email}")

        self.db.commit()

    async def maintain_database(self):
        """Perform database maintenance tasks."""
        # Vacuum and analyze (database-specific)
        try:
            # Check if using SQLite or PostgreSQL
            db_url = str(self.db.bind.url) if hasattr(self.db, "bind") else ""

            if "sqlite" in db_url.lower() or "sqlite" in str(type(self.db.bind)):
                # SQLite maintenance
                self.db.execute(text("VACUUM"))
                self.db.execute(text("ANALYZE"))
            else:
                # PostgreSQL maintenance
                self.db.execute(text("VACUUM ANALYZE"))

            logger.info("Database maintenance completed")
        except Exception as e:
            logger.error(f"Database maintenance error: {e}")

        # Update statistics
        from newsauto.models.subscriber import NewsletterSubscriber

        newsletters = self.db.query(Newsletter).all()
        for newsletter in newsletters:
            # Update subscriber count
            count = (
                self.db.query(NewsletterSubscriber)
                .filter(
                    NewsletterSubscriber.newsletter_id == newsletter.id,
                    NewsletterSubscriber.unsubscribed_at is None,
                )
                .count()
            )

            newsletter.subscriber_count = count

        self.db.commit()


class TaskRunner:
    """Runs automation tasks on schedule."""

    def __init__(self, db: Session):
        """Initialize task runner.

        Args:
            db: Database session
        """
        self.db = db
        self.tasks = AutomationTasks(db)
        self.running = False

    async def start(self):
        """Start task runner."""
        self.running = True
        logger.info("Task runner started")

        # Schedule tasks
        asyncio.create_task(self._run_hourly_tasks())
        asyncio.create_task(self._run_daily_tasks())
        asyncio.create_task(self._run_weekly_tasks())

    async def stop(self):
        """Stop task runner."""
        self.running = False
        logger.info("Task runner stopped")

    async def _run_hourly_tasks(self):
        """Run hourly tasks."""
        while self.running:
            try:
                await self.tasks.fetch_content_all_sources()
                await self.tasks.update_content_scores()
            except Exception as e:
                logger.error(f"Error in hourly tasks: {e}")

            await asyncio.sleep(3600)  # 1 hour

    async def _run_daily_tasks(self):
        """Run daily tasks."""
        while self.running:
            try:
                await self.tasks.process_subscriber_events()
                await self.tasks.validate_subscriber_emails()
                await self.tasks.cleanup_old_content()
                await self.tasks.optimize_send_times()
                await self.tasks.maintain_database()
            except Exception as e:
                logger.error(f"Error in daily tasks: {e}")

            await asyncio.sleep(86400)  # 24 hours

    async def _run_weekly_tasks(self):
        """Run weekly tasks."""
        while self.running:
            try:
                await self.tasks.reactivation_campaign()
                report = await self.tasks.generate_analytics_report()
                logger.info(f"Weekly report generated: {report}")
            except Exception as e:
                logger.error(f"Error in weekly tasks: {e}")

            await asyncio.sleep(604800)  # 7 days
