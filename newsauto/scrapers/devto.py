"""Dev.to API scraper for high-quality technical articles."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from newsauto.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class DevToScraper(BaseScraper):
    """Scraper for Dev.to articles using their public API."""

    BASE_URL = "https://dev.to/api"

    async def fetch_raw(self) -> List[Dict[str, Any]]:
        """Fetch articles from Dev.to API.

        Returns:
            List of Dev.to articles
        """
        config = self.source.config
        limit = config.get("limit", 30)
        tag = config.get("tag", "")  # e.g., "python", "webdev", "javascript"
        top_period = config.get("top_period", 7)  # Top articles from last N days
        min_reactions = config.get("min_reactions", 10)

        try:
            articles = []

            # Fetch top articles
            params = {
                "per_page": min(limit * 2, 100),  # Fetch extra for filtering
                "top": top_period,
            }

            if tag:
                params["tag"] = tag

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/articles",
                    params=params,
                    headers={
                        "User-Agent": "Newsauto/1.0 (Newsletter Bot)",
                        "Accept": "application/json",
                    },
                    timeout=30,
                )
                response.raise_for_status()
                articles = response.json()

            # Filter by minimum reactions
            if min_reactions > 0:
                articles = [
                    a
                    for a in articles
                    if a.get("public_reactions_count", 0) >= min_reactions
                ]

            # Limit results
            articles = articles[:limit]

            # Fetch full content for top articles
            if config.get("fetch_full_content", True):
                full_articles = []
                for article in articles[:10]:  # Limit full fetch to top 10
                    try:
                        full_article = await self._fetch_full_article(article["id"])
                        if full_article:
                            full_articles.append(full_article)
                        else:
                            full_articles.append(article)
                    except Exception as e:
                        logger.warning(f"Could not fetch full article: {e}")
                        full_articles.append(article)

                # Add remaining articles without full content
                full_articles.extend(articles[10:])
                articles = full_articles

            logger.info(
                f"Fetched {len(articles)} articles from Dev.to ({tag or 'all tags'})"
            )
            return articles

        except Exception as e:
            logger.error(f"Error fetching Dev.to articles: {e}")
            raise

    async def _fetch_full_article(self, article_id: int) -> Optional[Dict[str, Any]]:
        """Fetch full article content.

        Args:
            article_id: Dev.to article ID

        Returns:
            Full article data
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/articles/{article_id}",
                    headers={
                        "User-Agent": "Newsauto/1.0",
                        "Accept": "application/json",
                    },
                    timeout=10,
                )

                if response.status_code == 200:
                    return response.json()

        except Exception as e:
            logger.debug(f"Could not fetch full article {article_id}: {e}")

        return None

    def parse_item(self, article: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse Dev.to article into standard content format.

        Args:
            article: Article data from Dev.to API

        Returns:
            Parsed content item
        """
        try:
            # Extract basic fields
            title = article.get("title", "").strip()
            url = article.get("url", "").strip()

            if not title or not url:
                return None

            # Extract author information
            user = article.get("user", {})
            author = user.get("name", user.get("username", ""))

            # Get content (body_markdown for full articles, description for listings)
            content = article.get("body_markdown", "")
            if not content:
                content = article.get("description", "")

            # Add metadata to content
            if content:
                # Add article metadata
                meta_parts = []

                # Tags
                tags = article.get("tag_list", [])
                if tags:
                    meta_parts.append(f"**Tags**: {', '.join(tags)}")

                # Reading time
                reading_time = article.get("reading_time_minutes")
                if reading_time:
                    meta_parts.append(f"**Reading time**: {reading_time} minutes")

                # Reactions and comments
                reactions = article.get("public_reactions_count", 0)
                comments = article.get("comments_count", 0)
                meta_parts.append(
                    f"**Reactions**: {reactions} | **Comments**: {comments}"
                )

                # Organization
                org = article.get("organization")
                if org:
                    meta_parts.append(f"**Organization**: {org.get('name', '')}")

                if meta_parts:
                    content = "\n".join(meta_parts) + "\n\n---\n\n" + content

            # Parse published date
            published_at = None
            if article.get("published_at"):
                try:
                    published_at = datetime.fromisoformat(
                        article["published_at"].replace("Z", "+00:00")
                    )
                except (ValueError, KeyError, AttributeError):
                    published_at = datetime.now()

            # Build metadata
            metadata = {
                "source_type": "devto",
                "tags": article.get("tag_list", []),
                "reading_time_minutes": article.get("reading_time_minutes"),
                "reactions_count": article.get("public_reactions_count", 0),
                "comments_count": article.get("comments_count", 0),
                "cover_image": article.get("cover_image"),
            }

            # Add organization if present
            if article.get("organization"):
                metadata["organization"] = article["organization"].get("name")

            return {
                "url": url,
                "title": title,
                "author": author,
                "content": content,
                "published_at": published_at,
                "metadata": metadata,
                # Use reactions as score indicator
                "upvotes": article.get("public_reactions_count", 0),
                "comment_count": article.get("comments_count", 0),
            }

        except Exception as e:
            logger.error(f"Error parsing Dev.to article: {e}")
            return None
