"""
Niche-aware content aggregator for premium newsletters.
Fetches content from RSS feeds configured for each niche.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from newsauto.config.niches import niche_configs
from newsauto.config.rss_feeds import get_feeds_for_niche
from newsauto.scrapers.aggregator import ContentAggregator
from newsauto.scrapers.rss import RSSFetcher

logger = logging.getLogger(__name__)


class NicheContentAggregator:
    """Aggregates content specific to newsletter niches."""

    def __init__(self):
        """Initialize the niche content aggregator."""
        self.base_aggregator = ContentAggregator()
        self.rss_scraper = RSSFetcher()

    async def fetch_niche_content(
        self,
        niche_key: str,
        max_age_days: int = 7,
        limit_per_source: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Fetch content for a specific niche.

        Args:
            niche_key: The niche identifier (e.g., 'cto_engineering_playbook')
            max_age_days: Maximum age of content to fetch
            limit_per_source: Maximum items per RSS feed

        Returns:
            List of content items
        """
        if niche_key not in niche_configs:
            logger.error(f"Unknown niche: {niche_key}")
            return []

        niche = niche_configs[niche_key]
        logger.info(f"Fetching content for niche: {niche.name}")

        # Get RSS feeds for this niche
        rss_feeds = get_feeds_for_niche(niche_key, include_general=False)
        if not rss_feeds:
            logger.warning(f"No RSS feeds configured for niche: {niche_key}")
            rss_feeds = get_feeds_for_niche(niche_key, include_general=True)

        # Fetch content from RSS feeds
        all_content = []
        for feed_url in rss_feeds[:10]:  # Limit to 10 feeds to avoid overload
            try:
                logger.debug(f"Fetching from feed: {feed_url}")
                # Set the feed URL for the scraper
                self.rss_scraper.url = feed_url
                self.rss_scraper.config = {
                    "max_items": limit_per_source,
                    "parse_full_text": True
                }
                content = await self.rss_scraper.fetch()

                # Filter by age
                cutoff_date = datetime.now() - timedelta(days=max_age_days)
                filtered_content = []
                for item in content:
                    if item.get("published_at"):
                        if isinstance(item["published_at"], str):
                            try:
                                pub_date = datetime.fromisoformat(item["published_at"])
                                if pub_date >= cutoff_date:
                                    filtered_content.append(item)
                            except ValueError:
                                filtered_content.append(item)
                        elif isinstance(item["published_at"], datetime):
                            if item["published_at"] >= cutoff_date:
                                filtered_content.append(item)
                    else:
                        filtered_content.append(item)

                # Add niche metadata
                for item in filtered_content:
                    item["niche"] = niche_key
                    item["niche_name"] = niche.name
                    item["content_category"] = niche.category.value

                all_content.extend(filtered_content)

            except Exception as e:
                logger.error(f"Error fetching feed {feed_url}: {e}")
                continue

        # Apply niche-specific filtering
        filtered_content = self._apply_niche_filters(all_content, niche)

        # Score and rank content
        scored_content = self._score_content(filtered_content, niche)

        # Sort by score
        scored_content.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        logger.info(
            f"Fetched {len(scored_content)} items for niche {niche.name}"
        )
        return scored_content

    def _apply_niche_filters(
        self, content: List[Dict[str, Any]], niche
    ) -> List[Dict[str, Any]]:
        """Apply niche-specific keyword filtering."""
        filtered = []

        # Convert keywords to lowercase for case-insensitive matching
        keywords = [kw.lower() for kw in niche.keywords]
        exclude_keywords = [kw.lower() for kw in niche.exclude_keywords]

        for item in content:
            # Check content for keywords
            text = (
                f"{item.get('title', '')} {item.get('summary', '')} "
                f"{item.get('content', '')}"
            ).lower()

            # Must contain at least one keyword
            if keywords:
                has_keyword = any(kw in text for kw in keywords)
                if not has_keyword:
                    continue

            # Must not contain exclude keywords
            if exclude_keywords:
                has_excluded = any(kw in text for kw in exclude_keywords)
                if has_excluded:
                    continue

            filtered.append(item)

        return filtered

    def _score_content(
        self, content: List[Dict[str, Any]], niche
    ) -> List[Dict[str, Any]]:
        """Score content based on niche relevance."""
        for item in content:
            score = 0.5  # Base score

            text = (
                f"{item.get('title', '')} {item.get('summary', '')}"
            ).lower()

            # Keyword density scoring
            keywords = [kw.lower() for kw in niche.keywords]
            keyword_count = sum(1 for kw in keywords if kw in text)
            score += min(keyword_count * 0.1, 0.3)

            # Freshness scoring
            if item.get("published_at"):
                try:
                    if isinstance(item["published_at"], str):
                        pub_date = datetime.fromisoformat(item["published_at"])
                    else:
                        pub_date = item["published_at"]

                    age_days = (datetime.now() - pub_date).days
                    if age_days <= 1:
                        score += 0.2
                    elif age_days <= 3:
                        score += 0.1
                    elif age_days <= 7:
                        score += 0.05
                except (ValueError, TypeError):
                    pass

            # Source quality scoring (premium sources get higher scores)
            source = item.get("source", "").lower()
            premium_sources = [
                "bloomberg",
                "wsj",
                "financial times",
                "gartner",
                "forrester",
                "mckinsey",
            ]
            if any(ps in source for ps in premium_sources):
                score += 0.15

            item["relevance_score"] = min(score, 1.0)

        return content

    async def fetch_multiple_niches(
        self,
        niche_keys: List[str],
        max_age_days: int = 7,
        limit_per_source: int = 10,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch content for multiple niches concurrently.

        Args:
            niche_keys: List of niche identifiers
            max_age_days: Maximum age of content to fetch
            limit_per_source: Maximum items per RSS feed

        Returns:
            Dictionary mapping niche keys to content lists
        """
        tasks = []
        for niche_key in niche_keys:
            task = self.fetch_niche_content(
                niche_key, max_age_days, limit_per_source
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        niche_content = {}
        for niche_key, result in zip(niche_keys, results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching content for {niche_key}: {result}")
                niche_content[niche_key] = []
            else:
                niche_content[niche_key] = result

        return niche_content

    async def get_top_stories_for_niche(
        self,
        niche_key: str,
        count: int = 10,
        max_age_days: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Get the top stories for a specific niche.

        Args:
            niche_key: The niche identifier
            count: Number of top stories to return
            max_age_days: Maximum age of content

        Returns:
            List of top content items
        """
        content = await self.fetch_niche_content(
            niche_key,
            max_age_days=max_age_days,
            limit_per_source=20,
        )

        # Return top scored items
        return content[:count]

    def get_niche_info(self, niche_key: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a niche.

        Args:
            niche_key: The niche identifier

        Returns:
            Dictionary with niche information
        """
        if niche_key not in niche_configs:
            return None

        niche = niche_configs[niche_key]
        feeds = get_feeds_for_niche(niche_key)

        return {
            "key": niche_key,
            "name": niche.name,
            "description": niche.description,
            "target_audience": niche.target_audience,
            "keywords": niche.keywords,
            "feed_count": len(feeds),
            "feeds": feeds[:5],  # Sample of feeds
            "pricing": niche.pricing_tiers,
            "target_metrics": {
                "open_rate": niche.target_open_rate,
                "click_rate": niche.target_click_rate,
                "share_rate": niche.target_share_rate,
            },
        }


# Convenience function for CLI usage
async def test_niche_aggregator():
    """Test the niche aggregator with a sample niche."""
    aggregator = NicheContentAggregator()

    # Test with CTO Engineering Playbook niche
    niche_key = "cto_engineering_playbook"
    print(f"\n🔍 Testing content aggregation for: {niche_key}")

    # Get niche info
    info = aggregator.get_niche_info(niche_key)
    if info:
        print(f"📚 Niche: {info['name']}")
        print(f"🎯 Target: {info['target_audience']}")
        print(f"📡 RSS Feeds: {info['feed_count']}")

    # Fetch content
    content = await aggregator.get_top_stories_for_niche(
        niche_key, count=5, max_age_days=7
    )

    print(f"\n📰 Top {len(content)} stories:")
    for i, item in enumerate(content, 1):
        print(f"{i}. {item.get('title', 'Untitled')}")
        print(f"   Score: {item.get('relevance_score', 0):.2f}")
        print(f"   Source: {item.get('source', 'Unknown')}")
        print(f"   URL: {item.get('url', 'N/A')}")
        print()

    return content


if __name__ == "__main__":
    # Run test
    asyncio.run(test_niche_aggregator())