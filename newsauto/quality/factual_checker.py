"""
Factual Accuracy Checker.

Cross-references generated content with source URLs and known facts.
"""

import asyncio
import logging
import re
from typing import Dict, Optional
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger(__name__)


class FactualChecker:
    """Checks factual accuracy of generated content."""

    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=10)
        self.session: Optional[aiohttp.ClientSession] = None

        # Known reliable source domains
        self.trusted_sources = {
            "nytimes.com",
            "reuters.com",
            "apnews.com",
            "bbc.com",
            "theguardian.com",
            "wsj.com",
            "ft.com",
            "bloomberg.com",
            "techcrunch.com",
            "arstechnica.com",
            "wired.com",
            "nature.com",
            "science.org",
        }

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self.session

    async def close(self):
        """Close aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def check(self, summary: str, source_url: str) -> float:
        """
        Check factual accuracy of summary against source.

        Args:
            summary: Generated summary
            source_url: Original source URL

        Returns:
            Score from 0.0 (low accuracy) to 1.0 (high accuracy)
        """
        try:
            if not summary or not source_url:
                return 0.5  # Neutral score

            # Score components
            scores = []

            # 1. Source credibility check
            credibility_score = self._check_source_credibility(source_url)
            scores.append(credibility_score * 0.35)  # 35% weight

            # 2. URL accessibility check
            accessibility_score = await self._check_url_accessible(source_url)
            scores.append(accessibility_score * 0.25)  # 25% weight

            # 3. Content consistency (if we can fetch source)
            if accessibility_score > 0.5:
                try:
                    source_content = await self._fetch_source_content(source_url)
                    if source_content:
                        consistency_score = self._check_content_consistency(
                            summary, source_content
                        )
                        scores.append(consistency_score * 0.40)  # 40% weight
                    else:
                        # Use credibility as proxy if can't fetch content
                        scores.append(credibility_score * 0.40)
                except Exception:
                    scores.append(credibility_score * 0.40)
            else:
                scores.append(credibility_score * 0.40)

            final_score = sum(scores)

            logger.debug(
                f"Factual check for {source_url[:50]}: "
                f"credibility={credibility_score:.2f}, "
                f"accessible={accessibility_score:.2f}, "
                f"final={final_score:.2f}"
            )

            return round(final_score, 3)

        except Exception as e:
            logger.error(f"Error in factual checking: {e}")
            return 0.5  # Neutral score on error

    def _check_source_credibility(self, url: str) -> float:
        """Check if source is from a credible domain."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Remove www. prefix
            domain = domain.replace("www.", "")

            # Check against trusted sources
            for trusted in self.trusted_sources:
                if trusted in domain:
                    return 1.0  # High credibility

            # Check for academic/government domains
            if domain.endswith((".edu", ".gov", ".ac.uk", ".edu.au")):
                return 0.95

            # Check for known tech blogs/news sites
            known_tech = [
                "github.com",
                "stackoverflow.com",
                "medium.com",
                "dev.to",
                "hackernews.com",
                "reddit.com",
            ]
            if any(site in domain for site in known_tech):
                return 0.75

            # Unknown source - medium credibility
            return 0.60

        except Exception as e:
            logger.error(f"Error checking source credibility: {e}")
            return 0.50

    async def _check_url_accessible(self, url: str) -> float:
        """Check if URL is accessible."""
        try:
            session = await self.get_session()

            async with session.head(url, allow_redirects=True) as response:
                if response.status == 200:
                    return 1.0
                elif response.status in (301, 302, 307, 308):
                    return 0.8  # Redirects are okay
                elif response.status == 403:
                    return 0.6  # Forbidden but exists
                elif response.status == 404:
                    return 0.0  # Not found
                else:
                    return 0.4  # Other errors

        except asyncio.TimeoutError:
            logger.warning(f"Timeout checking {url}")
            return 0.3
        except Exception as e:
            logger.error(f"Error checking URL accessibility: {e}")
            return 0.3

    async def _fetch_source_content(self, url: str) -> Optional[str]:
        """Fetch source content for comparison."""
        try:
            session = await self.get_session()

            async with session.get(url, allow_redirects=True) as response:
                if response.status == 200:
                    # Only fetch text content
                    content_type = response.headers.get("Content-Type", "")
                    if "text/html" in content_type or "text/plain" in content_type:
                        text = await response.text()
                        # Limit to first 50KB to avoid memory issues
                        return text[:50000]

            return None

        except Exception as e:
            logger.error(f"Error fetching source content: {e}")
            return None

    def _check_content_consistency(self, summary: str, source_content: str) -> float:
        """Check if summary is consistent with source content."""
        try:
            # Clean source content (remove HTML tags)
            clean_source = re.sub(r"<[^>]+>", " ", source_content)
            clean_source = re.sub(r"\s+", " ", clean_source).lower()

            summary_lower = summary.lower()

            # Extract key phrases from summary (3-5 word sequences)
            summary_words = summary_lower.split()
            key_phrases = []

            for i in range(len(summary_words) - 2):
                # 3-word phrases
                phrase = " ".join(summary_words[i : i + 3])
                # Skip common phrases
                if len(phrase) > 15 and not phrase.startswith(("the ", "and ", "but ")):
                    key_phrases.append(phrase)

            if not key_phrases:
                return 0.7  # Neutral if no phrases to check

            # Check how many key phrases appear in source
            matches = sum(1 for phrase in key_phrases if phrase in clean_source)

            consistency_ratio = matches / len(key_phrases)

            # Be generous - even 40% match is decent
            adjusted_score = min(1.0, consistency_ratio * 2.0)

            return adjusted_score

        except Exception as e:
            logger.error(f"Error checking content consistency: {e}")
            return 0.5

    def get_credibility_report(self, url: str) -> Dict:
        """Get detailed credibility report for a source."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")

        is_trusted = any(trusted in domain for trusted in self.trusted_sources)
        is_academic = domain.endswith((".edu", ".gov", ".ac.uk"))

        return {
            "url": url,
            "domain": domain,
            "is_trusted_source": is_trusted,
            "is_academic": is_academic,
            "credibility_score": self._check_source_credibility(url),
            "trust_level": self._classify_trust(self._check_source_credibility(url)),
        }

    def _classify_trust(self, score: float) -> str:
        """Classify trust level from score."""
        if score >= 0.90:
            return "high"
        elif score >= 0.70:
            return "medium"
        else:
            return "low"
