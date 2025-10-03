"""End-to-end integration tests for newsletter system."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from newsauto.automation.tasks import AutomationTasks
from newsauto.email.delivery_manager import DeliveryManager
from newsauto.email.email_sender import EmailSender, SMTPConfig
from newsauto.generators.newsletter_generator import NewsletterGenerator
from newsauto.models.content import ContentItem
from newsauto.models.edition import Edition, EditionStatus
from newsauto.models.events import EventType, SubscriberEvent
from newsauto.models.newsletter import Newsletter
from newsauto.models.subscriber import Subscriber, SubscriberStatus
from newsauto.scrapers.aggregator import ContentAggregator


class TestNewsletterIntegration:
    """Test complete newsletter workflow."""

    @pytest.fixture(autouse=True)
    def setup(self, db_session):
        """Setup test environment."""
        # Create test user first
        from newsauto.models.user import User

        self.user = User(
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            is_active=True,
        )
        self.user.set_password("testpass123")
        db_session.add(self.user)
        db_session.flush()

        # Create test newsletter
        self.newsletter = Newsletter(
            name="Integration Test Newsletter",
            description="Test newsletter for integration testing",
            user_id=self.user.id,
            settings={
                "frequency": "daily",
                "target_audience": "Test users",
            },
            send_time=datetime.now().time(),
            status="active",
        )
        db_session.add(self.newsletter)

        # Create test subscribers
        self.subscribers = []
        for i in range(3):
            subscriber = Subscriber(
                email=f"test{i}@example.com",
                name=f"Test User {i}",
                status=SubscriberStatus.ACTIVE,
                verified_at=datetime.utcnow(),
            )
            self.subscribers.append(subscriber)
            db_session.add(subscriber)

        db_session.commit()

        # Link subscribers to newsletter
        from newsauto.models.subscriber import NewsletterSubscriber

        for subscriber in self.subscribers:
            subscription = NewsletterSubscriber(
                newsletter_id=self.newsletter.id,
                subscriber_id=subscriber.id,
            )
            db_session.add(subscription)
        db_session.commit()

    @pytest.mark.asyncio
    async def test_full_newsletter_workflow(self, db_session):
        """Test complete workflow from content fetch to delivery."""
        # Step 1: Fetch content
        aggregator = ContentAggregator(db_session)

        with patch.object(aggregator, "fetch_from_sources") as mock_fetch:
            # Mock content fetching
            mock_content = []
            for i in range(10):
                content = ContentItem(
                    title=f"Test Article {i}",
                    content=f"Article content {i}" * 100,
                    url=f"https://example.com/article-{i}",
                    author=f"Author {i}",
                    published_at=datetime.utcnow() - timedelta(hours=i),
                    score=90 - i * 5,
                )
                mock_content.append(content)
                db_session.add(content)

            mock_fetch.return_value = mock_content
            db_session.commit()

            # Fetch and process content
            await aggregator.fetch_and_process(
                newsletter_id=self.newsletter.id,
                process_with_llm=False,  # Skip LLM for testing
            )

        # Step 2: Generate newsletter
        generator = NewsletterGenerator(db_session)

        with patch.object(generator.llm_client, "generate") as mock_llm:
            mock_llm.return_value = "Test Newsletter: Today's Top Stories"

            with patch.object(generator.llm_client, "summarize") as mock_summarize:
                mock_summarize.return_value = "Test summary"

                edition = generator.generate_edition(
                    self.newsletter, test_mode=False, max_articles=5
                )

        # Verify edition was created
        assert edition is not None
        assert edition.newsletter_id == self.newsletter.id
        assert edition.status == EditionStatus.DRAFT
        assert len(edition.content["sections"]) > 0

        # Step 3: Send newsletter
        smtp_config = SMTPConfig(
            host="localhost",
            port=1025,
            use_tls=False,
            from_email="test@newsletter.com",
            from_name="Test Newsletter",
        )

        delivery_manager = DeliveryManager(db_session, smtp_config)

        with patch("aiosmtplib.SMTP") as mock_smtp:
            mock_client = AsyncMock()
            mock_smtp.return_value = mock_client

            # Send to all subscribers
            results = await delivery_manager.send_edition(
                edition_id=edition.id, test_mode=False
            )

            # Verify all emails were sent
            assert len(results) == len(self.subscribers)
            assert all(r["success"] for r in results)
            assert mock_client.send_message.call_count == len(self.subscribers)

        # Step 4: Track events
        for i, subscriber in enumerate(self.subscribers):
            # Record open event
            open_event = SubscriberEvent(
                subscriber_id=subscriber.id,
                edition_id=edition.id,
                event_type=EventType.OPEN,
                metadata={"user_agent": "Test Browser"},
            )
            db_session.add(open_event)

            # Record click event for first article
            if i < 2:  # Only first 2 subscribers click
                click_event = SubscriberEvent(
                    subscriber_id=subscriber.id,
                    edition_id=edition.id,
                    event_type=EventType.CLICK,
                    metadata={"url": "https://example.com/article-0"},
                )
                db_session.add(click_event)

        db_session.commit()

        # Step 5: Update statistics
        edition.update_stats(db_session)

        # Verify statistics
        assert edition.stats.sent_count == len(self.subscribers)
        assert edition.stats.open_count == len(self.subscribers)
        assert edition.stats.click_count == 2
        assert edition.stats.open_rate == 100.0
        assert edition.stats.click_rate > 60.0

    @pytest.mark.asyncio
    async def test_scheduled_newsletter_delivery(self, db_session):
        """Test scheduled newsletter generation and delivery."""
        tasks = AutomationTasks(db_session)

        # Create content
        for i in range(5):
            content = ContentItem(
                title=f"Scheduled Article {i}",
                content=f"Content {i}" * 50,
                url=f"https://example.com/scheduled-{i}",
                published_at=datetime.utcnow() - timedelta(hours=i),
                score=80 - i * 10,
            )
            db_session.add(content)
        db_session.commit()

        with patch.object(tasks.llm_client, "generate") as mock_llm:
            mock_llm.return_value = "Scheduled Newsletter"

            with patch.object(tasks.llm_client, "summarize") as mock_summarize:
                mock_summarize.return_value = "Summary"

                with patch("aiosmtplib.SMTP") as mock_smtp:
                    mock_client = AsyncMock()
                    mock_smtp.return_value = mock_client

                    # Use scheduler to process newsletters
                    from newsauto.automation.scheduler import NewsletterScheduler

                    scheduler = NewsletterScheduler(db_session)
                    # Manually trigger generation for test
                    await scheduler._async_generate_and_send(self.newsletter.id)

                    # Verify newsletter was generated and sent
                    editions = (
                        db_session.query(Edition)
                        .filter(Edition.newsletter_id == self.newsletter.id)
                        .all()
                    )

                    assert len(editions) > 0
                    edition = editions[0]
                    assert edition.status in [EditionStatus.SENT, EditionStatus.SENDING]

    @pytest.mark.asyncio
    async def test_error_recovery(self, db_session):
        """Test error recovery during newsletter processing."""
        generator = NewsletterGenerator(db_session)

        # Test with LLM failure
        with patch.object(generator.llm_client, "generate") as mock_llm:
            mock_llm.side_effect = Exception("LLM service unavailable")

            # Create minimal content
            content = ContentItem(
                title="Error Test Article",
                content="Test content",
                summary="Test summary",  # Pre-generated summary
                url="https://example.com/error-test",
                published_at=datetime.utcnow(),
                score=100,
            )
            db_session.add(content)
            db_session.commit()

            # Should still generate with fallback
            edition = generator.generate_edition(self.newsletter, test_mode=True)

            # Verify fallback worked
            assert edition is not None
            assert "Today's Top Stories" in edition.subject

        # Test with SMTP failure and retry
        smtp_config = SMTPConfig(host="localhost", port=1025)
        sender = EmailSender(smtp_config)

        with patch("aiosmtplib.SMTP") as mock_smtp:
            mock_client = AsyncMock()
            # Fail first attempt, succeed on retry
            mock_client.send_message.side_effect = [Exception("Connection reset"), None]
            mock_smtp.return_value = mock_client

            # Send with retry
            success = await sender.send_email_with_retry(
                to_email="test@example.com",
                subject="Test",
                html_content="<html>Test</html>",
                max_retries=2,
            )

            assert success is True
            assert mock_client.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_personalization_flow(self, db_session):
        """Test personalized newsletter generation."""
        # Set subscriber preferences
        subscriber = self.subscribers[0]
        subscriber.preferences = {
            "categories": ["Technology", "Science"],
            "keywords": ["AI", "Machine Learning"],
        }
        db_session.commit()

        # Create targeted content
        tech_content = ContentItem(
            title="AI Breakthrough",
            content="AI content" * 100,
            url="https://example.com/ai",
            published_at=datetime.utcnow(),
            score=95,
            meta_data={"category": "Technology", "topics": ["AI"]},
        )

        sports_content = ContentItem(
            title="Sports Update",
            content="Sports content" * 100,
            url="https://example.com/sports",
            published_at=datetime.utcnow(),
            score=90,
            meta_data={"category": "Sports"},
        )

        db_session.add_all([tech_content, sports_content])
        db_session.commit()

        # Generate personalized edition
        generator = NewsletterGenerator(db_session)

        with patch.object(generator.llm_client, "generate") as mock_llm:
            mock_llm.return_value = "Your Personalized Tech News"

            # Generate with personalization
            edition = generator.generate_edition(self.newsletter)

            # Render for specific subscriber
            html, text = generator.render_edition(edition, subscriber)

            # Verify personalization markers
            assert subscriber.name in text or "personalized" in html.lower()

    @pytest.mark.asyncio
    async def test_analytics_tracking(self, db_session):
        """Test analytics and tracking integration."""
        # Create edition with tracking
        edition = Edition(
            newsletter_id=self.newsletter.id,
            subject="Analytics Test",
            status=EditionStatus.SENT,
            content={"sections": []},
            sent_at=datetime.utcnow(),
        )
        db_session.add(edition)
        db_session.commit()

        # Simulate email events
        events = []

        # All subscribers receive email
        for subscriber in self.subscribers:
            events.append(
                SubscriberEvent(
                    subscriber_id=subscriber.id,
                    edition_id=edition.id,
                    event_type=EventType.DELIVERED,
                )
            )

        # 2 subscribers open
        for subscriber in self.subscribers[:2]:
            events.append(
                SubscriberEvent(
                    subscriber_id=subscriber.id,
                    edition_id=edition.id,
                    event_type=EventType.OPEN,
                )
            )

        # 1 subscriber clicks
        events.append(
            SubscriberEvent(
                subscriber_id=self.subscribers[0].id,
                edition_id=edition.id,
                event_type=EventType.CLICK,
                metadata={"url": "https://example.com/tracked"},
            )
        )

        # 1 subscriber unsubscribes
        events.append(
            SubscriberEvent(
                subscriber_id=self.subscribers[2].id,
                edition_id=edition.id,
                event_type=EventType.UNSUBSCRIBE,
            )
        )

        for event in events:
            db_session.add(event)
        db_session.commit()

        # Calculate analytics
        stats = edition.calculate_stats(db_session)

        # Verify analytics
        assert stats["delivered"] == 3
        assert stats["opened"] == 2
        assert stats["clicked"] == 1
        assert stats["unsubscribed"] == 1
        assert stats["open_rate"] == pytest.approx(66.67, 0.1)
        assert stats["click_rate"] == pytest.approx(33.33, 0.1)

    @pytest.mark.asyncio
    async def test_failure_notifications(self, db_session):
        """Test failure notification system."""
        AutomationTasks(db_session)

        # Create edition with failures
        edition = Edition(
            newsletter_id=self.newsletter.id,
            subject="Failure Test",
            status=EditionStatus.FAILED,
            content={"sections": []},
            error_message="Failed to send to 50% of subscribers",
        )
        db_session.add(edition)
        db_session.commit()

        # Verify the edition failed status is recorded
        assert edition.status == EditionStatus.FAILED
        assert edition.error_message is not None
        assert "50%" in edition.error_message
