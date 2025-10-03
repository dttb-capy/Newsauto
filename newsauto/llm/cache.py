"""LLM response caching system."""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from newsauto.core.config import get_settings
from newsauto.core.database import get_db
from newsauto.models.cache import CacheEntry

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMCache:
    """Cache for LLM responses to reduce API calls and improve performance."""

    def __init__(self, cache_dir: Path = None, ttl_days: int = None):
        """Initialize LLM cache.

        Args:
            cache_dir: Directory for file-based cache
            ttl_days: Time-to-live in days
        """
        self.cache_dir = cache_dir or settings.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(days=ttl_days or settings.cache_ttl_days)

    def generate_key(
        self, text: str, operation: str = "summary", model: str = None
    ) -> str:
        """Generate unique cache key for content.

        Args:
            text: Input text
            operation: Type of operation (summary, classify, etc.)
            model: Model name

        Returns:
            Cache key
        """
        content = f"{operation}:{model or 'default'}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, cache_key: str, db: Session = None) -> Optional[Dict[str, Any]]:
        """Retrieve cached response.

        Args:
            cache_key: Cache key
            db: Database session

        Returns:
            Cached response or None
        """
        # Try database cache first
        if db or next(get_db(), None):
            db = db or next(get_db())
            try:
                entry = db.query(CacheEntry).filter_by(cache_key=cache_key).first()

                if entry and not entry.is_expired:
                    entry.increment_hit()
                    db.commit()
                    logger.debug(f"Database cache hit: {cache_key[:8]}...")
                    return json.loads(entry.response) if entry.response else None

            except Exception as e:
                logger.warning(f"Database cache error: {e}")
            finally:
                if not db:
                    db.close()

        # Fall back to file cache
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    cached = json.load(f)

                # Check expiration
                cached_time = datetime.fromisoformat(cached["timestamp"])
                if datetime.utcnow() - cached_time < self.ttl:
                    logger.debug(f"File cache hit: {cache_key[:8]}...")
                    return cached.get("data")

            except Exception as e:
                logger.warning(f"File cache error: {e}")

        return None

    def set(
        self,
        cache_key: str,
        data: Dict[str, Any],
        model: str = None,
        db: Session = None,
    ) -> bool:
        """Store response in cache.

        Args:
            cache_key: Cache key
            data: Data to cache
            model: Model used
            db: Database session

        Returns:
            Success status
        """
        # Store in database if available
        if db or next(get_db(), None):
            db = db or next(get_db())
            try:
                # Check if entry exists
                entry = db.query(CacheEntry).filter_by(cache_key=cache_key).first()

                if entry:
                    # Update existing entry
                    entry.response = json.dumps(data)
                    entry.model = model
                    entry.expires_at = datetime.utcnow() + self.ttl
                    entry.updated_at = datetime.utcnow()
                else:
                    # Create new entry
                    entry = CacheEntry(
                        cache_key=cache_key,
                        response=json.dumps(data),
                        model=model,
                        expires_at=datetime.utcnow() + self.ttl,
                        hit_count=0,
                    )
                    db.add(entry)

                db.commit()
                logger.debug(f"Stored in database cache: {cache_key[:8]}...")

            except Exception as e:
                logger.warning(f"Failed to store in database cache: {e}")
                db.rollback()
            finally:
                if not db:
                    db.close()

        # Also store in file cache as backup
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            cache_data = {
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
                "model": model,
            }
            with open(cache_file, "w") as f:
                json.dump(cache_data, f, indent=2)

            logger.debug(f"Stored in file cache: {cache_key[:8]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to store in file cache: {e}")
            return False

    def clear_expired(self, db: Session = None) -> int:
        """Clear expired cache entries.

        Args:
            db: Database session

        Returns:
            Number of entries cleared
        """
        cleared = 0

        # Clear expired database entries
        if db or next(get_db(), None):
            db = db or next(get_db())
            try:
                expired = (
                    db.query(CacheEntry)
                    .filter(CacheEntry.expires_at < datetime.utcnow())
                    .all()
                )

                for entry in expired:
                    db.delete(entry)
                    cleared += 1

                db.commit()
                logger.info(f"Cleared {cleared} expired database cache entries")

            except Exception as e:
                logger.error(f"Failed to clear database cache: {e}")
                db.rollback()
            finally:
                if not db:
                    db.close()

        # Clear expired file cache
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r") as f:
                    cached = json.load(f)

                cached_time = datetime.fromisoformat(cached["timestamp"])
                if datetime.utcnow() - cached_time > self.ttl:
                    cache_file.unlink()
                    cleared += 1

            except Exception as e:
                logger.warning(f"Error processing cache file {cache_file}: {e}")

        logger.info(f"Cleared {cleared} total expired cache entries")
        return cleared

    def get_stats(self, db: Session = None) -> Dict[str, Any]:
        """Get cache statistics.

        Args:
            db: Database session

        Returns:
            Cache statistics
        """
        stats = {
            "file_cache_size": 0,
            "file_cache_count": 0,
            "db_cache_count": 0,
            "total_hits": 0,
            "avg_hit_rate": 0.0,
        }

        # File cache stats
        cache_files = list(self.cache_dir.glob("*.json"))
        stats["file_cache_count"] = len(cache_files)
        stats["file_cache_size"] = sum(f.stat().st_size for f in cache_files)

        # Database cache stats
        if db or next(get_db(), None):
            db = db or next(get_db())
            try:
                entries = db.query(CacheEntry).all()
                stats["db_cache_count"] = len(entries)

                if entries:
                    stats["total_hits"] = sum(e.hit_count for e in entries)
                    stats["avg_hit_rate"] = stats["total_hits"] / len(entries)

            except Exception as e:
                logger.error(f"Failed to get database cache stats: {e}")
            finally:
                if not db:
                    db.close()

        return stats

    def invalidate(self, cache_key: str, db: Session = None) -> bool:
        """Invalidate specific cache entry.

        Args:
            cache_key: Cache key to invalidate
            db: Database session

        Returns:
            Success status
        """
        success = False

        # Remove from database
        if db or next(get_db(), None):
            db = db or next(get_db())
            try:
                entry = db.query(CacheEntry).filter_by(cache_key=cache_key).first()
                if entry:
                    db.delete(entry)
                    db.commit()
                    success = True

            except Exception as e:
                logger.error(f"Failed to invalidate database cache: {e}")
                db.rollback()
            finally:
                if not db:
                    db.close()

        # Remove from file cache
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                cache_file.unlink()
                success = True
            except Exception as e:
                logger.error(f"Failed to remove cache file: {e}")

        return success
