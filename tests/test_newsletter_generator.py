"""Test suite for newsletter generation."""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from newsauto.generators.newsletter_generator import NewsletterGenerator
from newsauto.models.content import ContentItem
from newsauto.models.edition import Edition, EditionStatus
from newsauto.models.newsletter import Newsletter
from newsauto.models.subscriber import Subscriber


@pytest.fixture
def mock_newsletter():
    """Create a mock newsletter."""
    newsletter = Mock(spec=Newsletter)
    newsletter.id = 1
    newsletter.name = "Test Newsletter"
    newsletter.description = "A test newsletter"
    newsletter.settings = {
        "frequency": "daily",
        "target_audience": "Tech enthusiasts",
    }
    newsletter.send_time = datetime.now().time()
    newsletter.status = "active"
    # Add properties for backward compatibility
    newsletter.frequency = "daily"
    newsletter.target_audience = "Tech enthusiasts"
    return newsletter


@pytest.fixture
def mock_content_items():
    """Create mock content items."""
    items = []
    for i in range(5):
        item = Mock(spec=ContentItem)
        item.id = i + 1
        item.title = f"Test Article {i + 1}"
        item.content = f"Content for article {i + 1}" * 50
        item.summary = f"Summary for article {i + 1}"
        item.url = f"https://example.com/article-{i + 1}"
        item.author = f"Author {i + 1}"
        item.published_at = datetime.utcnow() - timedelta(hours=i)
        item.fetched_at = datetime.utcnow()
        item.score = 80.0 - (i * 5)
        item.processed_at = datetime.utcnow() if i < 3 else None
        item.meta_data = {
            "category": ["Technology", "Business", "Science"][i % 3],
            "topics": ["AI", "Machine Learning", "Data Science"],
            "sentiment": "positive",
        }
        items.append(item)
    return items


@pytest.fixture
def generator(db_session):
    """Create a NewsletterGenerator instance."""
    mock_llm = Mock()
    mock_llm.summarize.return_value = "Test summary"
    mock_llm.classify_content.return_value = {
        "category": "Technology",
        "topics": ["AI", "ML"],
        "sentiment": "positive",
    }
    mock_llm.generate.return_value = "Test Newsletter: Top Stories Today"

    return NewsletterGenerator(db_session, llm_client=mock_llm)


