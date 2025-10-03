"""Email delivery management."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from newsauto.email.email_sender import EmailSender, SMTPConfig
from newsauto.generators.newsletter_generator import NewsletterGenerator
from newsauto.generators.personalization import SegmentationEngine
from newsauto.models.edition import Edition, EditionStats, EditionStatus
from newsauto.models.events import EventType, SubscriberEvent
from newsauto.models.subscriber import NewsletterSubscriber, Subscriber
from newsauto.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DeliveryManager:
    """Manages newsletter delivery."""

    def __init__(
        self,
        db: Session,
        smtp_config: SMTPConfig,
        newsletter_generator: Optional[NewsletterGenerator] = None,
    ):
        """Initialize delivery manager.

        Args:
            db: Database session
            smtp_config: SMTP configuration
            newsletter_generator: Newsletter generator
        """
        self.db = db
        self.email_sender = EmailSender(smtp_config)
        self.newsletter_generator = newsletter_generator or NewsletterGenerator(db)
        self.segmentation = SegmentationEngine(db)

    async def send_edition(
        self,
        edition_id: int,
        test_mode: bool = False,
        test_emails: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Send newsletter edition.

        Args:
            edition_id: Edition ID
            test_mode: Whether this is a test send
            test_emails: List of test email addresses

        Returns:
            Sending results
        """
        # Get edition
        edition = self.db.query(Edition).filter(Edition.id == edition_id).first()

        if not edition:
            raise ValueError(f"Edition {edition_id} not found")

        if edition.status == EditionStatus.SENT and not test_mode:
            raise ValueError(f"Edition {edition_id} already sent")

        newsletter = edition.newsletter

        # Get recipients
        if test_mode and test_emails:
            recipients = self._get_test_recipients(test_emails)
        else:
            recipients = self._get_recipients(newsletter.id)

        if not recipients:
            raise ValueError("No recipients available")

        logger.info(f"Sending edition {edition_id} to {len(recipients)} recipients")

        # Update edition status
        if not test_mode:
            edition.status = EditionStatus.SENDING
            self.db.commit()

        # Initialize stats
        stats = EditionStats(edition_id=edition_id, sent_count=0, delivered_count=0)

        # Send emails
        results = {"sent": [], "failed": [], "total": len(recipients)}

        # Process in batches
        batch_size = 50
        for i in range(0, len(recipients), batch_size):
            batch = recipients[i : i + batch_size]

            # Send batch
            batch_results = await self._send_batch(edition, batch, test_mode)

            results["sent"].extend(batch_results["sent"])
            results["failed"].extend(batch_results["failed"])
            stats.sent_count += len(batch_results["sent"])

            # Update progress
            if not test_mode and i % 200 == 0:
                self.db.add(stats)
                self.db.commit()

        # Finalize
        if not test_mode:
            edition.status = EditionStatus.SENT
            edition.sent_at = datetime.utcnow()

            # Save final stats
            stats.delivered_count = stats.sent_count  # Will be updated by tracking
            self.db.add(stats)
            self.db.commit()

        logger.info(f"Edition {edition_id} sent: {stats.sent_count}/{results['total']}")

        return results

    async def _send_batch(
        self, edition: Edition, recipients: List[Subscriber], test_mode: bool
    ) -> Dict[str, List[str]]:
        """Send edition to batch of recipients.

        Args:
            edition: Edition object
            recipients: List of subscribers
            test_mode: Whether this is a test send

        Returns:
            Batch results
        """
        results = {"sent": [], "failed": []}
        tasks = []

        for subscriber in recipients:
            # Render personalized content
            html_content, text_content = self.newsletter_generator.render_edition(
                edition, subscriber
            )

            # Add tracking
            if not test_mode:
                tracking_id = self._create_tracking_id(edition.id, subscriber.id)
                html_content = self._add_tracking(html_content, tracking_id)

            # Create send task
            task = self.email_sender.send_email(
                to_email=subscriber.email,
                subject=edition.subject or "Newsletter",
                html_content=html_content,
                text_content=text_content,
                headers={
                    "List-Unsubscribe": f"<{settings.unsubscribe_base_url}/{tracking_id}>",
                    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
                    "X-Newsletter-ID": str(edition.newsletter_id),
                    "X-Edition-ID": str(edition.id),
                },
            )

            tasks.append((subscriber.email, task))

        # Execute all tasks
        for email, task in tasks:
            try:
                success = await task
                if success:
                    results["sent"].append(email)

                    # Log event
                    if not test_mode:
                        subscriber = next(s for s in recipients if s.email == email)
                        # Include tracking_id in event metadata
                        tracking_id = self._create_tracking_id(edition.id, subscriber.id)
                        self._log_event(
                            subscriber.id,
                            edition.id,
                            EventType.SENT,
                            {"tracking_id": tracking_id}
                        )
                else:
                    results["failed"].append(email)

            except Exception as e:
                logger.error(f"Error sending to {email}: {e}")
                results["failed"].append(email)

        return results

    def _get_recipients(self, newsletter_id: int) -> List[Subscriber]:
        """Get newsletter recipients.

        Args:
            newsletter_id: Newsletter ID

        Returns:
            List of subscribers
        """
        return (
            self.db.query(Subscriber)
            .join(NewsletterSubscriber)
            .filter(
                NewsletterSubscriber.newsletter_id == newsletter_id,
                NewsletterSubscriber.unsubscribed_at is None,
                Subscriber.status == "active",
                Subscriber.verified_at is not None,
            )
            .all()
        )

    def _get_test_recipients(self, emails: List[str]) -> List[Subscriber]:
        """Create test recipient objects.

        Args:
            emails: List of email addresses

        Returns:
            List of test subscribers
        """
        recipients = []
        for email in emails:
            # Check if subscriber exists
            subscriber = (
                self.db.query(Subscriber).filter(Subscriber.email == email).first()
            )

            if not subscriber:
                # Create temporary subscriber object
                subscriber = Subscriber(
                    email=email,
                    name="Test User",
                    status="active",
                    verified_at=datetime.utcnow(),
                )

            recipients.append(subscriber)

        return recipients

    def _create_tracking_id(self, edition_id: int, subscriber_id: int) -> str:
        """Create tracking identifier.

        Args:
            edition_id: Edition ID
            subscriber_id: Subscriber ID

        Returns:
            Tracking ID
        """
        import hashlib
        import secrets

        data = f"{edition_id}:{subscriber_id}:{secrets.token_hex(8)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _add_tracking(self, html_content: str, tracking_id: str) -> str:
        """Add tracking to HTML content.

        Args:
            html_content: HTML content
            tracking_id: Tracking ID

        Returns:
            HTML with tracking
        """
        from newsauto.email.email_sender import EmailBuilder

        # Add open tracking pixel
        html_content = EmailBuilder.add_tracking_pixel(
            html_content,
            tracking_id,
            settings.tracking_base_url,
        )

        # Add click tracking
        html_content = EmailBuilder.add_click_tracking(
            html_content,
            tracking_id,
            settings.tracking_base_url,
        )

        return html_content

    def _log_event(
        self,
        subscriber_id: int,
        edition_id: int,
        event_type: EventType,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log subscriber event.

        Args:
            subscriber_id: Subscriber ID
            edition_id: Edition ID
            event_type: Event type
            metadata: Optional event metadata
        """
        event = SubscriberEvent(
            subscriber_id=subscriber_id,
            event_type=event_type,
            metadata={"edition_id": edition_id, **(metadata or {})},
        )
        self.db.add(event)
        self.db.commit()

    async def process_scheduled_sends(self):
        """Process scheduled newsletter sends."""
        now = datetime.utcnow()

        # Find scheduled editions
        scheduled = (
            self.db.query(Edition)
            .filter(
                Edition.status == EditionStatus.SCHEDULED,
                Edition.scheduled_for <= now,
                not Edition.test_mode,
            )
            .all()
        )

        for edition in scheduled:
            try:
                logger.info(f"Processing scheduled edition {edition.id}")
                await self.send_edition(edition.id)
            except Exception as e:
                logger.error(f"Failed to send scheduled edition {edition.id}: {e}")
                edition.status = EditionStatus.FAILED
                self.db.commit()

    async def resend_failed(self, edition_id: int) -> Dict[str, Any]:
        """Resend to failed recipients.

        Args:
            edition_id: Edition ID

        Returns:
            Resend results
        """
        # Get failed recipients
        stats = (
            self.db.query(EditionStats)
            .filter(EditionStats.edition_id == edition_id)
            .first()
        )

        if not stats:
            raise ValueError(f"No stats found for edition {edition_id}")

        # Get subscribers who didn't receive the email
        sent_events = (
            self.db.query(SubscriberEvent.subscriber_id)
            .filter(
                and_(
                    SubscriberEvent.event_type == EventType.SENT,
                    SubscriberEvent.meta_data["edition_id"].astext == str(edition_id),
                )
            )
            .subquery()
        )

        failed_subscribers = (
            self.db.query(Subscriber)
            .join(NewsletterSubscriber)
            .filter(
                NewsletterSubscriber.newsletter_id == Edition.newsletter_id,
                ~Subscriber.id.in_(sent_events),
                Subscriber.status == "active",
            )
            .all()
        )

        if not failed_subscribers:
            return {"sent": [], "failed": [], "total": 0}

        # Resend to failed recipients
        edition = self.db.query(Edition).filter(Edition.id == edition_id).first()

        results = await self._send_batch(edition, failed_subscribers, test_mode=False)

        # Update stats
        stats.sent_count += len(results["sent"])
        self.db.commit()

        return results
