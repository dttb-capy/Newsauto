"""GitHub Trending scraper for high-value engineering content."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from newsauto.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class GitHubTrendingScraper(BaseScraper):
    """Scraper for GitHub trending repositories."""

    BASE_URL = "https://github.com/trending"
    API_BASE = "https://api.github.com/repos"

    async def fetch_raw(self) -> List[Dict[str, Any]]:
        """Fetch trending repositories from GitHub.

        Returns:
            List of trending repositories
        """
        config = self.source.config
        language = config.get("language", "")  # e.g., "python", "typescript"
        since = config.get("since", "daily")  # daily, weekly, monthly
        limit = config.get("limit", 25)

        try:
            # Build URL with parameters
            url = self.BASE_URL
            params = {}
            if language:
                params["language"] = language
            if since:
                params["since"] = since

            # Fetch trending page
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params=params,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; Newsauto/1.0)",
                        "Accept": "text/html",
                    },
                    timeout=30,
                )
                response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")
            repos = []

            # Find all repository articles
            for article in soup.find_all("article", class_="Box-row")[:limit]:
                try:
                    repo_data = self._parse_repo_article(article)
                    if repo_data:
                        # Enhance with API data if we have a token
                        if config.get("github_token"):
                            repo_data = await self._enhance_with_api(
                                repo_data, config["github_token"]
                            )
                        repos.append(repo_data)
                except Exception as e:
                    logger.warning(f"Error parsing repo article: {e}")
                    continue

            logger.info(
                f"Fetched {len(repos)} trending repos from GitHub ({language or 'all'}/{since})"
            )
            return repos

        except Exception as e:
            logger.error(f"Error fetching GitHub trending: {e}")
            raise

    def _parse_repo_article(self, article) -> Optional[Dict[str, Any]]:
        """Parse repository information from HTML article.

        Args:
            article: BeautifulSoup article element

        Returns:
            Parsed repository data
        """
        try:
            # Extract repo name and owner
            h2 = article.find("h2", class_="h3")
            if not h2:
                return None

            repo_link = h2.find("a")
            if not repo_link:
                return None

            repo_path = repo_link.get("href", "").strip("/")
            if "/" not in repo_path:
                return None

            owner, name = repo_path.split("/", 1)

            # Extract description
            description_p = article.find("p", class_="col-9")
            description = description_p.get_text(strip=True) if description_p else ""

            # Extract language
            language_span = article.find("span", {"itemprop": "programmingLanguage"})
            language = language_span.get_text(strip=True) if language_span else ""

            # Extract stars (today's stars)
            stars_span = article.find("span", class_="d-inline-block float-sm-right")
            stars_today = 0
            if stars_span:
                stars_text = stars_span.get_text(strip=True)
                # Parse "123 stars today" or "1,234 stars this week"
                import re

                match = re.search(r"([\d,]+)\s+stars", stars_text)
                if match:
                    stars_today = int(match.group(1).replace(",", ""))

            # Extract total stars
            total_stars = 0
            stars_link = article.find(
                "a", href=lambda x: x and x.endswith("/stargazers")
            )
            if stars_link:
                stars_text = stars_link.get_text(strip=True)
                total_stars = self._parse_number(stars_text)

            # Extract forks
            forks = 0
            forks_link = article.find("a", href=lambda x: x and x.endswith("/forks"))
            if forks_link:
                forks_text = forks_link.get_text(strip=True)
                forks = self._parse_number(forks_text)

            return {
                "owner": owner,
                "name": name,
                "full_name": f"{owner}/{name}",
                "description": description,
                "language": language,
                "stars": total_stars,
                "stars_today": stars_today,
                "forks": forks,
                "url": f"https://github.com/{owner}/{name}",
            }

        except Exception as e:
            logger.error(f"Error parsing repo article: {e}")
            return None

    def _parse_number(self, text: str) -> int:
        """Parse number from text like '1.2k' or '1,234'.

        Args:
            text: Text containing number

        Returns:
            Parsed integer
        """
        import re

        text = text.strip()
        # Handle k suffix
        if text.endswith("k"):
            num = float(text[:-1]) * 1000
            return int(num)
        # Remove commas and parse
        text = re.sub(r"[^\d]", "", text)
        return int(text) if text else 0

    async def _enhance_with_api(
        self, repo_data: Dict[str, Any], token: str
    ) -> Dict[str, Any]:
        """Enhance repository data using GitHub API.

        Args:
            repo_data: Basic repository data
            token: GitHub API token

        Returns:
            Enhanced repository data
        """
        try:
            url = f"{self.API_BASE}/{repo_data['full_name']}"

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers={
                        "Authorization": f"token {token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                    timeout=10,
                )

                if response.status_code == 200:
                    api_data = response.json()
                    # Enhance with additional data
                    repo_data.update(
                        {
                            "created_at": api_data.get("created_at"),
                            "updated_at": api_data.get("updated_at"),
                            "topics": api_data.get("topics", []),
                            "watchers": api_data.get("watchers_count", 0),
                            "open_issues": api_data.get("open_issues_count", 0),
                            "homepage": api_data.get("homepage"),
                        }
                    )

        except Exception as e:
            logger.debug(f"Could not enhance repo data: {e}")

        return repo_data

    def parse_item(self, repo: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse repository into standard content format.

        Args:
            repo: Repository data

        Returns:
            Parsed content item
        """
        try:
            # Build title
            title = f"{repo['full_name']}"
            if repo.get("stars_today"):
                title += f" - {repo['stars_today']} stars today"

            # Build content
            content_parts = []

            if repo.get("description"):
                content_parts.append(f"**Description**: {repo['description']}")

            content_parts.append(f"**Language**: {repo.get('language', 'Unknown')}")
            content_parts.append(f"**Stars**: {repo.get('stars', 0):,}")
            content_parts.append(f"**Forks**: {repo.get('forks', 0):,}")

            if repo.get("topics"):
                content_parts.append(f"**Topics**: {', '.join(repo['topics'][:5])}")

            content_parts.append(f"\n[View on GitHub]({repo['url']})")

            content = "\n\n".join(content_parts)

            # Set published date (use updated_at if available, else current time)
            published_at = datetime.now()
            if repo.get("updated_at"):
                try:
                    published_at = datetime.fromisoformat(
                        repo["updated_at"].replace("Z", "+00:00")
                    )
                except (ValueError, KeyError, AttributeError):
                    pass

            return {
                "url": repo["url"],
                "title": title,
                "author": repo["owner"],
                "content": content,
                "published_at": published_at,
                "metadata": {
                    "source_type": "github",
                    "language": repo.get("language"),
                    "stars": repo.get("stars", 0),
                    "stars_today": repo.get("stars_today", 0),
                    "forks": repo.get("forks", 0),
                },
                # High engagement metrics for scoring
                "score": repo.get("stars_today", 0),
                "upvotes": repo.get("stars", 0),
            }

        except Exception as e:
            logger.error(f"Error parsing GitHub repo: {e}")
            return None
