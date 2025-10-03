#!/usr/bin/env python3
"""
Content Army: Zero-touch content automation battalion.
Handles RSS fetching, LLM processing, and newsletter generation.
Designed for maximum parallelization and zero human intervention.
"""

import asyncio
import aiohttp
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import hashlib
import json
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from newsauto.core.config import get_settings
from newsauto.models.newsletter import Newsletter, NewsletterStatus
from newsauto.models.content import ContentItem, ContentSource
from newsauto.models.edition import Edition, EditionStatus
from newsauto.llm.ollama_client import OllamaClient
from newsauto.email.delivery_manager import DeliveryManager
from newsauto.email.email_sender import EmailSender, SMTPConfig
import feedparser

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


class ContentBattalion:
    """Main content operations battalion."""

    def __init__(self):
        """Initialize the content battalion."""
        self.engine = create_engine(settings.database_url)
        self.Session = sessionmaker(bind=self.engine)
        self.ollama = OllamaClient()
        self.cache = {}  # Simple in-memory cache
        self.stats = {
            "feeds_processed": 0,
            "articles_fetched": 0,
            "articles_summarized": 0,
            "newsletters_generated": 0,
            "emails_sent": 0
        }

    async def execute_daily_operations(self):
        """Execute complete daily content operations."""
        logger.info("🚀 CONTENT BATTALION: INITIATING DAILY OPERATIONS")
        logger.info("="*70)

        start_time = datetime.now()

        # Phase 1: Content Aggregation
        logger.info("\n📡 PHASE 1: CONTENT AGGREGATION")
        content = await self.aggregate_all_content()

        # Phase 2: Content Processing
        logger.info("\n🤖 PHASE 2: LLM PROCESSING")
        processed = await self.process_with_llm(content)

        # Phase 3: Newsletter Generation
        logger.info("\n📰 PHASE 3: NEWSLETTER GENERATION")
        newsletters = await self.generate_all_newsletters(processed)

        # Phase 4: Delivery
        logger.info("\n📧 PHASE 4: BATCH DELIVERY")
        delivery_results = await self.deliver_newsletters(newsletters)

        # Report
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        await self.generate_battle_report(duration)

        return self.stats

    async def aggregate_all_content(self) -> List[Dict]:
        """Aggregate content from all sources in parallel."""
        session = self.Session()

        try:
            # Get all active content sources
            sources = session.query(ContentSource).filter(
                ContentSource.is_active == True
            ).all()

            logger.info(f"Found {len(sources)} active content sources")

            # Create tasks for parallel fetching
            tasks = []
            for source in sources:
                task = self.fetch_source(source)
                tasks.append(task)

            # Execute all fetches in parallel (batches of 10)
            all_content = []
            for i in range(0, len(tasks), 10):
                batch = tasks[i:i+10]
                batch_results = await asyncio.gather(*batch, return_exceptions=True)

                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Error fetching source: {result}")
                    else:
                        all_content.extend(result)

            # Deduplicate content
            unique_content = self.deduplicate_content(all_content)

            self.stats["feeds_processed"] = len(sources)
            self.stats["articles_fetched"] = len(unique_content)

            logger.info(f"✅ Fetched {len(unique_content)} unique articles from {len(sources)} sources")
            return unique_content

        finally:
            session.close()

    async def fetch_source(self, source: ContentSource) -> List[Dict]:
        """Fetch content from a single source."""
        try:
            if source.source_type == "rss":
                return await self.fetch_rss(source.url, source.name)
            else:
                logger.warning(f"Unsupported source type: {source.source_type}")
                return []
        except Exception as e:
            logger.error(f"Error fetching {source.name}: {e}")
            return []

    async def fetch_rss(self, url: str, source_name: str) -> List[Dict]:
        """Fetch RSS feed content."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    content = await response.text()
                    feed = feedparser.parse(content)

                    articles = []
                    for entry in feed.entries[:10]:  # Limit to 10 per feed
                        article = {
                            "source": source_name,
                            "url": entry.get("link", ""),
                            "title": entry.get("title", ""),
                            "content": entry.get("summary", ""),
                            "published": entry.get("published", ""),
                            "hash": hashlib.md5(
                                entry.get("link", "").encode()
                            ).hexdigest()
                        }
                        articles.append(article)

                    return articles
        except Exception as e:
            logger.error(f"RSS fetch error for {source_name}: {e}")
            return []

    def deduplicate_content(self, content: List[Dict]) -> List[Dict]:
        """Remove duplicate content based on URL hash."""
        seen_hashes = set()
        unique = []

        for item in content:
            if item["hash"] not in seen_hashes:
                seen_hashes.add(item["hash"])
                unique.append(item)

        logger.info(f"Deduplication: {len(content)} → {len(unique)} articles")
        return unique

    async def process_with_llm(self, content: List[Dict]) -> List[Dict]:
        """Process content with LLM in parallel batches."""
        processed = []

        # Process in batches of 5 for parallel LLM calls
        for i in range(0, len(content), 5):
            batch = content[i:i+5]

            # Create summarization tasks
            tasks = []
            for article in batch:
                # Check cache first
                if article["hash"] in self.cache:
                    processed.append(self.cache[article["hash"]])
                    continue

                task = self.summarize_article(article)
                tasks.append(task)

            # Execute batch
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for article, result in zip(batch, results):
                    if isinstance(result, Exception):
                        logger.error(f"LLM error: {result}")
                        article["summary"] = article["content"][:500]
                    else:
                        article["summary"] = result
                        self.cache[article["hash"]] = article

                    processed.append(article)

        self.stats["articles_summarized"] = len(processed)
        logger.info(f"✅ Processed {len(processed)} articles with LLM")
        return processed

    async def summarize_article(self, article: Dict) -> str:
        """Summarize a single article with LLM."""
        try:
            prompt = f"""Summarize this article for C-suite executives in 3-4 sentences.
            Focus on strategic implications and actionable insights.

            Title: {article['title']}
            Content: {article['content'][:1000]}

            Summary:"""

            # Use Ollama for summarization
            response = await self.ollama.generate(
                prompt=prompt,
                model=settings.primary_model,
                temperature=0.7,
                max_tokens=150
            )

            return response.strip()
        except Exception as e:
            logger.error(f"Summarization error: {e}")
            return article["content"][:500]

    async def generate_all_newsletters(self, content: List[Dict]) -> List[Dict]:
        """Generate newsletters for all active newsletters."""
        session = self.Session()

        try:
            # Get active newsletters
            newsletters = session.query(Newsletter).filter(
                Newsletter.status == NewsletterStatus.ACTIVE
            ).all()

            generated = []

            for newsletter in newsletters:
                # Filter content relevant to this newsletter
                relevant_content = self.filter_content_for_newsletter(
                    content, newsletter
                )

                if len(relevant_content) < 3:
                    logger.warning(f"Not enough content for {newsletter.name}")
                    continue

                # Create edition
                edition = Edition(
                    newsletter_id=newsletter.id,
                    subject=f"{newsletter.name} - {datetime.now().strftime('%B %d, %Y')}",
                    content={
                        "articles": relevant_content[:10],  # Top 10 articles
                        "executive_summary": self.create_executive_summary(relevant_content),
                        "metrics": self.generate_metrics(newsletter)
                    },
                    status=EditionStatus.DRAFT,
                    scheduled_for=datetime.now(),
                    created_at=datetime.now()
                )
                session.add(edition)

                generated.append({
                    "newsletter": newsletter,
                    "edition": edition,
                    "content": relevant_content
                })

                logger.info(f"✅ Generated newsletter: {newsletter.name}")

            session.commit()
            self.stats["newsletters_generated"] = len(generated)
            return generated

        finally:
            session.close()

    def filter_content_for_newsletter(
        self, content: List[Dict], newsletter: Newsletter
    ) -> List[Dict]:
        """Filter content based on newsletter niche and keywords."""
        # Simple keyword matching for now
        niche_keywords = {
            "engineering_leadership": ["cto", "engineering", "scale", "team", "architecture"],
            "saas_business": ["saas", "arr", "mrr", "growth", "startup"],
            "career_development": ["principal", "engineer", "career", "promotion", "interview"],
            "defense_technology": ["defense", "dod", "pentagon", "military", "procurement"],
            "veteran_business": ["veteran", "military", "transition", "leadership"],
            "talent_acquisition": ["hiring", "remote", "latam", "talent", "developer"],
            "faith_technology": ["church", "faith", "ministry", "religious", "community"],
            "investment_tech": ["investment", "family office", "venture", "portfolio"],
            "agency_business": ["agency", "no-code", "freelance", "client", "webflow"],
            "succession_planning": ["succession", "family business", "transition", "legacy"]
        }

        keywords = niche_keywords.get(newsletter.niche, [])

        relevant = []
        for article in content:
            # Check if any keyword appears in title or content
            text = f"{article['title']} {article.get('summary', article['content'])}".lower()

            if any(keyword in text for keyword in keywords):
                article["relevance_score"] = sum(
                    1 for keyword in keywords if keyword in text
                )
                relevant.append(article)

        # Sort by relevance score
        relevant.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return relevant

    def create_executive_summary(self, content: List[Dict]) -> str:
        """Create executive summary from top articles."""
        if not content:
            return "No significant updates this week."

        summary_points = []
        for article in content[:3]:  # Top 3 articles
            summary_points.append(f"• {article['title']}: {article.get('summary', '')[:100]}")

        return "\n".join(summary_points)

    def generate_metrics(self, newsletter: Newsletter) -> Dict:
        """Generate newsletter metrics."""
        return {
            "subscriber_count": newsletter.subscriber_count,
            "projected_revenue": newsletter.subscriber_count * newsletter.settings.get("price_monthly", 0),
            "open_rate_target": newsletter.settings.get("target_open_rate", 0.40),
            "click_rate_target": newsletter.settings.get("target_click_rate", 0.05)
        }

    async def deliver_newsletters(self, newsletters: List[Dict]) -> Dict:
        """Deliver newsletters to subscribers."""
        session = self.Session()

        try:
            # Setup SMTP
            smtp_config = SMTPConfig(
                host=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                use_tls=settings.smtp_tls
            )

            delivery_manager = DeliveryManager(session, smtp_config)

            results = {
                "sent": 0,
                "failed": 0
            }

            for item in newsletters:
                newsletter = item["newsletter"]
                edition = item["edition"]

                try:
                    # For testing, just send to test email
                    result = await delivery_manager.send_edition(
                        edition_id=edition.id,
                        test_mode=True,
                        test_emails=["erick.durantt@gmail.com"]
                    )

                    results["sent"] += len(result.get("sent", []))
                    results["failed"] += len(result.get("failed", []))

                    logger.info(f"📧 Sent {newsletter.name} to test subscribers")

                except Exception as e:
                    logger.error(f"Delivery error for {newsletter.name}: {e}")
                    results["failed"] += 1

            self.stats["emails_sent"] = results["sent"]
            return results

        finally:
            session.close()

    async def generate_battle_report(self, duration: float):
        """Generate operations report."""
        logger.info("\n" + "="*70)
        logger.info("📊 BATTLE REPORT: CONTENT OPERATIONS COMPLETE")
        logger.info("="*70)

        logger.info(f"⏱️  Duration: {duration:.2f} seconds")
        logger.info(f"📡 Feeds Processed: {self.stats['feeds_processed']}")
        logger.info(f"📰 Articles Fetched: {self.stats['articles_fetched']}")
        logger.info(f"🤖 Articles Summarized: {self.stats['articles_summarized']}")
        logger.info(f"📧 Newsletters Generated: {self.stats['newsletters_generated']}")
        logger.info(f"✉️  Emails Sent: {self.stats['emails_sent']}")

        # Calculate efficiency
        if self.stats['articles_fetched'] > 0:
            processing_rate = self.stats['articles_summarized'] / duration
            logger.info(f"⚡ Processing Rate: {processing_rate:.2f} articles/second")

        # Save report to file
        report_path = Path("logs/content_army_report.json")
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
                "stats": self.stats
            }, f, indent=2)

        logger.info(f"\n✅ Report saved to: {report_path}")


async def main():
    """Main execution function."""
    battalion = ContentBattalion()

    # Execute daily operations
    results = await battalion.execute_daily_operations()

    # Return results for monitoring
    return results


if __name__ == "__main__":
    # Run the content army
    asyncio.run(main())