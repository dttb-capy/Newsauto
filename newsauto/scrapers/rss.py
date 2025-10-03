"""RSS feed scraper."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import feedparser
import httpx
from bs4 import BeautifulSoup

from newsauto.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class RSSFetcher(BaseScraper):
    """Fetcher for RSS/Atom feeds."""

    async def fetch_raw(self) -> List[Dict[str, Any]]:
        """Fetch raw RSS feed content.

        Returns:
            List of feed entries
        """
        feed_url = self.source.url or self.source.config.get("feed_url")
        if not feed_url:
            raise ValueError(f"No feed URL configured for source {self.source.name}")

        try:
            # Fetch feed
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    feed_url,
                    timeout=30,
                    headers={"User-Agent": "Newsauto/1.0 (RSS Reader)"},
                )
                response.raise_for_status()

            # Parse feed
            feed = feedparser.parse(response.text)

            if feed.bozo:
                logger.warning(
                    f"Feed parsing issues for {feed_url}: {feed.bozo_exception}"
                )

            logger.info(f"Fetched {len(feed.entries)} entries from {feed_url}")
            return feed.entries

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching RSS feed {feed_url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching RSS feed {feed_url}: {e}")
            raise

    def parse_item(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse RSS feed entry.

        Args:
            entry: Feed entry from feedparser

        Returns:
            Parsed content item
        """
        try:
            # Extract basic fields
            title = entry.get("title", "").strip()
            url = entry.get("link", "").strip()

            if not title or not url:
                logger.warning("Missing title or URL in RSS entry")
                return None

            # Extract content
            content = ""
            if "content" in entry:
                content = entry.content[0].get("value", "")
            elif "summary" in entry:
                content = entry.get("summary", "")
            elif "description" in entry:
                content = entry.get("description", "")

            # Clean HTML if needed
            if content and self.source.config.get("parse_full_text", True):
                soup = BeautifulSoup(content, "html.parser")
                content = soup.get_text(separator="\n", strip=True)

            # Parse published date
            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                from time import mktime

                published_at = datetime.fromtimestamp(mktime(entry.published_parsed))
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                from time import mktime

                published_at = datetime.fromtimestamp(mktime(entry.updated_parsed))

            # Extract author
            author = entry.get("author", "")
            if not author and "authors" in entry:
                authors = entry.get("authors", [])
                if authors and isinstance(authors, list):
                    author = authors[0].get("name", "")

            # Build metadata
            metadata = {
                "source_type": "rss",
                "feed_title": getattr(entry, "feed", {}).get("title", ""),
            }

            # Add categories/tags
            if "tags" in entry:
                tags = [tag.get("term", "") for tag in entry.tags]
                metadata["tags"] = tags
            elif "categories" in entry:
                metadata["categories"] = entry.categories

            return {
                "title": title,
                "url": url,
                "content": content,
                "author": author,
                "published_at": published_at,
                "metadata": metadata,
            }

        except Exception as e:
            logger.error(f"Error parsing RSS entry: {e}")
            return None

    async def fetch_full_content(self, url: str) -> Optional[str]:
        """Fetch full article content from URL.

        Args:
            url: Article URL

        Returns:
            Full content or None
        """
        if not self.source.config.get("fetch_full_content", False):
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    timeout=20,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; Newsauto/1.0)"},
                )
                response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Try to find article content
            # Common article containers
            selectors = [
                "article",
                "main",
                ".article-content",
                ".post-content",
                ".entry-content",
                '[itemprop="articleBody"]',
            ]

            content = None
            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(separator="\n", strip=True)
                    break

            if not content:
                # Fallback to body
                body = soup.find("body")
                if body:
                    # Remove script and style tags
                    for tag in body(["script", "style", "nav", "header", "footer"]):
                        tag.decompose()
                    content = body.get_text(separator="\n", strip=True)

            return content

        except Exception as e:
            logger.error(f"Error fetching full content from {url}: {e}")
            return None
