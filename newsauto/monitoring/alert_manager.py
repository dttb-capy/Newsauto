"""
Centralized Alert Management System.

Supports multiple channels:
- Slack webhooks
- Discord webhooks
- Email
- PagerDuty API
- Console logging
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp
import yaml

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    """Alert delivery channels."""

    SLACK = "slack"
    DISCORD = "discord"
    EMAIL = "email"
    PAGERDUTY = "pagerduty"
    CONSOLE = "console"


class Alert:
    """Alert message."""

    def __init__(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        component: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        self.title = title
        self.message = message
        self.severity = severity
        self.component = component or "system"
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
        self.alert_id = f"{self.component}_{self.timestamp.strftime('%Y%m%d_%H%M%S')}"


class AlertManager:
    """Centralized alert management."""

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path or "config/alert_rules.yml")
        self.alert_history: List[Alert] = []
        self.rate_limiter: Dict[str, datetime] = {}

    def _load_config(self, path: str) -> Dict:
        """Load alert configuration."""
        try:
            with open(path, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Alert config not found at {path}, using defaults")
            return self._default_config()
        except Exception as e:
            logger.error(f"Error loading alert config: {e}")
            return self._default_config()

    def _default_config(self) -> Dict:
        """Default alert configuration."""
        return {
            "channels": {
                "slack": {"enabled": False, "webhook_url": None},
                "discord": {"enabled": False, "webhook_url": None},
                "email": {"enabled": False, "to": []},
                "pagerduty": {"enabled": False, "integration_key": None},
                "console": {"enabled": True},
            },
            "rules": {
                "high_error_rate": {
                    "severity": "warning",
                    "channels": ["slack", "console"],
                    "rate_limit": 3600,  # 1 hour
                },
                "smtp_blacklisted": {
                    "severity": "critical",
                    "channels": ["slack", "pagerduty", "email"],
                    "rate_limit": 300,  # 5 minutes
                },
                "service_down": {
                    "severity": "critical",
                    "channels": ["pagerduty", "slack"],
                    "rate_limit": 60,  # 1 minute
                },
                "low_quality_content": {
                    "severity": "warning",
                    "channels": ["slack", "email"],
                    "rate_limit": 3600,
                },
            },
            "global_rate_limit": 60,  # Minimum seconds between any two alerts
        }

    async def send_alert(
        self,
        alert: Alert,
        channels: Optional[List[AlertChannel]] = None,
    ) -> Dict[str, bool]:
        """
        Send alert to configured channels.

        Args:
            alert: Alert to send
            channels: Optional specific channels (defaults to rule config)

        Returns:
            Dict of channel: success status
        """
        # Check rate limiting
        if not self._check_rate_limit(alert):
            logger.debug(f"Alert rate-limited: {alert.alert_id}")
            return {}

        # Determine channels
        if channels is None:
            rule_key = alert.metadata.get("rule_key", "default")
            rule = self.config.get("rules", {}).get(rule_key, {})
            channel_names = rule.get("channels", ["console"])
            channels = [AlertChannel(ch) for ch in channel_names]

        # Send to all channels
        tasks = {}
        for channel in channels:
            if self._is_channel_enabled(channel):
                tasks[channel.value] = self._send_to_channel(alert, channel)

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        # Map results back to channels
        status = {}
        for (channel, _), result in zip(tasks.items(), results):
            if isinstance(result, Exception):
                logger.error(f"Alert to {channel} failed: {result}")
                status[channel] = False
            else:
                status[channel] = result

        # Store in history
        self.alert_history.append(alert)
        self._cleanup_history()

        return status

    def _check_rate_limit(self, alert: Alert) -> bool:
        """Check if alert should be rate-limited."""
        now = datetime.utcnow()

        # Check rule-specific rate limit
        rule_key = alert.metadata.get("rule_key")
        if rule_key:
            rule = self.config.get("rules", {}).get(rule_key, {})
            rate_limit_seconds = rule.get("rate_limit", 0)

            key = f"{rule_key}_{alert.component}"
            last_sent = self.rate_limiter.get(key)

            if last_sent and (now - last_sent).total_seconds() < rate_limit_seconds:
                return False

            self.rate_limiter[key] = now

        # Check global rate limit
        global_limit = self.config.get("global_rate_limit", 60)
        if self.rate_limiter.get("_global"):
            if (now - self.rate_limiter["_global"]).total_seconds() < global_limit:
                return False

        self.rate_limiter["_global"] = now
        return True

    def _is_channel_enabled(self, channel: AlertChannel) -> bool:
        """Check if channel is enabled."""
        return self.config.get("channels", {}).get(channel.value, {}).get("enabled", False)

    async def _send_to_channel(self, alert: Alert, channel: AlertChannel) -> bool:
        """Send alert to specific channel."""
        try:
            if channel == AlertChannel.SLACK:
                return await self._send_to_slack(alert)
            elif channel == AlertChannel.DISCORD:
                return await self._send_to_discord(alert)
            elif channel == AlertChannel.EMAIL:
                return await self._send_to_email(alert)
            elif channel == AlertChannel.PAGERDUTY:
                return await self._send_to_pagerduty(alert)
            elif channel == AlertChannel.CONSOLE:
                return self._send_to_console(alert)
            else:
                logger.warning(f"Unknown channel: {channel}")
                return False

        except Exception as e:
            logger.error(f"Error sending alert to {channel}: {e}")
            return False

    async def _send_to_slack(self, alert: Alert) -> bool:
        """Send alert to Slack."""
        webhook_url = self.config["channels"]["slack"].get("webhook_url")
        if not webhook_url:
            return False

        color_map = {
            AlertSeverity.CRITICAL: "#FF0000",
            AlertSeverity.ERROR: "#FF6600",
            AlertSeverity.WARNING: "#FFCC00",
            AlertSeverity.INFO: "#36A64F",
            AlertSeverity.DEBUG: "#CCCCCC",
        }

        payload = {
            "attachments": [
                {
                    "color": color_map.get(alert.severity, "#CCCCCC"),
                    "title": f"{alert.severity.upper()}: {alert.title}",
                    "text": alert.message,
                    "fields": [
                        {"title": "Component", "value": alert.component, "short": True},
                        {
                            "title": "Time",
                            "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "short": True,
                        },
                    ],
                    "footer": "Newsauto Alert System",
                    "ts": int(alert.timestamp.timestamp()),
                }
            ]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                return response.status == 200

    async def _send_to_discord(self, alert: Alert) -> bool:
        """Send alert to Discord."""
        webhook_url = self.config["channels"]["discord"].get("webhook_url")
        if not webhook_url:
            return False

        color_map = {
            AlertSeverity.CRITICAL: 0xFF0000,
            AlertSeverity.ERROR: 0xFF6600,
            AlertSeverity.WARNING: 0xFFCC00,
            AlertSeverity.INFO: 0x36A64F,
            AlertSeverity.DEBUG: 0xCCCCCC,
        }

        payload = {
            "embeds": [
                {
                    "title": f"{alert.severity.upper()}: {alert.title}",
                    "description": alert.message,
                    "color": color_map.get(alert.severity, 0xCCCCCC),
                    "fields": [
                        {"name": "Component", "value": alert.component, "inline": True},
                        {
                            "name": "Time",
                            "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "inline": True,
                        },
                    ],
                    "footer": {"text": "Newsauto Alert System"},
                    "timestamp": alert.timestamp.isoformat(),
                }
            ]
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                return response.status == 204

    async def _send_to_email(self, alert: Alert) -> bool:
        """Send alert via email."""
        email_config = self.config["channels"]["email"]
        recipients = email_config.get("to", [])

        if not recipients:
            return False

        from newsauto.email.email_sender import EmailSender, SMTPConfig
        from newsauto.core.config import get_settings

        settings = get_settings()

        smtp_config = SMTPConfig(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            from_email=settings.smtp_from,
            from_name="Newsauto Alerts",
        )

        sender = EmailSender(smtp_config)

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: {'#FF0000' if alert.severity == AlertSeverity.CRITICAL else '#FFCC00'};">
                {alert.severity.upper()}: {alert.title}
            </h2>
            <p>{alert.message}</p>
            <hr>
            <p><strong>Component:</strong> {alert.component}</p>
            <p><strong>Time:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        </body>
        </html>
        """

        success = True
        for recipient in recipients:
            result = await sender.send_email(
                to_email=recipient,
                subject=f"[{alert.severity.upper()}] {alert.title}",
                html_content=html_content,
            )
            success = success and result

        return success

    async def _send_to_pagerduty(self, alert: Alert) -> bool:
        """Send alert to PagerDuty."""
        integration_key = self.config["channels"]["pagerduty"].get("integration_key")
        if not integration_key:
            return False

        severity_map = {
            AlertSeverity.CRITICAL: "critical",
            AlertSeverity.ERROR: "error",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.INFO: "info",
            AlertSeverity.DEBUG: "info",
        }

        payload = {
            "routing_key": integration_key,
            "event_action": "trigger",
            "dedup_key": alert.alert_id,
            "payload": {
                "summary": alert.title,
                "source": alert.component,
                "severity": severity_map.get(alert.severity, "info"),
                "timestamp": alert.timestamp.isoformat(),
                "custom_details": {
                    "message": alert.message,
                    **alert.metadata,
                },
            },
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload,
            ) as response:
                return response.status == 202

    def _send_to_console(self, alert: Alert) -> bool:
        """Send alert to console (logging)."""
        log_map = {
            AlertSeverity.CRITICAL: logger.critical,
            AlertSeverity.ERROR: logger.error,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.INFO: logger.info,
            AlertSeverity.DEBUG: logger.debug,
        }

        log_func = log_map.get(alert.severity, logger.info)
        log_func(f"[{alert.component}] {alert.title}: {alert.message}")

        return True

    def _cleanup_history(self):
        """Remove old alerts from history."""
        cutoff = datetime.utcnow() - timedelta(days=7)
        self.alert_history = [a for a in self.alert_history if a.timestamp > cutoff]

    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """Get recent alerts."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [
            {
                "title": a.title,
                "message": a.message,
                "severity": a.severity.value,
                "component": a.component,
                "timestamp": a.timestamp.isoformat(),
            }
            for a in self.alert_history
            if a.timestamp > cutoff
        ]


# Global instance
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get singleton alert manager instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


async def send_alert(
    title: str,
    message: str,
    severity: AlertSeverity = AlertSeverity.INFO,
    component: str = "system",
    rule_key: Optional[str] = None,
) -> Dict[str, bool]:
    """
    Convenience function to send an alert.

    Args:
        title: Alert title
        message: Alert message
        severity: Alert severity
        component: Component name
        rule_key: Optional rule key for channel/rate-limit config

    Returns:
        Dict of channel: success status
    """
    manager = get_alert_manager()
    alert = Alert(
        title=title,
        message=message,
        severity=severity,
        component=component,
        metadata={"rule_key": rule_key} if rule_key else {},
    )
    return await manager.send_alert(alert)
