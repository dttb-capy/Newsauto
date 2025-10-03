"""
Enhanced Health Checks for Self-Healing.

Specialized health checks for:
- SMTP servers (blacklist detection)
- Ollama models
- RSS feeds
- Database connections
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import aiohttp
from sqlalchemy import text
from sqlalchemy.orm import Session

from newsauto.core.config import get_settings
from newsauto.core.database import SessionLocal

logger = logging.getLogger(__name__)


class SMTPHealthCheck:
    """SMTP server health checker with blacklist detection."""

    def __init__(self, config=None):
        from newsauto.email.email_sender import SMTPConfig

        self.config = config or SMTPConfig(
            host=get_settings().smtp_host,
            port=get_settings().smtp_port,
            username=get_settings().smtp_username,
            password=get_settings().smtp_password,
        )

        self.canary_email = get_settings().smtp_canary_email or "test@example.com"

    async def check(self) -> Dict:
        """
        Check SMTP server health.

        Returns:
            Health status dict
        """
        try:
            from newsauto.email.email_sender import EmailSender

            sender = EmailSender(self.config)

            # Test connection
            await sender.connect()

            # Send test email to canary address
            test_result = await sender.send_email(
                to_email=self.canary_email,
                subject="Health Check",
                html_content="<html><body>Health check test</body></html>",
            )

            await sender.disconnect()

            if test_result:
                return {
                    "healthy": True,
                    "smtp_host": self.config.host,
                    "smtp_port": self.config.port,
                    "test_send": "success",
                }
            else:
                return {
                    "healthy": False,
                    "smtp_host": self.config.host,
                    "error": "Test email failed - possible blacklisting",
                }

        except Exception as e:
            logger.error(f"SMTP health check failed: {e}")

            # Check if error indicates blacklisting
            error_str = str(e).lower()
            is_blacklisted = any(
                keyword in error_str
                for keyword in ["blacklist", "spam", "reputation", "blocked", "refused"]
            )

            return {
                "healthy": False,
                "smtp_host": self.config.host,
                "error": str(e),
                "blacklisted": is_blacklisted,
            }


class OllamaHealthCheck:
    """Ollama service and model health checker."""

    def __init__(self):
        self.settings = get_settings()
        self.ollama_host = self.settings.ollama_host
        self.required_models = [
            self.settings.ollama_primary_model,
            self.settings.ollama_fallback_model,
        ]

    async def check(self) -> Dict:
        """
        Check Ollama service health.

        Returns:
            Health status dict
        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                # Check service is running
                async with session.get(f"{self.ollama_host}/api/tags") as response:
                    if response.status != 200:
                        return {
                            "healthy": False,
                            "error": f"Ollama service returned {response.status}",
                        }

                    data = await response.json()
                    available_models = [m["name"] for m in data.get("models", [])]

                    # Check required models are available
                    missing_models = []
                    for model in self.required_models:
                        # Match by prefix (e.g., "mistral:7b" matches "mistral:7b-instruct")
                        if not any(model.split(":")[0] in avail for avail in available_models):
                            missing_models.append(model)

                    if missing_models:
                        return {
                            "healthy": False,
                            "error": f"Missing models: {', '.join(missing_models)}",
                            "available_models": available_models,
                            "missing_models": missing_models,
                        }

                    return {
                        "healthy": True,
                        "available_models": available_models,
                        "model_count": len(available_models),
                    }

        except aiohttp.ClientConnectorError:
            return {"healthy": False, "error": "Cannot connect to Ollama service"}
        except asyncio.TimeoutError:
            return {"healthy": False, "error": "Ollama service timeout"}
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return {"healthy": False, "error": str(e)}