class TestNewsletterGenerator:
    """Test newsletter generation functionality."""

    def test_generate_edition(
        self, generator, mock_newsletter, mock_content_items, db_session
    ):
        """Test edition generation."""
        # Setup mock query responses
        db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
            mock_content_items
        )
        db_session.query.return_value.filter.return_value.first.return_value = (
            mock_newsletter
        )

        # Generate edition
        edition = generator.generate_edition(
            mock_newsletter, test_mode=True, max_articles=3
        )

        # Verify edition properties
        assert edition.newsletter_id == 1
        assert edition.status == EditionStatus.DRAFT
        assert edition.test_mode is True
        assert edition.subject is not None
        assert "sections" in edition.content

        # Verify database operations
        db_session.add.assert_called()
        db_session.commit.assert_called()

    def test_fetch_content_daily(
        self, generator, mock_newsletter, mock_content_items, db_session
    ):
        """Test content fetching for daily newsletter."""
        mock_newsletter.frequency = "daily"

        # Setup mock query
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.all.return_value = mock_content_items
        db_session.query.return_value = query_mock

        # Fetch content
        content = generator.fetch_content(mock_newsletter, min_score=50.0)

        # Verify results
        assert len(content) == 5
        assert all(isinstance(item, Mock) for item in content)

        # Verify query was filtered for last 24 hours
        db_session.query.assert_called_with(ContentItem)

    def test_fetch_content_insufficient(self, generator, mock_newsletter, db_session):
        """Test content fetching with insufficient content triggers fresh fetch."""
        # Setup mock query with few results
        query_mock = Mock()
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.limit.return_value = query_mock
        query_mock.all.return_value = []  # No content initially
        db_session.query.return_value = query_mock

        # Mock aggregator
        with patch.object(generator.aggregator, "fetch_and_process") as mock_fetch:
            # After fetch, return some content
            query_mock.all.side_effect = [[], mock_content_items[:3]]

            # Fetch content
            generator.fetch_content(mock_newsletter)

            # Verify fresh fetch was triggered
            mock_fetch.assert_called_once_with(
                newsletter_id=mock_newsletter.id, process_with_llm=True
            )

    def test_process_content(
        self, generator, mock_content_items, mock_newsletter, db_session
    ):
        """Test content processing with LLM."""
        # Process content
        processed = generator.process_content(mock_content_items, mock_newsletter)

        # Verify all items were processed
        assert len(processed) == len(mock_content_items)

        # Verify LLM was called for unprocessed items
        unprocessed_count = sum(
            1 for item in mock_content_items if not item.processed_at
        )
        assert generator.llm_client.summarize.call_count >= unprocessed_count

    def test_generate_subject(self, generator, mock_content_items, mock_newsletter):
        """Test subject line generation."""
        # Generate subject
        subject = generator.generate_subject(mock_content_items[:3], mock_newsletter)

        # Verify subject
        assert subject is not None
        assert len(subject) <= 60  # Should be within limit
        assert "Test Newsletter" in subject or "Top Stories" in subject

        # Verify LLM was called
        generator.llm_client.generate.assert_called_once()

    def test_generate_subject_error_fallback(
        self, generator, mock_content_items, mock_newsletter
    ):
        """Test subject generation with error fallback."""
        # Make LLM raise error
        generator.llm_client.generate.side_effect = Exception("LLM error")

        # Generate subject
        subject = generator.generate_subject(mock_content_items[:3], mock_newsletter)

        # Verify fallback subject
        assert subject == f"{mock_newsletter.name}: Today's Top Stories"

    def test_build_newsletter_structure(
        self, generator, mock_content_items, mock_newsletter
    ):
        """Test building newsletter data structure."""
        # Build structure
        structure = generator.build_newsletter_structure(
            mock_content_items, mock_newsletter, max_articles=3
        )

        # Verify structure
        assert structure["newsletter_id"] == mock_newsletter.id
        assert structure["newsletter_name"] == mock_newsletter.name
        assert "sections" in structure
        assert structure["total_articles"] <= 3
        assert "generated_at" in structure

        # Verify sections are organized by category
        sections = structure["sections"]
        assert len(sections) > 0
        assert all("title" in s and "articles" in s for s in sections)

    def test_render_edition(self, generator, mock_newsletter, db_session):
        """Test edition rendering."""
        # Create mock edition
        edition = Mock(spec=Edition)
        edition.newsletter = mock_newsletter
        edition.subject = "Test Subject"
        edition.edition_number = 1
        edition.content = {
            "sections": [
                {
                    "title": "Technology",
                    "articles": [
                        {
                            "id": 1,
                            "title": "Test Article",
                            "summary": "Test summary",
                            "url": "https://example.com",
                        }
                    ],
                }
            ]
        }

        # Mock template engine
        generator.template_engine.render_newsletter.return_value = (
            "<html>Test HTML</html>",
            "Test Text",
        )

        # Render edition
        html, text = generator.render_edition(edition)

        # Verify rendering
        assert html == "<html>Test HTML</html>"
        assert text == "Test Text"
        generator.template_engine.render_newsletter.assert_called_once()

    def test_render_edition_with_personalization(
        self, generator, mock_newsletter, db_session
    ):
        """Test edition rendering with subscriber personalization."""
        # Create mock edition and subscriber
        edition = Mock(spec=Edition)
        edition.newsletter = mock_newsletter
        edition.subject = "Test Subject"
        edition.edition_number = 1
        edition.content = {"sections": []}

        subscriber = Mock(spec=Subscriber)
        subscriber.email = "test@example.com"
        subscriber.name = "Test User"

        # Mock personalization
        generator.personalization.personalize_for_subscriber.return_value = {
            "subscriber_name": "Test User",
            "preferences": {},
        }

        # Mock template engine
        generator.template_engine.render_newsletter.return_value = (
            "<html>Hello Test User</html>",
            "Hello Test User",
        )

        # Render edition
        html, text = generator.render_edition(edition, subscriber)

        # Verify personalization was applied
        generator.personalization.personalize_for_subscriber.assert_called_once_with(
            subscriber, [], mock_newsletter.id
        )

    def test_schedule_edition(self, generator, db_session, mock_newsletter):
        """Test edition scheduling."""
        # Create real edition object
        edition = Edition(
            newsletter_id=mock_newsletter.id,
            subject="Test Subject",
            content={"sections": []},
            status=EditionStatus.DRAFT,
        )

        # Schedule edition
        send_time = datetime.utcnow() + timedelta(hours=1)
        generator.schedule_edition(edition, send_time)

        # Verify scheduling
        assert edition.scheduled_for == send_time
        assert edition.status == EditionStatus.SCHEDULED

    def test_preview_edition(self, generator, mock_newsletter, db_session):
        """Test edition preview generation."""
        # Setup mock query
        db_session.query.return_value.filter.return_value.first.return_value = (
            mock_newsletter
        )

        # Mock generate_edition
        mock_edition = Mock(spec=Edition)
        mock_edition.id = 1
        mock_edition.subject = "Preview Subject"
        with patch.object(generator, "generate_edition", return_value=mock_edition):
            with patch.object(
                generator,
                "render_edition",
                return_value=("<html>Preview</html>", "Preview"),
            ):
                # Generate preview
                preview = generator.preview_edition(newsletter_id=1)

                # Verify preview
                assert preview["edition_id"] == 1
                assert preview["subject"] == "Preview Subject"
                assert preview["html"] == "<html>Preview</html>"
                assert preview["text"] == "Preview"
                assert preview["personalized"] is False

    def test_preview_edition_not_found(self, generator, db_session):
        """Test preview generation with non-existent newsletter."""
        # Setup mock query to return None
        db_session.query.return_value.filter.return_value.first.return_value = None

        # Attempt preview
        with pytest.raises(ValueError, match="Newsletter .* not found"):
            generator.preview_edition(newsletter_id=999)

    def test_generate_edition_no_content(self, generator, mock_newsletter, db_session):
        """Test edition generation with no available content."""
        # Setup mock query to return no content
        db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = (
            []
        )

        # Mock aggregator to also return no content
        with patch.object(generator.aggregator, "fetch_and_process"):
            # Attempt to generate edition
            with pytest.raises(ValueError, match="No content available"):
                generator.generate_edition(mock_newsletter)
