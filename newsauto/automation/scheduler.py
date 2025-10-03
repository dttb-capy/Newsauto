"""Newsletter scheduling system."""

import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional

import schedule
from sqlalchemy.orm import Session

from newsauto.email.delivery_manager import DeliveryManager
from newsauto.email.email_sender import SMTPConfig
from newsauto.generators.newsletter_generator import NewsletterGenerator
from newsauto.models.newsletter import Newsletter

logger = logging.getLogger(__name__)


class NewsletterScheduler:
    """Manages newsletter scheduling and automation."""

    def __init__(self, db: Session, smtp_config: SMTPConfig):
        """Initialize scheduler.

        Args:
            db: Database session
            smtp_config: SMTP configuration
        """
        self.db = db
        self.generator = NewsletterGenerator(db)
        self.delivery = DeliveryManager(db, smtp_config)
        self.running = False
        self.tasks: List[asyncio.Task] = []

    def schedule_newsletter(self, newsletter: Newsletter) -> bool:
        """Schedule newsletter based on its frequency.

        Args:
            newsletter: Newsletter object

        Returns:
            Success status
        """
        try:
            frequency = newsletter.frequency
            send_time = newsletter.send_time or time(9, 0)  # Default 9 AM

            # Clear existing schedule for this newsletter
            tag = f"newsletter_{newsletter.id}"
            schedule.clear(tag)

            if frequency == "daily":
                schedule.every().day.at(send_time.strftime("%H:%M")).do(
                    self._generate_and_send, newsletter_id=newsletter.id
                ).tag(tag)

            elif frequency == "weekly":
                # Send on specified day (default Monday)
                day = newsletter.settings.get("send_day", "monday")
                getattr(schedule.every(), day).at(send_time.strftime("%H:%M")).do(
                    self._generate_and_send, newsletter_id=newsletter.id
                ).tag(tag)

            elif frequency == "monthly":
                # Send on specified day of month
                day_of_month = newsletter.settings.get("send_day_of_month", 1)
                # Schedule check daily and send on the right day
                schedule.every().day.at(send_time.strftime("%H:%M")).do(
                    self._check_monthly_send,
                    newsletter_id=newsletter.id,
                    day_of_month=day_of_month,
                ).tag(tag)

            logger.info(
                f"Scheduled newsletter {newsletter.id} for {frequency} delivery"
            )
            return True

        except Exception as e:
            logger.error(f"Error scheduling newsletter {newsletter.id}: {e}")
            return False

    def _generate_and_send(self, newsletter_id: int):
        """Generate and send newsletter edition.

        Args:
            newsletter_id: Newsletter ID
        """
        asyncio.create_task(self._async_generate_and_send(newsletter_id))

    async def _async_generate_and_send(self, newsletter_id: int):
        """Async generate and send newsletter.

        Args:
            newsletter_id: Newsletter ID
        """
        try:
            # Get newsletter
            newsletter = (
                self.db.query(Newsletter)
                .filter(Newsletter.id == newsletter_id, Newsletter.status == "active")
                .first()
            )

            if not newsletter:
                logger.warning(f"Newsletter {newsletter_id} not found or inactive")
                return

            logger.info(f"Generating edition for newsletter {newsletter_id}")

            # Generate edition
            edition = self.generator.generate_edition(
                newsletter,
                test_mode=False,
                max_articles=newsletter.settings.get("max_articles", 10),
                min_score=newsletter.settings.get("min_score", 50.0),
            )

            # Send edition
            logger.info(f"Sending edition {edition.id}")
            results = await self.delivery.send_edition(edition.id)

            logger.info(
                f"Edition {edition.id} sent: "
                f"{len(results['sent'])}/{results['total']} successful"
            )

        except Exception as e:
            logger.error(
                f"Error in generate and send for newsletter {newsletter_id}: {e}"
            )

    def _check_monthly_send(self, newsletter_id: int, day_of_month: int):
        """Check if monthly newsletter should be sent today.

        Args:
            newsletter_id: Newsletter ID
            day_of_month: Day of month to send
        """
        today = datetime.now().day
        if today == day_of_month:
            self._generate_and_send(newsletter_id)

    async def start(self):
        """Start the scheduler."""
        self.running = True
        logger.info("Newsletter scheduler started")

        # Schedule all active newsletters
        newsletters = (
            self.db.query(Newsletter)
            .filter(Newsletter.status == "active", Newsletter.frequency is not None)
            .all()
        )

        for newsletter in newsletters:
            self.schedule_newsletter(newsletter)

        # Run scheduler loop
        while self.running:
            schedule.run_pending()
            await asyncio.sleep(60)  # Check every minute

    async def stop(self):
        """Stop the scheduler."""
        self.running = False
        schedule.clear()

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        logger.info("Newsletter scheduler stopped")

    def get_next_runs(self) -> List[Dict[str, Any]]:
        """Get next scheduled runs for all newsletters.

        Returns:
            List of scheduled runs
        """
        next_runs = []

        for job in schedule.jobs:
            if job.next_run:
                tags = job.tags
                newsletter_id = None

                # Extract newsletter ID from tags
                for tag in tags:
                    if tag.startswith("newsletter_"):
                        newsletter_id = int(tag.split("_")[1])
                        break

                if newsletter_id:
                    newsletter = (
                        self.db.query(Newsletter)
                        .filter(Newsletter.id == newsletter_id)
                        .first()
                    )

                    if newsletter:
                        next_runs.append(
                            {
                                "newsletter_id": newsletter_id,
                                "newsletter_name": newsletter.name,
                                "next_run": job.next_run.isoformat(),
                                "frequency": newsletter.frequency,
                            }
                        )

        return sorted(next_runs, key=lambda x: x["next_run"])