class FeedHealthCheck:
    """RSS feed health checker."""

    def __init__(self):
        self.failure_threshold = 3  # Mark feed as failed after 3 consecutive failures

    async def check(self) -> Dict:
        """
        Check health of all RSS feeds.

        Returns:
            Health status dict with failed feeds
        """
        try:
            db = SessionLocal()

            try:
                # Get all enabled content sources
                from newsauto.models.content import ContentSource

                sources = db.query(ContentSource).filter(ContentSource.enabled == True).all()

                if not sources:
                    return {"healthy": True, "total_feeds": 0, "failed_feeds": []}

                # Check each feed's recent failure rate
                failed_feeds = []
                warning_feeds = []

                for source in sources:
                    # Count recent failures (last 24 hours)
                    cutoff = datetime.utcnow() - timedelta(hours=24)

                    # Get failure count from source metadata
                    failure_count = source.metadata.get("consecutive_failures", 0) if source.metadata else 0

                    if failure_count >= self.failure_threshold:
                        failed_feeds.append(
                            {
                                "source_id": source.id,
                                "name": source.name,
                                "url": source.url,
                                "failure_count": failure_count,
                            }
                        )
                    elif failure_count > 0:
                        warning_feeds.append(
                            {
                                "source_id": source.id,
                                "name": source.name,
                                "failure_count": failure_count,
                            }
                        )

                # Calculate failure rate
                total_feeds = len(sources)
                failure_rate = len(failed_feeds) / total_feeds if total_feeds > 0 else 0

                # Unhealthy if >20% of feeds are failing
                is_healthy = failure_rate < 0.20

                return {
                    "healthy": is_healthy,
                    "total_feeds": total_feeds,
                    "failed_feeds": failed_feeds,
                    "warning_feeds": warning_feeds,
                    "failure_rate": round(failure_rate, 3),
                }

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Feed health check failed: {e}")
            return {"healthy": False, "error": str(e)}


class DatabaseHealthCheck:
    """Database connection and integrity checker."""

    def __init__(self):
        pass

    async def check(self) -> Dict:
        """
        Check database health.

        Returns:
            Health status dict
        """
        try:
            db = SessionLocal()

            try:
                # Test basic query
                result = db.execute(text("SELECT 1")).scalar()

                if result != 1:
                    return {"healthy": False, "error": "Query returned unexpected result"}

                # Check table existence
                tables_query = text(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                )
                table_count = db.execute(tables_query).scalar()

                if table_count < 5:  # Expect at least 5 core tables
                    return {
                        "healthy": False,
                        "error": f"Only {table_count} tables found (expected >=5)",
                    }

                # Check database file size
                import os

                db_url = get_settings().database_url
                if "sqlite" in db_url:
                    db_path = db_url.replace("sqlite:///", "")
                    if os.path.exists(db_path):
                        db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
                    else:
                        db_size_mb = 0
                else:
                    db_size_mb = None

                return {
                    "healthy": True,
                    "table_count": table_count,
                    "db_size_mb": round(db_size_mb, 2) if db_size_mb else None,
                    "connection": "ok",
                }

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"healthy": False, "error": str(e), "connection": "failed"}


class ComprehensiveHealthCheck:
    """Comprehensive health check orchestrator."""

    def __init__(self):
        self.smtp_check = SMTPHealthCheck()
        self.ollama_check = OllamaHealthCheck()
        self.feed_check = FeedHealthCheck()
        self.db_check = DatabaseHealthCheck()

    async def check_all(self) -> Dict:
        """
        Run all health checks.

        Returns:
            Complete health status
        """
        try:
            # Run all checks in parallel
            smtp, ollama, feeds, database = await asyncio.gather(
                self.smtp_check.check(),
                self.ollama_check.check(),
                self.feed_check.check(),
                self.db_check.check(),
                return_exceptions=True,
            )

            # Process results
            checks = {
                "smtp": smtp if not isinstance(smtp, Exception) else {"healthy": False, "error": str(smtp)},
                "ollama": ollama if not isinstance(ollama, Exception) else {"healthy": False, "error": str(ollama)},
                "feeds": feeds if not isinstance(feeds, Exception) else {"healthy": False, "error": str(feeds)},
                "database": database if not isinstance(database, Exception) else {"healthy": False, "error": str(database)},
            }

            # Overall health
            all_healthy = all(check.get("healthy", False) for check in checks.values())

            return {
                "overall_healthy": all_healthy,
                "timestamp": datetime.utcnow().isoformat(),
                "checks": checks,
            }

        except Exception as e:
            logger.error(f"Comprehensive health check failed: {e}")
            return {
                "overall_healthy": False,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }
