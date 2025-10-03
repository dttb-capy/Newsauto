"""Tests for database models."""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from newsauto.models.content import ContentItem
from newsauto.models.edition import Edition, EditionStatus
from newsauto.models.newsletter import Newsletter, NewsletterStatus
from newsauto.models.subscriber import NewsletterSubscriber, Subscriber
from newsauto.models.user import User


class TestUserModel:
    """Test User model."""

    def test_create_user(self, db_session):
        """Test creating a user."""
        user = User(
            email="newuser@example.com", username="newuser", full_name="New User"
        )
        user.set_password("password123")

        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.check_password("password123")
        assert not user.check_password("wrongpassword")

    def test_unique_email_constraint(self, db_session, test_user):
        """Test email uniqueness constraint."""
        duplicate_user = User(
            email=test_user.email, username="another", full_name="Another User"
        )

        db_session.add(duplicate_user)
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestNewsletterModel:
    """Test Newsletter model."""

    def test_create_newsletter(self, db_session, test_user):
        """Test creating a newsletter."""
        newsletter = Newsletter(
            name="Tech News",
            description="Latest tech news",
            user_id=test_user.id,
            settings={
                "frequency": "daily",
                "target_audience": "Tech enthusiasts",
            },
        )

        db_session.add(newsletter)
        db_session.commit()

        assert newsletter.id is not None
        assert newsletter.name == "Tech News"
        assert newsletter.subscriber_count == 0
        assert newsletter.status == NewsletterStatus.DRAFT

    def test_newsletter_relationships(self, db_session, test_newsletter):
        """Test newsletter relationships."""
        # Add subscriber
        subscriber = Subscriber(email="sub@example.com", status="active")
        db_session.add(subscriber)
        db_session.flush()

        # Create subscription
        subscription = NewsletterSubscriber(
            newsletter_id=test_newsletter.id, subscriber_id=subscriber.id
        )
        db_session.add(subscription)
        db_session.commit()

        # Test relationship
        db_session.refresh(test_newsletter)
        assert len(test_newsletter.subscribers) == 1
        assert test_newsletter.subscribers[0].subscriber_id == subscriber.id


class TestSubscriberModel:
    """Test Subscriber model."""

    def test_create_subscriber(self, db_session):
        """Test creating a subscriber."""
        subscriber = Subscriber(
            email="newsubscriber@example.com",
            name="New Subscriber",
            preferences={"topics": ["tech", "science"]},
            segments=["premium", "engaged"],
        )

        db_session.add(subscriber)
        db_session.commit()

        assert subscriber.id is not None
        assert subscriber.status == "pending"
        assert "tech" in subscriber.preferences["topics"]
        assert "premium" in subscriber.segments

    def test_subscriber_verification(self, db_session):
        """Test subscriber verification."""
        import secrets

        subscriber = Subscriber(
            email="verify@example.com", verification_token=secrets.token_urlsafe(32)
        )

        db_session.add(subscriber)
        db_session.commit()

        # Verify subscriber
        subscriber.verified_at = datetime.utcnow()
        subscriber.status = "active"
        subscriber.verification_token = None
        db_session.commit()

        assert subscriber.status == "active"
        assert subscriber.verified_at is not None
        assert subscriber.verification_token is None


class TestContentModel:
    """Test ContentItem model."""

    def test_create_content(self, db_session):
        """Test creating content item."""
        content = ContentItem(
            url="https://example.com/article",
            title="Test Article",
            author="John Doe",
            content="Full article content here",
            summary="Article summary",
            source="example.com",
            score=85.5,
            published_at=datetime.utcnow(),
        )

        db_session.add(content)
        db_session.commit()

        assert content.id is not None
        assert content.score == 85.5
        assert content.url_hash is not None

    def test_content_duplicate_detection(self, db_session):
        """Test duplicate content detection."""
        content1 = ContentItem(
            url="https://example.com/same-article",
            title="Same Article",
            content="Content",
            source="example.com",
        )

        db_session.add(content1)
        db_session.commit()

        # Try to add duplicate
        content2 = ContentItem(
            url="https://example.com/same-article",
            title="Same Article Again",
            content="Different content",
            source="other.com",
        )

        db_session.add(content2)
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestEditionModel:
    """Test Edition model."""

    def test_create_edition(self, db_session, test_newsletter):
        """Test creating newsletter edition."""
        edition = Edition(
            newsletter_id=test_newsletter.id,
            subject="Weekly Tech News",
            status=EditionStatus.DRAFT,
            content={"sections": [{"title": "Top Stories", "articles": []}]},
        )

        db_session.add(edition)
        db_session.commit()

        assert edition.id is not None
        assert edition.status == EditionStatus.DRAFT
        assert edition.edition_number == 1

    def test_edition_numbering(self, db_session, test_newsletter):
        """Test automatic edition numbering."""
        # Create first edition
        edition1 = Edition(
            newsletter_id=test_newsletter.id, status=EditionStatus.SENT, test_mode=False
        )
        db_session.add(edition1)
        db_session.commit()

        # Create second edition
        edition2 = Edition(
            newsletter_id=test_newsletter.id,
            status=EditionStatus.DRAFT,
            test_mode=False,
        )
        db_session.add(edition2)
        db_session.commit()

        assert edition1.edition_number == 1
        assert edition2.edition_number == 2

    def test_test_edition_no_numbering(self, db_session, test_newsletter):
        """Test that test editions don't get numbers."""
        edition = Edition(
            newsletter_id=test_newsletter.id, status=EditionStatus.DRAFT, test_mode=True
        )

        db_session.add(edition)
        db_session.commit()

        assert edition.edition_number is None
