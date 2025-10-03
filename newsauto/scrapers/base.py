"""Base scraper class for all content sources."""

import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from newsauto.models.content import ContentItem, ContentSource

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for content scrapers."""

    def __init__(self, source: ContentSource, db: Session = None):
        """Initialize scraper.

        Args:
            source: Content source configuration
            db: Database session
        """
        self.source = source
        self.db = db
        self.fetched_items = []
        self.errors = []

    @abstractmethod
    async def fetch_raw(self) -> List[Dict[str, Any]]:
        """Fetch raw content from source.

        Returns:
            List of raw content items
        """
        pass

    @abstractmethod
    def parse_item(self, raw_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse raw item into standard format.

        Args:
            raw_item: Raw content item

        Returns:
            Parsed item or None if invalid
        """
        pass

    def generate_hash(self, content: str) -> str:
        """Generate hash for content deduplication.

        Args:
            content: Content to hash

        Returns:
            SHA256 hash
        """
        return hashlib.sha256(content.encode()).hexdigest()

    def calculate_score(self, item: Dict[str, Any]) -> float:
        """Calculate relevance score for content.

        Args:
            item: Content item

        Returns:
            Score between 0 and 100
        """
        score = 40.0  # Base score

        # Author reputation bonus
        if item.get("author"):
            score += 5
            # Known high-quality authors get extra points
            known_authors = self.source.config.get("trusted_authors", [])
            if item["author"] in known_authors:
                score += 10

        # Recency bonus (stronger weighting)
        if item.get("published_at"):
            published = item["published_at"]
            if isinstance(published, str):
                published = datetime.fromisoformat(published)

            # Make both datetimes timezone-naive for comparison
            now = datetime.now()
            if published.tzinfo is not None:
                # Convert to naive datetime (assuming UTC)
                published = published.replace(tzinfo=None)

            age_hours = (now - published).total_seconds() / 3600
            if age_hours < 6:  # Very fresh
                score += 25
            elif age_hours < 24:
                score += 20
            elif age_hours < 72:
                score += 10
            elif age_hours < 168:  # 1 week
                score += 5

        # Engagement metrics
        if "upvotes" in item or "score" in item:
            engagement = item.get("upvotes", item.get("score", 0))
            if engagement > 1000:
                score += 20
            elif engagement > 500:
                score += 15
            elif engagement > 100:
                score += 10
            elif engagement > 50:
                score += 5

        # Comment count
        if item.get("comment_count", 0) > 100:
            score += 10
        elif item.get("comment_count", 0) > 50:
            score += 5

        # Keyword matching (if configured)
        if self.source.config.get("keywords"):
            keywords = self.source.config["keywords"]
            content = (item.get("title", "") + " " + item.get("content", "")).lower()
            matches = sum(1 for kw in keywords if kw.lower() in content)
            score += min(matches * 5, 25)

        return min(score, 100.0)

    async def fetch(self) -> List[ContentItem]:
        """Fetch and process content from source.

        Returns:
            List of content items
        """
        try:
            # Fetch raw content
            raw_items = await self.fetch_raw()
            logger.info(f"Fetched {len(raw_items)} raw items from {self.source.name}")

            # Process each item
            processed_items = []
            for raw_item in raw_items:
                try:
                    # Parse item
                    parsed = self.parse_item(raw_item)
                    if not parsed:
                        continue

                    # Check for duplicates by URL first (more reliable)
                    url = parsed.get("url", "")
                    if not url:
                        logger.warning("Skipping item with no URL")
                        continue

                    # Skip if URL already exists
                    if self.db:
                        existing = self.db.query(ContentItem).filter_by(url=url).first()
                        if existing:
                            logger.debug(
                                f"Skipping duplicate URL: {parsed.get('title')}"
                            )
                            continue

                    # Generate content hash as secondary dedup
                    content_hash = self.generate_hash(url + parsed.get("title", ""))

                    # Calculate score
                    score = self.calculate_score(parsed)

                    # Create content item
                    content_item = ContentItem(
                        source_id=self.source.id,
                        url=parsed["url"],
                        title=parsed["title"],
                        author=parsed.get("author"),
                        content=parsed.get("content", ""),
                        content_hash=content_hash,
                        score=score,
                        published_at=parsed.get("published_at"),
                        metadata=parsed.get("metadata", {}),
                        fetched_at=datetime.utcnow(),
                    )

                    processed_items.append(content_item)

                except Exception as e:
                    logger.error(f"Error processing item: {e}")
                    self.errors.append(str(e))

            # Save to database with error handling
            if self.db and processed_items:
                saved_count = 0
                for item in processed_items:
                    try:
                        self.db.add(item)
                        self.db.flush()  # Check constraints before commit
                        saved_count += 1
                    except Exception as e:
                        self.db.rollback()
                        logger.warning(f"Could not save item {item.title}: {e}")
                        continue

                self.db.commit()
                logger.info(
                    f"Saved {saved_count}/{len(processed_items)} items to database"
                )

            # Update source last_fetched
            if self.db:
                self.source.last_fetched = datetime.utcnow()
                self.source.error_count = len(self.errors)
                self.db.commit()

            self.fetched_items = processed_items
            return processed_items

        except Exception as e:
            logger.error(f"Fetch error for {self.source.name}: {e}")
            if self.db:
                self.source.error_count += 1
                self.db.commit()
            raise

    def filter_by_config(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter items based on source configuration.

        Args:
            items: List of content items

        Returns:
            Filtered list
        """
        config = self.source.config

        # Filter by keywords
        if config.get("keywords"):
            keywords = [kw.lower() for kw in config["keywords"]]
            items = [
                item
                for item in items
                if any(
                    kw in (item.get("title", "") + item.get("content", "")).lower()
                    for kw in keywords
                )
            ]

        # Filter by exclude keywords
        if config.get("exclude_keywords"):
            exclude = [kw.lower() for kw in config["exclude_keywords"]]
            items = [
                item
                for item in items
                if not any(
                    kw in (item.get("title", "") + item.get("content", "")).lower()
                    for kw in exclude
                )
            ]

        # Filter by minimum score
        if config.get("min_score"):
            min_score = config["min_score"]
            items = [item for item in items if item.get("score", 0) >= min_score]

        # Limit number of items
        if config.get("limit"):
            items = items[: config["limit"]]

        return items
