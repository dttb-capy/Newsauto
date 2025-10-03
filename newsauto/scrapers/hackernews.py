"""HackerNews scraper."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from newsauto.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class HackerNewsScraper(BaseScraper):
    """Scraper for HackerNews posts."""

    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    ITEM_URL = f"{BASE_URL}/item/{{item_id}}.json"
    TOP_STORIES_URL = f"{BASE_URL}/topstories.json"
    BEST_STORIES_URL = f"{BASE_URL}/beststories.json"
    NEW_STORIES_URL = f"{BASE_URL}/newstories.json"

    async def fetch_raw(self) -> List[Dict[str, Any]]:
        """Fetch posts from HackerNews.

        Returns:
            List of HackerNews posts
        """
        config = self.source.config
        story_type = config.get("story_type", "top")
        limit = config.get("limit", 50)
        min_score = config.get("min_score", 0)

        try:
            # Get story IDs
            story_ids = await self._fetch_story_ids(
                story_type, limit * 2
            )  # Fetch extra for filtering

            # Fetch story details
            stories = await self._fetch_stories(story_ids)

            # Filter by score
            if min_score > 0:
                stories = [s for s in stories if s.get("score", 0) >= min_score]

            # Limit results
            stories = stories[:limit]

            logger.info(
                f"Fetched {len(stories)} stories from HackerNews ({story_type})"
            )
            return stories

        except Exception as e:
            logger.error(f"Error fetching HackerNews stories: {e}")
            raise

    async def _fetch_story_ids(self, story_type: str, limit: int) -> List[int]:
        """Fetch story IDs from HackerNews.

        Args:
            story_type: Type of stories (top, best, new)
            limit: Number of IDs to fetch

        Returns:
            List of story IDs
        """
        # Select appropriate endpoint
        if story_type == "best":
            url = self.BEST_STORIES_URL
        elif story_type == "new":
            url = self.NEW_STORIES_URL
        else:
            url = self.TOP_STORIES_URL

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30)
            response.raise_for_status()
            story_ids = response.json()

        return story_ids[:limit]

    async def _fetch_stories(self, story_ids: List[int]) -> List[Dict[str, Any]]:
        """Fetch story details for given IDs.

        Args:
            story_ids: List of story IDs

        Returns:
            List of story details
        """
        stories = []

        async with httpx.AsyncClient() as client:
            # Fetch stories in batches to avoid overwhelming the API
            batch_size = 10
            for i in range(0, len(story_ids), batch_size):
                batch_ids = story_ids[i : i + batch_size]
                batch_stories = await self._fetch_story_batch(client, batch_ids)
                stories.extend(batch_stories)

        return stories

    async def _fetch_story_batch(
        self, client: httpx.AsyncClient, story_ids: List[int]
    ) -> List[Dict[str, Any]]:
        """Fetch a batch of stories.

        Args:
            client: HTTP client
            story_ids: Story IDs to fetch

        Returns:
            List of story details
        """
        import asyncio

        tasks = []
        for story_id in story_ids:
            url = self.ITEM_URL.format(item_id=story_id)
            tasks.append(client.get(url, timeout=20))

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        stories = []
        for response in responses:
            if isinstance(response, Exception):
                logger.warning(f"Failed to fetch story: {response}")
                continue

            try:
                story = response.json()
                if story and story.get("type") == "story":
                    stories.append(story)
            except Exception as e:
                logger.warning(f"Failed to parse story: {e}")

        return stories

    def parse_item(self, story: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse HackerNews story into standard format.

        Args:
            story: HackerNews story data

        Returns:
            Parsed content item
        """
        try:
            # Skip dead/deleted stories
            if story.get("dead") or story.get("deleted"):
                return None

            # Get URL (use HN discussion for Ask HN/Show HN)
            url = story.get("url")
            hn_url = f"https://news.ycombinator.com/item?id={story['id']}"

            if not url:
                url = hn_url  # Use HN discussion page for text posts

            # Build content
            content = story.get("text", "")
            if not content and story.get("url"):
                content = f"External link: {story['url']}"

            # Add HN context
            hn_context = (
                f"\n\n---\n"
                f"HackerNews Discussion: {hn_url}\n"
                f"Points: {story.get('score', 0)} | "
                f"Comments: {story.get('descendants', 0)}"
            )
            content += hn_context

            # Parse timestamp
            published_at = datetime.fromtimestamp(story.get("time", 0), tz=timezone.utc)

            # Build metadata
            metadata = {
                "source_type": "hackernews",
                "hn_id": story["id"],
                "hn_type": story.get("type", "story"),
                "hn_score": story.get("score", 0),
                "comment_count": story.get("descendants", 0),
                "hn_url": hn_url,
            }

            # Add story type flags
            title = story.get("title", "")
            if title.startswith("Ask HN:"):
                metadata["story_category"] = "ask"
            elif title.startswith("Show HN:"):
                metadata["story_category"] = "show"
            elif title.startswith("Launch HN:"):
                metadata["story_category"] = "launch"
            else:
                metadata["story_category"] = "link"

            # Calculate engagement score
            score = story.get("score", 0)
            comments = story.get("descendants", 0)
            engagement_score = score + (comments * 1.5)

            return {
                "title": title,
                "url": url,
                "content": content,
                "author": story.get("by", ""),
                "published_at": published_at,
                "metadata": metadata,
                "score": min(100, engagement_score / 10),  # Normalize score
            }

        except Exception as e:
            logger.error(f"Error parsing HackerNews story: {e}")
            return None

    async def fetch_comments(
        self, story_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Fetch top comments from a story.

        Args:
            story_id: HackerNews story ID
            limit: Number of comments to fetch

        Returns:
            List of comments
        """
        try:
            async with httpx.AsyncClient() as client:
                # Fetch story to get comment IDs
                story_url = self.ITEM_URL.format(item_id=story_id)
                response = await client.get(story_url, timeout=20)
                response.raise_for_status()
                story = response.json()

                # Get comment IDs
                comment_ids = story.get("kids", [])[:limit]

                # Fetch comments
                comments = []
                for comment_id in comment_ids:
                    comment_url = self.ITEM_URL.format(item_id=comment_id)
                    response = await client.get(comment_url, timeout=20)

                    if response.status_code == 200:
                        comment = response.json()
                        if (
                            comment
                            and not comment.get("dead")
                            and not comment.get("deleted")
                        ):
                            comments.append(
                                {
                                    "text": comment.get("text", ""),
                                    "author": comment.get("by", ""),
                                    "time": datetime.fromtimestamp(
                                        comment.get("time", 0), tz=timezone.utc
                                    ),
                                }
                            )

                return comments

        except Exception as e:
            logger.error(f"Error fetching comments for story {story_id}: {e}")
            return []
