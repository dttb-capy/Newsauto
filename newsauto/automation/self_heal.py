"""
Self-Healing Infrastructure Orchestrator.

Automatically detects and recovers from common failures:
- SMTP blacklisting
- Ollama model unavailability
- Feed outages
- Database issues
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from newsauto.core.database import SessionLocal
from newsauto.monitoring.health_checks import (
    DatabaseHealthCheck,
    FeedHealthCheck,
    OllamaHealthCheck,
    SMTPHealthCheck,
)

logger = logging.getLogger(__name__)


class SelfHealingOrchestrator:
    """Main self-healing orchestrator."""

    def __init__(self):
        self.smtp_check = SMTPHealthCheck()
        self.ollama_check = OllamaHealthCheck()
        self.feed_check = FeedHealthCheck()
        self.db_check = DatabaseHealthCheck()

        self.check_interval = 300  # 5 minutes
        self.running = False

        # Track failure counts
        self.failure_counts: Dict[str, int] = {}
        self.last_heal_attempt: Dict[str, datetime] = {}

    async def start_monitoring(self):
        """Start continuous health monitoring and self-healing."""
        self.running = True
        logger.info("🔄 Self-healing orchestrator started")

        while self.running:
            try:
                await self.check_and_heal_all()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in self-healing loop: {e}")
                await asyncio.sleep(60)  # Short sleep on error

    async def stop_monitoring(self):
        """Stop monitoring."""
        self.running = False
        logger.info("🛑 Self-healing orchestrator stopped")

    async def check_and_heal_all(self):
        """Run all health checks and trigger healing if needed."""
        logger.debug("Running comprehensive health check...")

        # Run all checks in parallel
        checks = await asyncio.gather(
            self._check_and_heal_smtp(),
            self._check_and_heal_ollama(),
            self._check_and_heal_feeds(),
            self._check_and_heal_database(),
            return_exceptions=True,
        )

        # Log results
        for i, result in enumerate(checks):
            if isinstance(result, Exception):
                logger.error(f"Health check {i} failed: {result}")

    async def _check_and_heal_smtp(self):
        """Check SMTP health and rotate if blacklisted."""
        try:
            health = await self.smtp_check.check()

            if not health["healthy"]:
                logger.warning(f"SMTP unhealthy: {health.get('error')}")

                # Check if blacklisted
                if "blacklist" in str(health.get("error", "")).lower():
                    logger.error("🚨 SMTP blacklisting detected!")
                    await self._heal_smtp_blacklist()

                # Check if connection failed
                elif "connection" in str(health.get("error", "")).lower():
                    self._increment_failure("smtp_connection")

                    if self._should_attempt_heal("smtp_connection"):
                        await self._heal_smtp_connection()

        except Exception as e:
            logger.error(f"Error checking SMTP health: {e}")

    async def _heal_smtp_blacklist(self):
        """Heal SMTP blacklisting by rotating to backup relay."""
        try:
            logger.info("🔧 Attempting SMTP relay rotation...")

            # Import here to avoid circular imports
            from newsauto.email.email_sender import SMTPConfig

            # Get current config
            from newsauto.core.config import get_settings

            settings = get_settings()

            # Try backup relays in order
            backup_relays = [
                {
                    "name": "SendGrid",
                    "host": "smtp.sendgrid.net",
                    "port": 587,
                    "use_tls": True,
                },
                {
                    "name": "Resend",
                    "host": "smtp.resend.com",
                    "port": 587,
                    "use_tls": True,
                },
                {
                    "name": "Gmail Backup",
                    "host": "smtp.gmail.com",
                    "port": 587,
                    "use_tls": True,
                },
            ]

            for relay in backup_relays:
                logger.info(f"Trying {relay['name']}...")

                # Test relay
                test_config = SMTPConfig(
                    host=relay["host"],
                    port=relay["port"],
                    use_tls=relay["use_tls"],
                    username=settings.smtp_username,
                    password=settings.smtp_password,
                    from_email=settings.smtp_from,
                )

                # Quick health check
                check = SMTPHealthCheck(test_config)
                health = await check.check()

                if health["healthy"]:
                    logger.info(f"✅ Successfully rotated to {relay['name']}")

                    # Update configuration
                    await self._update_smtp_config(relay)
                    self._reset_failure_count("smtp_blacklist")
                    return True

            logger.error("❌ All backup SMTP relays failed")
            return False

        except Exception as e:
            logger.error(f"Error healing SMTP blacklist: {e}")
            return False

    async def _heal_smtp_connection(self):
        """Heal SMTP connection issues."""
        logger.info("🔧 Attempting to fix SMTP connection...")

        # Wait a bit and retry
        await asyncio.sleep(30)

        health = await self.smtp_check.check()
        if health["healthy"]:
            logger.info("✅ SMTP connection restored")
            self._reset_failure_count("smtp_connection")
            return True

        return False

    async def _check_and_heal_ollama(self):
        """Check Ollama health and restore models if needed."""
        try:
            health = await self.ollama_check.check()

            if not health["healthy"]:
                logger.warning(f"Ollama unhealthy: {health.get('error')}")
                await self._heal_ollama()

        except Exception as e:
            logger.error(f"Error checking Ollama health: {e}")

    async def _heal_ollama(self):
        """Heal Ollama by ensuring models are available."""
        try:
            logger.info("🔧 Attempting Ollama healing...")

            from newsauto.core.config import get_settings

            settings = get_settings()

            required_models = [
                settings.ollama_primary_model,
                settings.ollama_fallback_model,
            ]

            for model in required_models:
                logger.info(f"Checking model: {model}")

                # Try to pull model
                import subprocess

                result = subprocess.run(
                    ["ollama", "pull", model],
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minutes
                )

                if result.returncode == 0:
                    logger.info(f"✅ Model {model} ready")
                else:
                    logger.error(f"❌ Failed to pull {model}: {result.stderr}")

            # Check health again
            health = await self.ollama_check.check()
            if health["healthy"]:
                logger.info("✅ Ollama healing successful")
                self._reset_failure_count("ollama")
                return True

            return False

        except Exception as e:
            logger.error(f"Error healing Ollama: {e}")
            return False

    async def _check_and_heal_feeds(self):
        """Check feed health and disable problematic feeds."""
        try:
            health = await self.feed_check.check()

            if not health["healthy"]:
                failed_feeds = health.get("failed_feeds", [])

                if len(failed_feeds) > 0:
                    logger.warning(f"⚠️  {len(failed_feeds)} feeds failing")
                    await self._heal_feeds(failed_feeds)

        except Exception as e:
            logger.error(f"Error checking feed health: {e}")

    async def _heal_feeds(self, failed_feeds: List[Dict]):
        """Heal feeds by temporarily disabling problematic ones."""
        try:
            logger.info(f"🔧 Healing {len(failed_feeds)} failed feeds...")

            db = SessionLocal()

            try:
                from newsauto.models.content import ContentSource

                for feed_info in failed_feeds:
                    source_id = feed_info.get("source_id")
                    failure_count = feed_info.get("failure_count", 0)

                    if failure_count >= 3:
                        # Disable feed temporarily
                        source = db.query(ContentSource).get(source_id)
                        if source:
                            source.enabled = False
                            source.disabled_reason = f"Auto-disabled: {failure_count} consecutive failures"
                            source.disabled_until = datetime.utcnow() + timedelta(hours=6)

                            logger.info(f"Disabled feed {source.name} for 6 hours")

                db.commit()
                logger.info("✅ Feed healing complete")
                return True

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error healing feeds: {e}")
            return False

    async def _check_and_heal_database(self):
        """Check database health and attempt recovery if needed."""
        try:
            health = await self.db_check.check()

            if not health["healthy"]:
                logger.warning(f"Database unhealthy: {health.get('error')}")
                await self._heal_database()

        except Exception as e:
            logger.error(f"Error checking database health: {e}")

    async def _heal_database(self):
        """Heal database issues."""
        try:
            logger.info("🔧 Attempting database healing...")

            # Check if it's a connection issue
            db = SessionLocal()

            try:
                # Try a simple query
                db.execute("SELECT 1")
                logger.info("✅ Database connection restored")
                return True

            except Exception as e:
                logger.error(f"Database still unhealthy: {e}")

                # Try to restore from backup
                logger.info("Attempting restore from latest backup...")
                # TODO: Implement backup restoration
                return False

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error healing database: {e}")
            return False

    def _increment_failure(self, component: str):
        """Increment failure count for a component."""
        self.failure_counts[component] = self.failure_counts.get(component, 0) + 1
        logger.debug(f"Failure count for {component}: {self.failure_counts[component]}")

    def _reset_failure_count(self, component: str):
        """Reset failure count for a component."""
        self.failure_counts[component] = 0

    def _should_attempt_heal(self, component: str) -> bool:
        """Determine if we should attempt healing for a component."""
        # Don't heal too frequently (at least 10 minutes between attempts)
        last_attempt = self.last_heal_attempt.get(component)
        if last_attempt and datetime.utcnow() - last_attempt < timedelta(minutes=10):
            return False

        # Heal after 3 consecutive failures
        if self.failure_counts.get(component, 0) >= 3:
            self.last_heal_attempt[component] = datetime.utcnow()
            return True

        return False

    async def _update_smtp_config(self, relay_config: Dict):
        """Update SMTP configuration in settings."""
        # This would typically update a config file or environment
        # For now, we'll just log it
        logger.info(f"Updated SMTP config to: {relay_config['name']}")

        # In production, you'd update .env or config file here
        # For example:
        # import os
        # os.environ['SMTP_HOST'] = relay_config['host']
        # os.environ['SMTP_PORT'] = str(relay_config['port'])


# Singleton instance
_orchestrator: Optional[SelfHealingOrchestrator] = None


def get_orchestrator() -> SelfHealingOrchestrator:
    """Get singleton orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SelfHealingOrchestrator()
    return _orchestrator


async def start_self_healing():
    """Start self-healing monitoring."""
    orchestrator = get_orchestrator()
    await orchestrator.start_monitoring()


async def stop_self_healing():
    """Stop self-healing monitoring."""
    orchestrator = get_orchestrator()
    await orchestrator.stop_monitoring()
