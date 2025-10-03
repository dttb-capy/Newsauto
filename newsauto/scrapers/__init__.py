"""Content scrapers for various sources."""

from newsauto.scrapers.aggregator import ContentAggregator
from newsauto.scrapers.base import BaseScraper
from newsauto.scrapers.hackernews import HackerNewsScraper
from newsauto.scrapers.reddit import RedditScraper
from newsauto.scrapers.rss import RSSFetcher

__all__ = [
    "BaseScraper",
    "RSSFetcher",
    "RedditScraper",
    "HackerNewsScraper",
    "ContentAggregator",
]
