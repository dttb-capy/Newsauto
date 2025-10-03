"""Reddit content scraper."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import praw
from praw.models import Submission

from newsauto.core.config import get_settings
from newsauto.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)
settings = get_settings()


class RedditScraper(BaseScraper):
    """Scraper for Reddit posts."""

    def __init__(self, *args, **kwargs):
        """Initialize Reddit scraper."""
        super().__init__(*args, **kwargs)
        self.reddit = None
        self._init_reddit()

    def _init_reddit(self):
        """Initialize Reddit API client."""
        if not settings.reddit_client_id or not settings.reddit_client_secret:
            logger.warning("Reddit API credentials not configured")
            return

        try:
            self.reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                user_agent=settings.reddit_user_agent,
            )
            # Test connection
            self.reddit.read_only = True
            logger.info("Reddit API client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit client: {e}")

    async def fetch_raw(self) -> List[Dict[str, Any]]:
        """Fetch posts from Reddit.

        Returns:
            List of Reddit posts
        """
        if not self.reddit:
            raise ValueError("Reddit API not configured")

        config = self.source.config
        subreddit_name = config.get("subreddit", "programming")
        sort_by = config.get("sort", "hot")
        limit = config.get("limit", 50)
        time_filter = config.get("time_filter", "week")

        try:
            # Run in executor since PRAW is synchronous
            loop = asyncio.get_event_loop()
            posts = await loop.run_in_executor(
                None,
                self._fetch_subreddit_posts,
                subreddit_name,
                sort_by,
                limit,
                time_filter,
            )

            logger.info(f"Fetched {len(posts)} posts from r/{subreddit_name}")
            return posts

        except Exception as e:
            logger.error(f"Error fetching Reddit posts: {e}")
            raise

    def _fetch_subreddit_posts(
        self, subreddit_name: str, sort_by: str, limit: int, time_filter: str
    ) -> List[Dict[str, Any]]:
        """Fetch posts from a subreddit (synchronous).

        Args:
            subreddit_name: Name of subreddit
            sort_by: Sort method (hot, new, top, rising)
            limit: Number of posts to fetch
            time_filter: Time filter for top posts

        Returns:
            List of post data
        """
        subreddit = self.reddit.subreddit(subreddit_name)

        # Get posts based on sort method
        if sort_by == "hot":
            submissions = subreddit.hot(limit=limit)
        elif sort_by == "new":
            submissions = subreddit.new(limit=limit)
        elif sort_by == "top":
            submissions = subreddit.top(time_filter=time_filter, limit=limit)
        elif sort_by == "rising":
            submissions = subreddit.rising(limit=limit)
        else:
            submissions = subreddit.hot(limit=limit)

        posts = []
        for submission in submissions:
            posts.append(self._extract_post_data(submission))

        return posts

    def _extract_post_data(self, submission: Submission) -> Dict[str, Any]:
        """Extract data from Reddit submission.

        Args:
            submission: Reddit submission object

        Returns:
            Post data dictionary
        """
        return {
            "id": submission.id,
            "title": submission.title,
            "url": submission.url,
            "reddit_url": f"https://reddit.com{submission.permalink}",
            "author": str(submission.author) if submission.author else "[deleted]",
            "subreddit": submission.subreddit.display_name,
            "score": submission.score,
            "upvote_ratio": submission.upvote_ratio,
            "num_comments": submission.num_comments,
            "created_utc": submission.created_utc,
            "selftext": submission.selftext,
            "is_self": submission.is_self,
            "link_flair_text": submission.link_flair_text,
            "over_18": submission.over_18,
            "spoiler": submission.spoiler,
            "stickied": submission.stickied,
        }

    def parse_item(self, post: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse Reddit post into standard format.

        Args:
            post: Reddit post data

        Returns:
            Parsed content item
        """
        try:
            # Skip stickied posts unless configured
            if post.get("stickied") and not self.source.config.get(
                "include_stickied", False
            ):
                return None

            # Skip NSFW if configured
            if post.get("over_18") and not self.source.config.get(
                "include_nsfw", False
            ):
                return None

            # Skip if below minimum score
            min_score = self.source.config.get("min_score", 0)
            if post.get("score", 0) < min_score:
                return None

            # Determine URL (use reddit URL for self posts)
            url = (
                post["reddit_url"]
                if post.get("is_self")
                else post.get("url", post["reddit_url"])
            )

            # Build content
            content = post.get("selftext", "")
            if not content and not post.get("is_self"):
                content = f"External link: {post.get('url', '')}"

            # Add Reddit context to content
            reddit_context = (
                f"\n\n---\n"
                f"Posted in r/{post['subreddit']} | "
                f"Score: {post['score']} | "
                f"Comments: {post['num_comments']}"
            )
            content += reddit_context

            # Parse timestamp
            published_at = datetime.fromtimestamp(post["created_utc"], tz=timezone.utc)

            # Build metadata
            metadata = {
                "source_type": "reddit",
                "reddit_id": post["id"],
                "subreddit": post["subreddit"],
                "reddit_score": post["score"],
                "upvote_ratio": post["upvote_ratio"],
                "comment_count": post["num_comments"],
                "is_self_post": post["is_self"],
                "flair": post.get("link_flair_text"),
                "reddit_url": post["reddit_url"],
            }

            # Add engagement score for relevance
            engagement_score = post["score"] + (post["num_comments"] * 2)
            metadata["engagement_score"] = engagement_score

            return {
                "title": post["title"],
                "url": url,
                "content": content,
                "author": post["author"],
                "published_at": published_at,
                "metadata": metadata,
                "score": min(100, engagement_score / 10),  # Normalize score
            }

        except Exception as e:
            logger.error(f"Error parsing Reddit post: {e}")
            return None

    async def fetch_comments(self, post_id: str, limit: int = 10) -> List[str]:
        """Fetch top comments from a post.

        Args:
            post_id: Reddit post ID
            limit: Number of comments to fetch

        Returns:
            List of comment texts
        """
        if not self.reddit:
            return []

        try:
            loop = asyncio.get_event_loop()
            comments = await loop.run_in_executor(
                None, self._fetch_post_comments, post_id, limit
            )
            return comments

        except Exception as e:
            logger.error(f"Error fetching comments for post {post_id}: {e}")
            return []

    def _fetch_post_comments(self, post_id: str, limit: int) -> List[str]:
        """Fetch comments from a post (synchronous).

        Args:
            post_id: Reddit post ID
            limit: Number of comments

        Returns:
            List of comment texts
        """
        submission = self.reddit.submission(id=post_id)
        submission.comment_sort = "best"
        submission.comments.replace_more(limit=0)

        comments = []
        for comment in submission.comments[:limit]:
            if hasattr(comment, "body"):
                comments.append(comment.body)

        return comments