class AdvancedScheduler(NewsletterScheduler):
    """Advanced scheduler with additional features."""

    def __init__(self, db: Session, smtp_config: SMTPConfig):
        """Initialize advanced scheduler.

        Args:
            db: Database session
            smtp_config: SMTP configuration
        """
        super().__init__(db, smtp_config)
        self.content_prefetch_hours = 2  # Prefetch content 2 hours before send

    def schedule_with_optimization(self, newsletter: Newsletter) -> bool:
        """Schedule newsletter with send time optimization.

        Args:
            newsletter: Newsletter object

        Returns:
            Success status
        """
        # Get optimal send time based on engagement
        optimal_time = self._get_optimal_send_time(newsletter.id)

        if optimal_time:
            newsletter.send_time = optimal_time
            self.db.commit()

        return self.schedule_newsletter(newsletter)

    def _get_optimal_send_time(self, newsletter_id: int) -> Optional[time]:
        """Get optimal send time based on engagement data.

        Args:
            newsletter_id: Newsletter ID

        Returns:
            Optimal time or None
        """
        from sqlalchemy import func

        from newsauto.models.events import EventType, SubscriberEvent

        # Analyze open times from last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        opens = (
            self.db.query(
                func.extract("hour", SubscriberEvent.created_at).label("hour"),
                func.count(SubscriberEvent.id).label("count"),
            )
            .filter(
                SubscriberEvent.event_type == EventType.OPEN,
                SubscriberEvent.created_at >= thirty_days_ago,
            )
            .group_by("hour")
            .order_by("count")
            .all()
        )

        if opens:
            # Get hour with most opens
            best_hour = max(opens, key=lambda x: x.count).hour
            return time(int(best_hour), 0)

        return None

    def schedule_content_prefetch(self, newsletter: Newsletter):
        """Schedule content prefetching before send time.

        Args:
            newsletter: Newsletter object
        """
        # Calculate prefetch time
        send_datetime = self._get_next_send_datetime(newsletter)
        if not send_datetime:
            return

        prefetch_time = send_datetime - timedelta(hours=self.content_prefetch_hours)

        # Schedule prefetch
        schedule.every().day.at(prefetch_time.strftime("%H:%M")).do(
            self._prefetch_content, newsletter_id=newsletter.id
        ).tag(f"prefetch_{newsletter.id}")

    def _prefetch_content(self, newsletter_id: int):
        """Prefetch content for newsletter.

        Args:
            newsletter_id: Newsletter ID
        """
        asyncio.create_task(self._async_prefetch_content(newsletter_id))

    async def _async_prefetch_content(self, newsletter_id: int):
        """Async prefetch content.

        Args:
            newsletter_id: Newsletter ID
        """
        try:
            from newsauto.scrapers.aggregator import ContentAggregator

            newsletter = (
                self.db.query(Newsletter).filter(Newsletter.id == newsletter_id).first()
            )

            if not newsletter:
                return

            logger.info(f"Prefetching content for newsletter {newsletter_id}")

            aggregator = ContentAggregator(self.db)
            await aggregator.fetch_and_process(
                newsletter_id=newsletter_id, process_with_llm=True
            )

            logger.info(f"Content prefetched for newsletter {newsletter_id}")

        except Exception as e:
            logger.error(f"Error prefetching content: {e}")

    def _get_next_send_datetime(self, newsletter: Newsletter) -> Optional[datetime]:
        """Get next send datetime for newsletter.

        Args:
            newsletter: Newsletter object

        Returns:
            Next send datetime or None
        """
        now = datetime.now()
        send_time = newsletter.send_time or time(9, 0)

        if newsletter.frequency == "daily":
            # Next occurrence of send_time
            next_send = now.replace(
                hour=send_time.hour, minute=send_time.minute, second=0, microsecond=0
            )
            if next_send <= now:
                next_send += timedelta(days=1)
            return next_send

        elif newsletter.frequency == "weekly":
            # Next occurrence of send_day at send_time
            send_day = newsletter.settings.get("send_day", "monday")
            days = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6,
            }
            target_day = days.get(send_day, 0)

            days_ahead = target_day - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7

            next_send = now + timedelta(days=days_ahead)
            next_send = next_send.replace(
                hour=send_time.hour, minute=send_time.minute, second=0, microsecond=0
            )
            return next_send

        return None
