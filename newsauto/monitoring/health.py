"""Health check and monitoring endpoints."""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from newsauto.core.config import get_settings
from newsauto.core.database import get_db

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth:
    """Health status of a component."""

    def __init__(
        self,
        name: str,
        status: HealthStatus,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize component health.

        Args:
            name: Component name
            status: Health status
            message: Optional status message
            details: Optional additional details
        """
        self.name = name
        self.status = status
        self.message = message or f"{name} is {status}"
        self.details = details or {}
        self.checked_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Health status dictionary
        """
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "checked_at": self.checked_at.isoformat(),
        }


class HealthChecker:
    """Application health checker."""

    def __init__(self, db: Optional[Session] = None):
        """Initialize health checker.

        Args:
            db: Optional database session
        """
        self.db = db
        self.settings = get_settings()
        self.last_check: Optional[datetime] = None
        self.cached_status: Optional[Dict[str, Any]] = None
        self.cache_duration = timedelta(seconds=10)

    async def check_database(self) -> ComponentHealth:
        """Check database health.

        Returns:
            Database health status
        """
        try:
            if not self.db:
                self.db = next(get_db())

            # Execute simple query
            result = self.db.execute(text("SELECT 1"))
            result.fetchone()

            # Check table count
            tables = self.db.execute(
                text("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            ).scalar()

            return ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                details={"tables": tables, "connected": True},
            )

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {str(e)}",
                details={"connected": False, "error": str(e)},
            )

    async def check_ollama(self) -> ComponentHealth:
        """Check Ollama service health.

        Returns:
            Ollama health status
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.settings.ollama_host}/api/tags")

                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    model_names = [m.get("name") for m in models]

                    # Check if required models are available
                    required_models = [
                        self.settings.ollama_primary_model,
                        self.settings.ollama_fallback_model,
                    ]

                    missing_models = [
                        m
                        for m in required_models
                        if not any(m in name for name in model_names)
                    ]

                    if missing_models:
                        return ComponentHealth(
                            name="ollama",
                            status=HealthStatus.DEGRADED,
                            message=f"Missing models: {', '.join(missing_models)}",
                            details={
                                "available_models": model_names,
                                "missing_models": missing_models,
                            },
                        )

                    return ComponentHealth(
                        name="ollama",
                        status=HealthStatus.HEALTHY,
                        details={
                            "models": len(models),
                            "available_models": model_names[:5],  # First 5 models
                        },
                    )
                else:
                    return ComponentHealth(
                        name="ollama",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Ollama returned status {response.status_code}",
                    )

        except httpx.TimeoutException:
            return ComponentHealth(
                name="ollama",
                status=HealthStatus.UNHEALTHY,
                message="Ollama service timeout",
            )
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return ComponentHealth(
                name="ollama",
                status=HealthStatus.UNHEALTHY,
                message=f"Ollama error: {str(e)}",
            )

    async def check_redis(self) -> ComponentHealth:
        """Check Redis health.

        Returns:
            Redis health status
        """
        try:
            import redis.asyncio as redis

            client = redis.from_url(
                self.settings.redis_url or "redis://localhost:6379",
                decode_responses=True,
            )

            # Ping Redis
            await client.ping()

            # Get info
            info = await client.info()
            memory_used = info.get("used_memory_human", "N/A")
            connected_clients = info.get("connected_clients", 0)

            await client.close()

            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                details={
                    "memory_used": memory_used,
                    "connected_clients": connected_clients,
                },
            )

        except Exception as e:
            # Redis is optional, so degraded not unhealthy
            return ComponentHealth(
                name="redis",
                status=HealthStatus.DEGRADED,
                message=f"Redis not available: {str(e)}",
                details={"available": False},
            )

    async def check_disk_space(self) -> ComponentHealth:
        """Check disk space.

        Returns:
            Disk space health status
        """
        try:
            import psutil

            disk = psutil.disk_usage("/")
            free_gb = disk.free / (1024**3)
            percent_used = disk.percent

            if percent_used > 90:
                status = HealthStatus.UNHEALTHY
                message = f"Critical: Disk {percent_used:.1f}% full"
            elif percent_used > 80:
                status = HealthStatus.DEGRADED
                message = f"Warning: Disk {percent_used:.1f}% full"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk {percent_used:.1f}% used"

            return ComponentHealth(
                name="disk",
                status=status,
                message=message,
                details={
                    "free_gb": round(free_gb, 2),
                    "percent_used": percent_used,
                    "total_gb": round(disk.total / (1024**3), 2),
                },
            )

        except Exception as e:
            return ComponentHealth(
                name="disk",
                status=HealthStatus.DEGRADED,
                message=f"Could not check disk: {str(e)}",
            )

    async def check_memory(self) -> ComponentHealth:
        """Check memory usage.

        Returns:
            Memory health status
        """
        try:
            import psutil

            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            percent_used = memory.percent

            if percent_used > 90:
                status = HealthStatus.UNHEALTHY
                message = f"Critical: Memory {percent_used:.1f}% used"
            elif percent_used > 80:
                status = HealthStatus.DEGRADED
                message = f"Warning: Memory {percent_used:.1f}% used"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory {percent_used:.1f}% used"

            return ComponentHealth(
                name="memory",
                status=status,
                message=message,
                details={
                    "available_gb": round(available_gb, 2),
                    "percent_used": percent_used,
                    "total_gb": round(memory.total / (1024**3), 2),
                },
            )

        except Exception as e:
            return ComponentHealth(
                name="memory",
                status=HealthStatus.DEGRADED,
                message=f"Could not check memory: {str(e)}",
            )

    async def check_all(self) -> Dict[str, Any]:
        """Check all components.

        Returns:
            Complete health status
        """
        # Check cache
        now = datetime.utcnow()
        if self.cached_status and self.last_check:
            if now - self.last_check < self.cache_duration:
                return self.cached_status

        # Run all health checks concurrently
        checks = await asyncio.gather(
            self.check_database(),
            self.check_ollama(),
            self.check_redis(),
            self.check_disk_space(),
            self.check_memory(),
            return_exceptions=True,
        )

        # Process results
        components = []
        overall_status = HealthStatus.HEALTHY

        for check in checks:
            if isinstance(check, Exception):
                logger.error(f"Health check error: {check}")
                components.append(
                    ComponentHealth(
                        name="unknown",
                        status=HealthStatus.UNHEALTHY,
                        message=str(check),
                    ).to_dict()
                )
                overall_status = HealthStatus.UNHEALTHY
            else:
                components.append(check.to_dict())

                # Update overall status
                if check.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif (
                    check.status == HealthStatus.DEGRADED
                    and overall_status == HealthStatus.HEALTHY
                ):
                    overall_status = HealthStatus.DEGRADED

        # Build response
        self.cached_status = {
            "status": overall_status,
            "timestamp": now.isoformat(),
            "components": components,
            "version": self.settings.app_version,
            "environment": "production" if not self.settings.debug else "development",
        }

        self.last_check = now
        return self.cached_status

    async def check_readiness(self) -> Dict[str, Any]:
        """Check if application is ready to serve requests.

        Returns:
            Readiness status
        """
        # Check only critical components for readiness
        db_health = await self.check_database()

        ready = db_health.status != HealthStatus.UNHEALTHY

        return {
            "ready": ready,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {"database": db_health.status},
        }

    async def check_liveness(self) -> Dict[str, Any]:
        """Check if application is alive.

        Returns:
            Liveness status
        """
        # Simple liveness check - if we can respond, we're alive
        return {"alive": True, "timestamp": datetime.utcnow().isoformat()}


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get health checker instance.

    Returns:
        Health checker instance
    """
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


