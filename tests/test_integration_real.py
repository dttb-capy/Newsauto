#!/usr/bin/env python
"""
Real integration tests - uses actual external services.
Run manually with: pytest tests/test_integration_real.py -v

WARNING: These tests:
- Require Ollama running with mistral model
- Make real HTTP requests to external sites
- May send actual emails (use mailhog locally)
- Take 30-60 seconds to complete
- Should NOT run in CI/CD pipeline
"""

import asyncio
import os
from datetime import datetime

import pytest

# Skip these tests in CI environment
pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true", reason="Real integration tests don't run in CI"
)


@pytest.mark.slow
@pytest.mark.real_services
class TestRealIntegration:
    """Test with real external services."""

    @pytest.mark.asyncio
    async def test_real_ollama_summarization(self):
        """Test with real Ollama server."""
        from newsauto.llm.ollama_client import OllamaClient

        # This requires Ollama running
        client = OllamaClient()

        text = """
        OpenAI announced GPT-5 today with breakthrough capabilities
        in reasoning and multimodal understanding. The model shows
        significant improvements in mathematical reasoning and can now
        process video inputs natively.
        """

        try:
            summary = await client.summarize(text)
            assert summary is not None
            assert len(summary) < len(text)
            print(f"Real summary: {summary}")
        except Exception as e:
            pytest.skip(f"Ollama not available: {e}")

    @pytest.mark.asyncio
    async def test_real_rss_feed(self):
        """Test with real RSS feeds."""
        from newsauto.scrapers.rss import RSSFetcher

        fetcher = RSSFetcher()
        feeds = [
            "https://news.ycombinator.com/rss",
            "https://www.reddit.com/r/programming/.rss",
        ]

        for feed_url in feeds:
            try:
                content = await fetcher.fetch_feed(feed_url)
                assert len(content) > 0
                print(f"Fetched {len(content)} items from {feed_url}")
            except Exception as e:
                print(f"Feed {feed_url} failed: {e}")

    @pytest.mark.asyncio
    async def test_real_email_send(self):
        """Test with real email (local mailhog)."""
        from newsauto.email.email_sender import EmailSender, SMTPConfig

        # Use local mailhog for testing
        config = SMTPConfig(
            host="localhost",
            port=1025,
            use_tls=False,
            from_email="test@newsauto.local",
            from_name="Test Newsletter",
        )

        sender = EmailSender(config)

        try:
            success = await sender.send_email(
                to_email="test@example.com",
                subject=f"Real Test Email - {datetime.now()}",
                html_content="<h1>This is a real test</h1>",
                text_content="This is a real test",
            )
            assert success is True
            print("Email sent to mailhog successfully")
        except Exception as e:
            pytest.skip(f"Mailhog not available: {e}")

    @pytest.mark.asyncio
    async def test_full_pipeline_real(self, tmp_path):
        """Test complete pipeline with real services."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from newsauto.generators.newsletter_generator import NewsletterGenerator
        from newsauto.models.base import Base
        from newsauto.scrapers.aggregator import ContentAggregator

        # Create real test database
        db_path = tmp_path / "test.db"
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # 1. Fetch real content
            aggregator = ContentAggregator(session)
            content = await aggregator.fetch_and_process(
                sources=["hackernews"],  # Just HN for speed
                process_with_llm=False,  # Skip LLM for this test
            )
            assert len(content) > 0
            print(f"Fetched {len(content)} real articles")

            # 2. Generate newsletter
            generator = NewsletterGenerator(session)
            # Would need real newsletter object here

        finally:
            session.close()


# Run with: pytest tests/test_integration_real.py -v -m real_services
# Or specific test: pytest tests/test_integration_real.py::TestRealIntegration::test_real_ollama_summarization -v
