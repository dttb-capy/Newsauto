"""Metrics collection and monitoring."""

import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, Optional

import psutil
from fastapi import Request, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# Prometheus metrics
request_count = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

request_duration = Histogram(
    "http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"]
)

active_users = Gauge("active_users_total", "Number of active users")

newsletter_sends = Counter(
    "newsletter_sends_total", "Total newsletter sends", ["newsletter_id", "status"]
)

content_fetches = Counter(
    "content_fetches_total", "Total content fetches", ["source", "status"]
)

llm_requests = Counter(
    "llm_requests_total", "Total LLM API requests", ["model", "operation"]
)

llm_tokens = Counter("llm_tokens_total", "Total LLM tokens used", ["model", "type"])

email_sends = Counter("email_sends_total", "Total emails sent", ["status"])

subscriber_events = Counter(
    "subscriber_events_total", "Subscriber events", ["event_type"]
)

# System metrics
cpu_usage = Gauge("system_cpu_percent", "CPU usage percentage")
memory_usage = Gauge("system_memory_percent", "Memory usage percentage")
disk_usage = Gauge("system_disk_percent", "Disk usage percentage")


class MetricsCollector:
    """Collects and manages application metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.start_time = datetime.utcnow()
        self.request_times: Dict[str, list] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.cache_hits = 0
        self.cache_misses = 0

    def record_request(
        self, method: str, endpoint: str, status_code: int, duration: float
    ):
        """Record HTTP request metrics.

        Args:
            method: HTTP method
            endpoint: API endpoint
            status_code: Response status code
            duration: Request duration in seconds
        """
        # Prometheus metrics
        request_count.labels(method=method, endpoint=endpoint, status=status_code).inc()
        request_duration.labels(method=method, endpoint=endpoint).observe(duration)

        # Internal tracking
        key = f"{method}:{endpoint}"
        self.request_times[key].append(duration)

        # Keep only last 1000 requests per endpoint
        if len(self.request_times[key]) > 1000:
            self.request_times[key] = self.request_times[key][-1000:]

        # Track errors
        if status_code >= 400:
            self.error_counts[key] += 1

    def record_newsletter_send(
        self, newsletter_id: int, success: bool, recipient_count: int = 1
    ):
        """Record newsletter send metrics.

        Args:
            newsletter_id: Newsletter ID
            success: Whether send was successful
            recipient_count: Number of recipients
        """
        status = "success" if success else "failed"
        newsletter_sends.labels(newsletter_id=newsletter_id, status=status).inc(
            recipient_count
        )

    def record_content_fetch(self, source: str, success: bool, item_count: int = 0):
        """Record content fetch metrics.

        Args:
            source: Content source
            success: Whether fetch was successful
            item_count: Number of items fetched
        """
        status = "success" if success else "failed"
        content_fetches.labels(source=source, status=status).inc()

        if success:
            logger.info(f"Fetched {item_count} items from {source}")

    def record_llm_request(
        self, model: str, operation: str, tokens_input: int = 0, tokens_output: int = 0
    ):
        """Record LLM request metrics.

        Args:
            model: LLM model name
            operation: Operation type (summarize, generate, etc.)
            tokens_input: Input token count
            tokens_output: Output token count
        """
        llm_requests.labels(model=model, operation=operation).inc()

        if tokens_input > 0:
            llm_tokens.labels(model=model, type="input").inc(tokens_input)

        if tokens_output > 0:
            llm_tokens.labels(model=model, type="output").inc(tokens_output)

    def record_email_send(self, success: bool):
        """Record email send metrics.

        Args:
            success: Whether email was sent successfully
        """
        status = "success" if success else "failed"
        email_sends.labels(status=status).inc()

    def record_subscriber_event(self, event_type: str):
        """Record subscriber event.

        Args:
            event_type: Type of event (open, click, unsubscribe, etc.)
        """
        subscriber_events.labels(event_type=event_type).inc()

    def record_cache_access(self, hit: bool):
        """Record cache access.

        Args:
            hit: Whether it was a cache hit
        """
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def update_system_metrics(self):
        """Update system resource metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_usage.set(cpu_percent)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage.set(memory.percent)

            # Disk usage
            disk = psutil.disk_usage("/")
            disk_usage.set(disk.percent)

        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics.

        Returns:
            Statistics dictionary
        """
        uptime = datetime.utcnow() - self.start_time

        # Calculate average response times
        avg_response_times = {}
        for endpoint, times in self.request_times.items():
            if times:
                avg_response_times[endpoint] = sum(times) / len(times)

        # Calculate cache hit rate
        total_cache_access = self.cache_hits + self.cache_misses
        cache_hit_rate = (
            (self.cache_hits / total_cache_access * 100)
            if total_cache_access > 0
            else 0
        )

        return {
            "uptime_seconds": uptime.total_seconds(),
            "total_requests": sum(len(times) for times in self.request_times.values()),
            "error_count": sum(self.error_counts.values()),
            "avg_response_times": avg_response_times,
            "cache_hit_rate": cache_hit_rate,
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
            },
        }

    def get_prometheus_metrics(self) -> bytes:
        """Get metrics in Prometheus format.

        Returns:
            Prometheus formatted metrics
        """
        # Update system metrics
        self.update_system_metrics()

        # Generate Prometheus format
        return generate_latest()


# Global metrics collector instance
metrics_collector = MetricsCollector()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting request metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Record metrics
        metrics_collector.record_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration=duration,
        )

        # Add timing header
        response.headers["X-Process-Time"] = str(duration)

        return response


def metrics_middleware(app):
    """Create metrics middleware for FastAPI app.

    Args:
        app: FastAPI application

    Returns:
        Configured app with metrics middleware
    """
    app.add_middleware(MetricsMiddleware)
    return app


class PerformanceMonitor:
    """Monitor application performance."""

    def __init__(self, threshold_ms: float = 1000):
        """Initialize performance monitor.

        Args:
            threshold_ms: Threshold in milliseconds for slow requests
        """
        self.threshold_ms = threshold_ms
        self.slow_requests: list = []

    def check_request(
        self, endpoint: str, duration_ms: float, request_id: Optional[str] = None
    ):
        """Check if request is slow.

        Args:
            endpoint: API endpoint
            duration_ms: Request duration in milliseconds
            request_id: Optional request ID
        """
        if duration_ms > self.threshold_ms:
            self.slow_requests.append(
                {
                    "endpoint": endpoint,
                    "duration_ms": duration_ms,
                    "request_id": request_id,
                    "timestamp": datetime.utcnow(),
                }
            )

            # Keep only last 100 slow requests
            if len(self.slow_requests) > 100:
                self.slow_requests = self.slow_requests[-100:]

            logger.warning(
                f"Slow request detected: {endpoint} took {duration_ms:.2f}ms"
            )

    def get_slow_endpoints(self) -> Dict[str, Any]:
        """Get statistics about slow endpoints.

        Returns:
            Slow endpoint statistics
        """
        if not self.slow_requests:
            return {"count": 0, "endpoints": []}

        # Group by endpoint
        endpoint_stats = defaultdict(list)
        for req in self.slow_requests:
            endpoint_stats[req["endpoint"]].append(req["duration_ms"])

        # Calculate stats per endpoint
        results = []
        for endpoint, durations in endpoint_stats.items():
            results.append(
                {
                    "endpoint": endpoint,
                    "count": len(durations),
                    "avg_duration_ms": sum(durations) / len(durations),
                    "max_duration_ms": max(durations),
                }
            )

        # Sort by average duration
        results.sort(key=lambda x: x["avg_duration_ms"], reverse=True)

        return {
            "count": len(self.slow_requests),
            "endpoints": results[:10],  # Top 10 slowest
        }