async def get_health_status() -> Dict[str, Any]:
    """Get current health status.

    Returns:
        Health status dictionary
    """
    checker = get_health_checker()
    return await checker.check_all()


class SystemMonitor:
    """Monitor system resources and performance."""

    def __init__(self):
        """Initialize system monitor."""
        self.alerts: List[Dict[str, Any]] = []
        self.thresholds = {
            "cpu_percent": 80,
            "memory_percent": 85,
            "disk_percent": 90,
            "response_time_ms": 2000,
        }

    def check_thresholds(self, metrics: Dict[str, Any]):
        """Check if any metrics exceed thresholds.

        Args:
            metrics: Current metrics
        """
        alerts = []

        # Check CPU
        if (
            metrics.get("system", {}).get("cpu_percent", 0)
            > self.thresholds["cpu_percent"]
        ):
            alerts.append(
                {
                    "level": "warning",
                    "component": "cpu",
                    "message": f"CPU usage high: {metrics['system']['cpu_percent']:.1f}%",
                }
            )

        # Check memory
        if (
            metrics.get("system", {}).get("memory_percent", 0)
            > self.thresholds["memory_percent"]
        ):
            alerts.append(
                {
                    "level": "warning",
                    "component": "memory",
                    "message": f"Memory usage high: {metrics['system']['memory_percent']:.1f}%",
                }
            )

        # Check disk
        if (
            metrics.get("system", {}).get("disk_percent", 0)
            > self.thresholds["disk_percent"]
        ):
            alerts.append(
                {
                    "level": "critical",
                    "component": "disk",
                    "message": f"Disk usage critical: {metrics['system']['disk_percent']:.1f}%",
                }
            )

        # Add alerts with timestamp
        for alert in alerts:
            alert["timestamp"] = datetime.utcnow()
            self.alerts.append(alert)
            logger.warning(f"Alert: {alert['message']}")

        # Keep only recent alerts
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self.alerts = [a for a in self.alerts if a["timestamp"] > cutoff]

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get current alerts.

        Returns:
            List of alerts
        """
        return [
            {**alert, "timestamp": alert["timestamp"].isoformat()}
            for alert in self.alerts
        ]
