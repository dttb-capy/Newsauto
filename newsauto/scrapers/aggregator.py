"""Content aggregator for managing multiple scrapers."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from newsauto.core.database import get_db
from newsauto.models.content import ContentItem, ContentSource, ContentSourceType
from newsauto.scrapers.devto import DevToScraper
from newsauto.scrapers.github import GitHubTrendingScraper
from newsauto.scrapers.hackernews import HackerNewsScraper
from newsauto.scrapers.reddit import RedditScraper
from newsauto.scrapers.rss import RSSFetcher

logger = logging.getLogger(__name__)


class ContentAggregator:
    """Aggregates content from multiple sources."""

    def __init__(self, db: Session = None):
        """Initialize content aggregator.

        Args:
            db: Database session
        """
        self.db = db or next(get_db())
        self.scrapers = {
            ContentSourceType.RSS: RSSFetcher,
            ContentSourceType.REDDIT: RedditScraper,
            ContentSourceType.HACKERNEWS: HackerNewsScraper,
            ContentSourceType.GITHUB: GitHubTrendingScraper,
            ContentSourceType.DEVTO: DevToScraper,
        }
        self.results = {}
        self.errors = {}

    async def fetch_all(
        self,
        newsletter_id: Optional[int] = None,
        source_ids: Optional[List[int]] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Fetch content from all active sources.

        Args:
            newsletter_id: Filter sources by newsletter
            source_ids: Specific source IDs to fetch
            force: Force fetch even if recently fetched

        Returns:
            Aggregation results
        """
        # Get sources to fetch
        sources = self._get_sources(newsletter_id, source_ids, force)

        if not sources:
            logger.info("No sources to fetch")
            return {"sources": 0, "items": 0, "errors": []}

        logger.info(f"Fetching content from {len(sources)} sources")

        # Fetch from each source concurrently
        tasks = []
        for source in sources:
            task = self._fetch_source(source)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        total_items = 0
        errors = []

        for i, result in enumerate(results):
            source = sources[i]

            if isinstance(result, Exception):
                error_msg = f"Error fetching {source.name}: {str(result)}"
                logger.error(error_msg)
                errors.append(error_msg)
                self.errors[source.id] = str(result)
            else:
                self.results[source.id] = result
                total_items += len(result) if result else 0

        return {
            "sources": len(sources),
            "items": total_items,
            "errors": errors,
            "details": self.results,
        }

    def _get_sources(
        self, newsletter_id: Optional[int], source_ids: Optional[List[int]], force: bool
    ) -> List[ContentSource]:
        """Get sources to fetch from.

        Args:
            newsletter_id: Filter by newsletter
            source_ids: Specific source IDs
            force: Include recently fetched sources

        Returns:
            List of content sources
        """
        query = self.db.query(ContentSource).filter(ContentSource.active)

        if newsletter_id:
            query = query.filter(ContentSource.newsletter_id == newsletter_id)

        if source_ids:
            query = query.filter(ContentSource.id.in_(source_ids))

        sources = query.all()

        # Filter by fetch frequency unless forced
        if not force:
            sources = [s for s in sources if s.needs_fetch]

        return sources

    async def _fetch_source(self, source: ContentSource) -> List[ContentItem]:
        """Fetch content from a single source.

        Args:
            source: Content source

        Returns:
            List of fetched items
        """
        try:
            # Get appropriate scraper
            scraper_class = self.scrapers.get(source.type)
            if not scraper_class:
                raise ValueError(f"No scraper available for type {source.type}")

            # Initialize scraper
            scraper = scraper_class(source, self.db)

            # Fetch content
            items = await scraper.fetch()

            logger.info(f"Fetched {len(items)} items from {source.name}")
            return items

        except Exception as e:
            logger.error(f"Error fetching from {source.name}: {e}")
            raise

    async def fetch_and_process(
        self, newsletter_id: Optional[int] = None, process_with_llm: bool = True
    ) -> Dict[str, Any]:
        """Fetch content and optionally process with LLM.

        Args:
            newsletter_id: Newsletter to fetch for
            process_with_llm: Whether to generate summaries

        Returns:
            Processing results
        """
        # Fetch content
        fetch_results = await self.fetch_all(newsletter_id)

        if fetch_results["items"] == 0:
            return fetch_results

        # Process with LLM if requested
        if process_with_llm:
            from newsauto.llm.model_router import ModelRouter

            router = ModelRouter()

            # Get unprocessed items
            unprocessed = (
                self.db.query(ContentItem)
                .filter(ContentItem.processed_at is None)
                .limit(100)
                .all()
            )

            logger.info(f"Processing {len(unprocessed)} items with LLM")

            # Process in batches
            batch_size = 5
            processed_count = 0

            for i in range(0, len(unprocessed), batch_size):
                batch = unprocessed[i : i + batch_size]

                # Prepare batch for processing
                batch_data = [
                    {
                        "content": item.content,
                        "title": item.title,
                        "url": item.url,
                        "id": item.id,
                    }
                    for item in batch
                ]

                # Process batch
                results = router.batch_process(batch_data, batch_size=batch_size)

                # Update items with results
                for j, result in enumerate(results):
                    if result and "summary" in result:
                        item = batch[j]
                        item.summary = result["summary"]
                        item.key_points = result.get("key_points", [])
                        item.processed_at = datetime.utcnow()
                        item.llm_model = result.get("model_used", "unknown")

                        # Update score if provided
                        if "score" in result:
                            item.score = result["score"]

                        processed_count += 1

                self.db.commit()

            fetch_results["processed"] = processed_count

        return fetch_results

    def get_recent_content(
        self,
        hours: int = 24,
        min_score: float = 0,
        limit: int = 100,
        newsletter_id: Optional[int] = None,
    ) -> List[ContentItem]:
        """Get recent content items.

        Args:
            hours: Hours to look back
            min_score: Minimum relevance score
            limit: Maximum items to return
            newsletter_id: Filter by newsletter

        Returns:
            List of content items
        """
        from datetime import timedelta

        since = datetime.utcnow() - timedelta(hours=hours)

        query = self.db.query(ContentItem).filter(
            ContentItem.fetched_at >= since, ContentItem.score >= min_score
        )

        if newsletter_id:
            query = query.join(ContentSource).filter(
                ContentSource.newsletter_id == newsletter_id
            )

        # Order by score and recency
        query = query.order_by(
            ContentItem.score.desc(), ContentItem.published_at.desc()
        )

        return query.limit(limit).all()

    def deduplicate_content(
        self, items: List[ContentItem], similarity_threshold: float = 0.8
    ) -> List[ContentItem]:
        """Remove duplicate content items.

        Args:
            items: List of content items
            similarity_threshold: Similarity threshold for duplicates

        Returns:
            Deduplicated list
        """
        from difflib import SequenceMatcher

        if not items:
            return items

        # Sort by score (keep best version of duplicates)
        items = sorted(items, key=lambda x: x.score, reverse=True)

        unique_items = []
        seen_titles = set()
        seen_urls = set()

        for item in items:
            # Check exact URL match
            if item.url in seen_urls:
                continue

            # Check title similarity
            is_duplicate = False
            for seen_title in seen_titles:
                similarity = SequenceMatcher(
                    None, item.title.lower(), seen_title
                ).ratio()
                if similarity > similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_items.append(item)
                seen_urls.add(item.url)
                seen_titles.add(item.title.lower())

        logger.info(f"Deduplicated {len(items)} items to {len(unique_items)}")
        return unique_items
