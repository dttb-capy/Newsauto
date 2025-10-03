"""Tests for content scrapers."""

from unittest.mock import MagicMock, Mock, patch

import feedparser
import pytest

from newsauto.models.content import ContentSource
from newsauto.scrapers.aggregator import ContentAggregator
from newsauto.scrapers.hackernews import HackerNewsScraper
from newsauto.scrapers.reddit import RedditScraper
from newsauto.scrapers.rss import RSSFetcher


class TestRSSScraper:
    """Test RSS feed scraper."""

    def test_parse_feed(self):
        """Test parsing RSS feed."""
        # Create mock content source
        source = Mock(spec=ContentSource)
        source.url = "https://example.com/feed"
        source.config = {}
        scraper = RSSFetcher(source)

        # Mock feed data
        mock_feed = MagicMock()
        mock_feed.entries = [
            MagicMock(
                title="Article 1",
                link="https://example.com/1",
                summary="Summary 1",
                published_parsed=(2024, 1, 1, 0, 0, 0, 0, 1, -1),
                get=lambda x, default=None: "Author 1" if x == "author" else default,
            ),
            MagicMock(
                title="Article 2",
                link="https://example.com/2",
                summary="Summary 2",
                published_parsed=(2024, 1, 2, 0, 0, 0, 0, 2, -1),
                get=lambda x, default=None: None,
            ),
        ]

        with patch.object(feedparser, "parse", return_value=mock_feed):
            with patch("httpx.AsyncClient.get"):  # Mock the HTTP call
                import asyncio

                items = asyncio.run(scraper.fetch_raw())

        assert len(items) == 2
        assert items[0]["title"] == "Article 1"
        assert items[0]["author"] == "Author 1"
        assert items[1]["author"] is None

    def test_fetch_from_source(self, db_session):
        """Test fetching from RSS source."""
        source = Mock(spec=ContentSource)
        source.url = "https://example.com/feed"
        source.config = {}
        scraper = RSSFetcher(source, db_session)

        mock_feed = MagicMock()
        mock_feed.entries = [
            MagicMock(
                title="Test Article",
                link="https://example.com/test",
                summary="Test summary",
                published_parsed=(2024, 1, 1, 0, 0, 0, 0, 1, -1),
                get=lambda x, default=None: default,
            )
        ]

        with patch.object(feedparser, "parse", return_value=mock_feed):
            content = scraper.fetch_from_source(
                {"url": "https://example.com/feed", "name": "Test Feed"}
            )

        assert len(content) == 1
        assert content[0].title == "Test Article"
        assert content[0].source == "Test Feed"

    def test_deduplication(self, db_session):
        """Test content deduplication."""
        from newsauto.models.content import ContentItem

        # Add existing content
        existing = ContentItem(
            url="https://example.com/existing",
            title="Existing Article",
            content="Content",
            source="test",
        )
        db_session.add(existing)
        db_session.commit()

        source = Mock(spec=ContentSource)
        source.url = "https://example.com/feed"
        source.config = {}
        scraper = RSSFetcher(source, db_session)

        mock_feed = MagicMock()
        mock_feed.entries = [
            MagicMock(
                title="Existing Article",
                link="https://example.com/existing",
                summary="Same article",
                published_parsed=(2024, 1, 1, 0, 0, 0, 0, 1, -1),
                get=lambda x, default=None: default,
            ),
            MagicMock(
                title="New Article",
                link="https://example.com/new",
                summary="New content",
                published_parsed=(2024, 1, 1, 0, 0, 0, 0, 1, -1),
                get=lambda x, default=None: default,
            ),
        ]

        with patch.object(feedparser, "parse", return_value=mock_feed):
            content = scraper.fetch_from_source(
                {"url": "https://example.com/feed", "name": "Test Feed"}
            )

        # Should only return the new article
        assert len(content) == 1
        assert content[0].title == "New Article"


class TestRedditScraper:
    """Test Reddit scraper."""

    @pytest.fixture
    def mock_praw(self):
        """Mock praw Reddit instance."""
        with patch("praw.Reddit") as mock_reddit:
            mock_instance = MagicMock()
            mock_reddit.return_value = mock_instance
            yield mock_instance

    def test_fetch_subreddit_posts(self, mock_praw):
        """Test fetching subreddit posts."""
        source = Mock(spec=ContentSource)
        source.url = "https://reddit.com/r/programming"
        source.config = {"subreddit": "programming"}
        scraper = RedditScraper(source)
        scraper.reddit = mock_praw

        # Mock subreddit
        mock_subreddit = MagicMock()
        mock_praw.subreddit.return_value = mock_subreddit

        # Mock posts
        mock_post1 = MagicMock(
            title="Post 1",
            url="https://reddit.com/post1",
            selftext="Text content",
            author=MagicMock(name="author1"),
            created_utc=1704067200.0,
            score=100,
            num_comments=50,
        )

        mock_post2 = MagicMock(
            title="Post 2",
            url="https://example.com/link",
            selftext="",
            author=MagicMock(name="author2"),
            created_utc=1704067200.0,
            score=200,
            num_comments=75,
        )

        mock_subreddit.hot.return_value = [mock_post1, mock_post2]

        posts = scraper.fetch_subreddit("programming", sort="hot", limit=2)

        assert len(posts) == 2
        assert posts[0]["title"] == "Post 1"
        assert posts[0]["score"] == 100
        assert posts[1]["url"] == "https://example.com/link"

    def test_fetch_from_source(self, db_session, mock_praw):
        """Test fetching from Reddit source."""
        source = Mock(spec=ContentSource)
        source.url = "https://reddit.com/r/python"
        source.config = {"subreddit": "python", "limit": 10}
        scraper = RedditScraper(source, db_session)
        scraper.reddit = mock_praw

        mock_subreddit = MagicMock()
        mock_praw.subreddit.return_value = mock_subreddit

        mock_post = MagicMock(
            title="Test Post",
            url="https://reddit.com/test",
            selftext="Test content",
            author=MagicMock(name="testauthor"),
            created_utc=1704067200.0,
            score=150,
            num_comments=25,
        )

        mock_subreddit.hot.return_value = [mock_post]

        content = scraper.fetch_from_source(
            {"subreddit": "test", "sort": "hot", "limit": 1}
        )

        assert len(content) == 1
        assert content[0].title == "Test Post"
        assert content[0].source == "reddit.com/r/test"
        assert content[0].score > 0


