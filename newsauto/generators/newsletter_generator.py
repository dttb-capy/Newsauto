"""Newsletter generation engine."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from newsauto.generators.personalization import PersonalizationEngine
from newsauto.generators.template_engine import TemplateEngine
from newsauto.llm.ollama_client import OllamaClient
from newsauto.models.content import ContentItem
from newsauto.models.edition import Edition, EditionStatus
from newsauto.models.newsletter import Newsletter
from newsauto.models.subscriber import Subscriber
from newsauto.scrapers.aggregator import ContentAggregator
from newsauto.auth.tokens import TokenGenerator
from newsauto.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class NewsletterGenerator:
    """Main newsletter generation engine."""

    def __init__(
        self,
        db: Session,
        llm_client: Optional[OllamaClient] = None,
        template_engine: Optional[TemplateEngine] = None,
    ):
        """Initialize newsletter generator.

        Args:
            db: Database session
            llm_client: LLM client for content processing
            template_engine: Template engine for rendering
        """
        self.db = db
        self.llm_client = llm_client or OllamaClient()
        self.template_engine = template_engine or TemplateEngine()
        self.personalization = PersonalizationEngine(db)
        self.aggregator = ContentAggregator(db)

    def generate_edition(
        self,
        newsletter: Newsletter,
        test_mode: bool = False,
        max_articles: int = 10,
        min_score: float = 50.0,
    ) -> Edition:
        """Generate newsletter edition.

        Args:
            newsletter: Newsletter object
            test_mode: Whether this is a test edition
            max_articles: Maximum articles to include
            min_score: Minimum content score threshold

        Returns:
            Generated edition
        """
        logger.info(f"Generating edition for newsletter {newsletter.id}")

        # Fetch fresh content
        content = self.fetch_content(newsletter, min_score)

        if not content:
            logger.warning("No content available for newsletter")
            raise ValueError("No content available for newsletter generation")

        # Process content with LLM
        processed_content = self.process_content(content, newsletter)

        # Create edition
        edition = Edition(
            newsletter_id=newsletter.id,
            status=EditionStatus.DRAFT,
            test_mode=test_mode,
            content={"sections": []},
        )

        # Generate subject line
        edition.subject = self.generate_subject(processed_content, newsletter)

        # Build newsletter structure
        newsletter_data = self.build_newsletter_structure(
            processed_content, newsletter, max_articles
        )

        edition.content = newsletter_data

        # Save edition
        self.db.add(edition)
        self.db.commit()
        self.db.refresh(edition)

        logger.info(f"Generated edition {edition.id} for newsletter {newsletter.id}")
        return edition

    def fetch_content(
        self, newsletter: Newsletter, min_score: float = 50.0
    ) -> List[ContentItem]:
        """Fetch content for newsletter.

        Args:
            newsletter: Newsletter object
            min_score: Minimum content score

        Returns:
            List of content items
        """
        # Get content from last 24-72 hours based on frequency
        if newsletter.frequency == "daily":
            hours = 24
        elif newsletter.frequency == "weekly":
            hours = 168
        else:
            hours = 72

        since = datetime.utcnow() - timedelta(hours=hours)

        # Query content
        content = (
            self.db.query(ContentItem)
            .filter(ContentItem.fetched_at >= since, ContentItem.score >= min_score)
            .order_by(ContentItem.score.desc(), ContentItem.published_at.desc())
            .limit(100)
            .all()
        )

        # If not enough content, trigger fresh fetch
        if len(content) < 5:
            logger.info("Insufficient content, triggering fresh fetch")
            self.aggregator.fetch_and_process(
                newsletter_id=newsletter.id, process_with_llm=True
            )

            # Re-query after fetch
            content = (
                self.db.query(ContentItem)
                .filter(ContentItem.fetched_at >= since, ContentItem.score >= min_score)
                .order_by(ContentItem.score.desc(), ContentItem.published_at.desc())
                .limit(100)
                .all()
            )

        return content

    def process_content(
        self, content: List[ContentItem], newsletter: Newsletter
    ) -> List[ContentItem]:
        """Process content with LLM.

        Args:
            content: List of content items
            newsletter: Newsletter object

        Returns:
            Processed content items
        """
        processed = []

        for item in content:
            # Skip if already processed
            if item.processed_at and item.summary:
                processed.append(item)
                continue

            try:
                # Generate summary if missing
                if not item.summary and item.content:
                    item.summary = self.llm_client.summarize(
                        item.content, max_tokens=200
                    )

                # Classify content
                categories = newsletter.settings.get(
                    "categories", ["Technology", "Science", "Business", "General"]
                )
                classification = self.llm_client.classify_content(
                    item.content or item.summary, categories=categories
                )

                # Update metadata
                if not item.meta_data:
                    item.meta_data = {}

                # Update metadata - need to reassign for JSON column
                updated_metadata = item.meta_data or {}
                updated_metadata.update(
                    {
                        "category": classification.get("category", "General"),
                        "topics": classification.get("topics", []),
                        "sentiment": classification.get("sentiment", "neutral"),
                        "newsletter_id": newsletter.id,
                    }
                )
                item.meta_data = updated_metadata

                item.processed_at = datetime.utcnow()

                # Save updates
                self.db.add(item)
                processed.append(item)

            except Exception as e:
                logger.error(f"Error processing content {item.id}: {e}")
                continue

        self.db.commit()
        return processed

    def generate_subject(
        self, content: List[ContentItem], newsletter: Newsletter
    ) -> str:
        """Generate newsletter subject line.

        Args:
            content: List of content items
            newsletter: Newsletter object

        Returns:
            Subject line
        """
        # Get top stories
        top_stories = content[:3]
        titles = [item.title for item in top_stories]

        # Use LLM to generate subject
        try:
            # Use generate_title method instead of generate
            subject = self.llm_client.generate_title(
                chr(10).join(f"- {title}" for title in titles), style="engaging"
            )
            if not subject:
                # Fallback to simple format
                subject = f"{newsletter.name}: {titles[0][:40]}..."

            # Fallback if too long
            if len(subject) > 60:
                subject = f"{newsletter.name}: {titles[0][:40]}..."

        except Exception as e:
            logger.error(f"Error generating subject: {e}")
            # Fallback subject
            subject = f"{newsletter.name}: Today's Top Stories"

        return subject

    def build_newsletter_structure(
        self, content: List[ContentItem], newsletter: Newsletter, max_articles: int
    ) -> Dict[str, Any]:
        """Build newsletter data structure.

        Args:
            content: List of content items
            newsletter: Newsletter object
            max_articles: Maximum articles to include

        Returns:
            Newsletter data structure
        """
        # Group content by category
        categories = {}
        for item in content[:max_articles]:
            category = "General"
            if item.meta_data and "category" in item.meta_data:
                category = item.meta_data["category"]

            if category not in categories:
                categories[category] = []

            categories[category].append(
                {
                    "id": item.id,
                    "title": item.title,
                    "url": item.url,
                    "author": item.author,
                    "summary": item.summary,
                    "published_at": (
                        item.published_at.isoformat() if item.published_at else None
                    ),
                    "score": item.score,
                    "metadata": item.meta_data,
                }
            )

        # Build sections
        sections = []
        priority_categories = ["Breaking", "Featured", "Trending"]

        # Add priority sections first
        for category in priority_categories:
            if category in categories:
                sections.append({"title": category, "articles": categories[category]})
                del categories[category]

        # Add remaining sections
        for category, articles in sorted(categories.items()):
            sections.append({"title": category, "articles": articles})

        return {
            "newsletter_id": newsletter.id,
            "newsletter_name": newsletter.name,
            "sections": sections,
            "total_articles": sum(len(s["articles"]) for s in sections),
            "generated_at": datetime.utcnow().isoformat(),
        }

    def render_edition(
        self, edition: Edition, subscriber: Optional[Subscriber] = None
    ) -> tuple[str, str]:
        """Render edition for sending.

        Args:
            edition: Edition object
            subscriber: Optional subscriber for personalization

        Returns:
            Tuple of (html_content, text_content)
        """
        newsletter = edition.newsletter

        # Build context
        context = {
            "newsletter": {
                "id": newsletter.id,
                "name": newsletter.name,
                "description": newsletter.description,
            },
            "subject": edition.subject,
            "sections": edition.content.get("sections", []),
            "edition_number": edition.edition_number,
        }

        # Generate URLs if subscriber provided
        if subscriber:
            token = TokenGenerator.generate_unsubscribe_token(
                subscriber.id, newsletter.id
            )
            context["unsubscribe_url"] = f"{settings.unsubscribe_base_url}?token={token}"
            context["preferences_url"] = f"{settings.frontend_url}/preferences?token={token}"
        else:
            # Default URLs for preview/test
            context["unsubscribe_url"] = f"{settings.unsubscribe_base_url}"
            context["preferences_url"] = f"{settings.frontend_url}/preferences"

        # Add personalization if subscriber provided
        if subscriber:
            personalized = self.personalization.personalize_for_subscriber(
                subscriber, self.get_edition_content_items(edition), newsletter.id
            )
            context.update(personalized)

        # Render template
        return self.template_engine.render_newsletter("default", context)

    def get_edition_content_items(self, edition: Edition) -> List[ContentItem]:
        """Get content items for edition.

        Args:
            edition: Edition object

        Returns:
            List of content items
        """
        content_ids = []
        for section in edition.content.get("sections", []):
            for article in section.get("articles", []):
                if "id" in article:
                    content_ids.append(article["id"])

        if not content_ids:
            return []

        return self.db.query(ContentItem).filter(ContentItem.id.in_(content_ids)).all()

    def schedule_edition(self, edition: Edition, send_at: datetime) -> Edition:
        """Schedule edition for sending.

        Args:
            edition: Edition object
            send_at: Scheduled send time

        Returns:
            Updated edition
        """
        edition.scheduled_for = send_at
        edition.status = EditionStatus.SCHEDULED

        self.db.add(edition)
        self.db.commit()

        logger.info(f"Scheduled edition {edition.id} for {send_at}")
        return edition

    def preview_edition(
        self, newsletter_id: int, subscriber_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate preview of newsletter edition.

        Args:
            newsletter_id: Newsletter ID
            subscriber_email: Optional subscriber email for personalized preview

        Returns:
            Preview data
        """
        newsletter = (
            self.db.query(Newsletter).filter(Newsletter.id == newsletter_id).first()
        )

        if not newsletter:
            raise ValueError(f"Newsletter {newsletter_id} not found")

        # Generate test edition
        edition = self.generate_edition(newsletter, test_mode=True, max_articles=5)

        # Get subscriber if email provided
        subscriber = None
        if subscriber_email:
            subscriber = (
                self.db.query(Subscriber)
                .filter(Subscriber.email == subscriber_email)
                .first()
            )

        # Render edition
        html_content, text_content = self.render_edition(edition, subscriber)

        return {
            "edition_id": edition.id,
            "subject": edition.subject,
            "html": html_content,
            "text": text_content,
            "personalized": subscriber is not None,
        }