class TestHackerNewsScraper:
    """Test HackerNews scraper."""

    @pytest.fixture
    def mock_requests(self):
        """Mock requests for API calls."""
        with patch("httpx.AsyncClient") as mock_client:
            yield mock_client

    async def test_fetch_top_stories(self, mock_requests):
        """Test fetching top stories."""
        source = Mock(spec=ContentSource)
        source.url = "https://news.ycombinator.com"
        source.config = {"story_type": "top"}
        scraper = HackerNewsScraper(source)

        # Mock API responses
        mock_client = MagicMock()
        mock_requests.return_value.__aenter__.return_value = mock_client

        # Mock top stories IDs
        mock_client.get.side_effect = [
            MagicMock(json=lambda: [1, 2, 3]),  # Top stories IDs
            MagicMock(
                json=lambda: {  # Story 1
                    "id": 1,
                    "title": "Story 1",
                    "url": "https://example.com/1",
                    "by": "user1",
                    "time": 1704067200,
                    "score": 100,
                    "descendants": 50,
                }
            ),
            MagicMock(
                json=lambda: {  # Story 2
                    "id": 2,
                    "title": "Story 2",
                    "url": "https://example.com/2",
                    "by": "user2",
                    "time": 1704067200,
                    "score": 200,
                    "descendants": 75,
                }
            ),
        ]

        stories = await scraper.fetch_top_stories(limit=2)

        assert len(stories) == 2
        assert stories[0]["title"] == "Story 1"
        assert stories[1]["score"] == 200

    async def test_fetch_from_source(self, db_session, mock_requests):
        """Test fetching from HackerNews source."""
        source = Mock(spec=ContentSource)
        source.url = "https://news.ycombinator.com"
        source.config = {"story_type": "best", "limit": 10}
        scraper = HackerNewsScraper(source, db_session)

        mock_client = MagicMock()
        mock_requests.return_value.__aenter__.return_value = mock_client

        mock_client.get.side_effect = [
            MagicMock(json=lambda: [1]),  # Top stories IDs
            MagicMock(
                json=lambda: {  # Story details
                    "id": 1,
                    "title": "HN Story",
                    "url": "https://example.com/hn",
                    "by": "hnuser",
                    "time": 1704067200,
                    "score": 150,
                    "descendants": 30,
                }
            ),
        ]

        content = await scraper.fetch_from_source({"category": "top", "limit": 1})

        assert len(content) == 1
        assert content[0].title == "HN Story"
        assert content[0].source == "news.ycombinator.com"


class TestContentAggregator:
    """Test content aggregator."""

    def test_aggregate_content(self, db_session):
        """Test aggregating content from multiple sources."""
        aggregator = ContentAggregator(db_session)

        # Mock content from different sources
        from newsauto.models.content import ContentItem

        content1 = ContentItem(
            url="https://example.com/1",
            title="Article 1",
            content="Content 1",
            source="source1",
            score=80,
        )

        content2 = ContentItem(
            url="https://example.com/2",
            title="Article 2",
            content="Content 2",
            source="source2",
            score=90,
        )

        all_content = [content1, content2]

        # Test deduplication
        deduplicated = aggregator._deduplicate_content(all_content)
        assert len(deduplicated) == 2

        # Add duplicate
        content3 = ContentItem(
            url="https://example.com/1",  # Same URL
            title="Article 1 Duplicate",
            content="Different content",
            source="source3",
            score=70,
        )

        all_content.append(content3)
        deduplicated = aggregator._deduplicate_content(all_content)
        assert len(deduplicated) == 2  # Should still be 2

        # Verify the one with higher score is kept
        urls = [c.url for c in deduplicated]
        assert "https://example.com/1" in urls
        assert "https://example.com/2" in urls

    async def test_fetch_and_process(self, db_session, mock_ollama_client):
        """Test fetching and processing with LLM."""
        aggregator = ContentAggregator(db_session, mock_ollama_client)

        # Mock scraper results
        from newsauto.models.content import ContentItem

        mock_content = ContentItem(
            url="https://example.com/test",
            title="Test Article",
            content="This is test content that needs summarization.",
            source="test",
            score=75,
        )

        with patch.object(aggregator, "fetch_all", return_value=[mock_content]):
            content = await aggregator.fetch_and_process(process_with_llm=True)

        assert len(content) == 1
        assert content[0].summary == "Mock summary"
        assert content[0].processed_at is not None
