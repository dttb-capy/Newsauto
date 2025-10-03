"""
Content ratio manager to maintain optimal content mix (65% original, 25% curated, 10% syndicated).
Based on successful newsletter models with 40%+ open rates.
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Types of content in newsletters."""

    ORIGINAL = "original"  # AI-generated or fully processed content
    CURATED = "curated"  # Handpicked external content with commentary
    SYNDICATED = "syndicated"  # Aggregated news items with minimal processing


@dataclass
class ContentItem:
    """Individual content item with metadata."""

    id: str
    title: str
    content: str
    summary: str
    url: Optional[str]
    source: str
    content_type: ContentType
    score: float  # Relevance/quality score
    published_at: datetime
    author: Optional[str] = None
    read_time: Optional[int] = None  # in minutes
    tags: List[str] = None
    metrics: Dict[str, Any] = None
    code_snippets: List[str] = None
    key_takeaways: List[str] = None
    visual_elements: List[Dict] = None  # diagrams, charts, etc.


class ContentRatioManager:
    """Manages content distribution to maintain optimal ratios."""

    def __init__(
        self,
        target_ratios: Dict[str, float] = None,
        min_items: int = 5,
        max_items: int = 15,
    ):
        """
        Initialize content ratio manager.

        Args:
            target_ratios: Target distribution of content types
            min_items: Minimum number of items in newsletter
            max_items: Maximum number of items in newsletter
        """
        self.target_ratios = target_ratios or {
            "original": 0.65,
            "curated": 0.25,
            "syndicated": 0.10,
        }
        self.min_items = min_items
        self.max_items = max_items

        # Validate ratios sum to 1.0
        ratio_sum = sum(self.target_ratios.values())
        if abs(ratio_sum - 1.0) > 0.01:
            raise ValueError(f"Content ratios must sum to 1.0, got {ratio_sum}")

    def calculate_item_counts(self, total_items: int) -> Dict[ContentType, int]:
        """
        Calculate number of items for each content type.

        Args:
            total_items: Total number of items to include

        Returns:
            Dictionary mapping content type to item count
        """
        counts = {}
        remaining = total_items

        # Calculate counts based on ratios
        for content_type, ratio in [
            (ContentType.ORIGINAL, self.target_ratios["original"]),
            (ContentType.CURATED, self.target_ratios["curated"]),
            (ContentType.SYNDICATED, self.target_ratios["syndicated"]),
        ]:
            count = round(total_items * ratio)
            counts[content_type] = count
            remaining -= count

        # Adjust for rounding errors - add to original content
        if remaining != 0:
            counts[ContentType.ORIGINAL] += remaining

        # Ensure at least 1 original item
        if counts[ContentType.ORIGINAL] < 1:
            counts[ContentType.ORIGINAL] = 1
            if counts[ContentType.SYNDICATED] > 0:
                counts[ContentType.SYNDICATED] -= 1

        return counts

    def select_content(
        self,
        available_content: List[ContentItem],
        target_count: Optional[int] = None,
        quality_threshold: float = 0.5,
    ) -> Tuple[List[ContentItem], Dict[str, Any]]:
        """
        Select content items maintaining optimal ratios.

        Args:
            available_content: Pool of available content items
            target_count: Target number of items (auto-determined if None)
            quality_threshold: Minimum quality score for inclusion

        Returns:
            Tuple of (selected items, selection metrics)
        """
        if not available_content:
            return [], {"error": "No content available"}

        # Filter by quality threshold
        qualified_content = [
            item for item in available_content if item.score >= quality_threshold
        ]

        if not qualified_content:
            logger.warning(f"No content meets quality threshold {quality_threshold}")
            qualified_content = available_content[: self.min_items]

        # Group content by type
        content_by_type = {
            ContentType.ORIGINAL: [],
            ContentType.CURATED: [],
            ContentType.SYNDICATED: [],
        }

        for item in qualified_content:
            content_by_type[item.content_type].append(item)

        # Sort each group by score (descending)
        for content_list in content_by_type.values():
            content_list.sort(key=lambda x: x.score, reverse=True)

        # Determine target count
        if target_count is None:
            # Auto-determine based on available content
            total_available = len(qualified_content)
            target_count = min(
                max(self.min_items, total_available // 2), self.max_items
            )

        # Calculate item counts for each type
        target_counts = self.calculate_item_counts(target_count)

        # Select items
        selected_items = []
        actual_counts = {
            ContentType.ORIGINAL: 0,
            ContentType.CURATED: 0,
            ContentType.SYNDICATED: 0,
        }

        for content_type, target in target_counts.items():
            available = content_by_type[content_type]
            selected = available[:target]
            selected_items.extend(selected)
            actual_counts[content_type] = len(selected)

            # If we don't have enough of this type, try to compensate
            if len(selected) < target:
                deficit = target - len(selected)
                logger.info(f"Deficit of {deficit} items for {content_type.value}")

                # Try to fill from other categories (prefer original content)
                for fallback_type in [
                    ContentType.ORIGINAL,
                    ContentType.CURATED,
                    ContentType.SYNDICATED,
                ]:
                    if fallback_type != content_type:
                        remaining = content_by_type[fallback_type][
                            actual_counts[fallback_type] :
                        ]
                        fill = remaining[:deficit]
                        selected_items.extend(fill)
                        actual_counts[fallback_type] += len(fill)
                        deficit -= len(fill)
                        if deficit <= 0:
                            break

        # Sort final selection by score for optimal presentation
        selected_items.sort(key=lambda x: x.score, reverse=True)

        # Calculate metrics
        metrics = self._calculate_selection_metrics(
            selected_items, actual_counts, target_counts, len(qualified_content)
        )

        return selected_items, metrics

    def optimize_content_mix(
        self,
        content_items: List[ContentItem],
        engagement_data: Optional[Dict[str, float]] = None,
    ) -> List[ContentItem]:
        """
        Optimize content mix based on engagement data.

        Args:
            content_items: List of content items to optimize
            engagement_data: Historical engagement rates by content type

        Returns:
            Optimized list of content items
        """
        if engagement_data:
            # Adjust ratios based on engagement
            adjusted_ratios = self._adjust_ratios_by_engagement(engagement_data)
            self.target_ratios = adjusted_ratios

        selected, metrics = self.select_content(content_items)

        # Apply diversity optimization
        selected = self._ensure_topic_diversity(selected)

        # Apply temporal distribution
        selected = self._apply_temporal_distribution(selected)

        return selected

    def _calculate_selection_metrics(
        self,
        selected_items: List[ContentItem],
        actual_counts: Dict[ContentType, int],
        target_counts: Dict[ContentType, int],
        total_qualified: int,
    ) -> Dict[str, Any]:
        """Calculate metrics about the content selection."""
        total_selected = len(selected_items)

        if total_selected == 0:
            return {"total_selected": 0, "ratios": {}, "deviation": 1.0, "quality": 0}

        # Calculate actual ratios
        actual_ratios = {
            content_type.value: count / total_selected
            for content_type, count in actual_counts.items()
        }

        # Calculate deviation from target
        deviation = sum(
            abs(actual_ratios.get(key, 0) - target)
            for key, target in self.target_ratios.items()
        )

        # Calculate average quality score
        avg_score = sum(item.score for item in selected_items) / total_selected

        # Calculate read time
        total_read_time = (
            sum(item.read_time for item in selected_items if item.read_time)
            or total_selected * 3
        )  # Default 3 min per item

        return {
            "total_selected": total_selected,
            "total_qualified": total_qualified,
            "target_counts": {k.value: v for k, v in target_counts.items()},
            "actual_counts": {k.value: v for k, v in actual_counts.items()},
            "target_ratios": self.target_ratios,
            "actual_ratios": actual_ratios,
            "deviation_from_target": deviation,
            "average_quality_score": avg_score,
            "total_read_time": total_read_time,
            "has_code_examples": any(item.code_snippets for item in selected_items),
            "has_visuals": any(item.visual_elements for item in selected_items),
        }

    def _adjust_ratios_by_engagement(
        self, engagement_data: Dict[str, float]
    ) -> Dict[str, float]:
        """Adjust content ratios based on engagement data."""
        # Calculate engagement-weighted ratios
        total_engagement = sum(engagement_data.values())
        if total_engagement == 0:
            return self.target_ratios

        adjusted = {}
        for content_type in ["original", "curated", "syndicated"]:
            if content_type in engagement_data:
                # Weight current ratio by engagement performance
                engagement_weight = engagement_data[content_type] / total_engagement
                current_ratio = self.target_ratios[content_type]

                # Blend current ratio with engagement weight (70% current, 30% engagement)
                adjusted[content_type] = (0.7 * current_ratio) + (
                    0.3 * engagement_weight
                )
            else:
                adjusted[content_type] = self.target_ratios[content_type]

        # Normalize to sum to 1.0
        total = sum(adjusted.values())
        return {k: v / total for k, v in adjusted.items()}

    def _ensure_topic_diversity(
        self, content_items: List[ContentItem], min_unique_tags: int = 3
    ) -> List[ContentItem]:
        """Ensure topic diversity in content selection."""
        if len(content_items) <= min_unique_tags:
            return content_items

        # Track unique tags
        seen_tags = set()
        diverse_items = []
        remaining_items = []

        for item in content_items:
            if item.tags:
                item_tags = set(item.tags)
                if (
                    not item_tags.issubset(seen_tags)
                    or len(seen_tags) < min_unique_tags
                ):
                    diverse_items.append(item)
                    seen_tags.update(item_tags)
                else:
                    remaining_items.append(item)
            else:
                remaining_items.append(item)

        # Add remaining high-score items
        diverse_items.extend(
            remaining_items[: max(0, len(content_items) - len(diverse_items))]
        )

        return diverse_items

    def _apply_temporal_distribution(
        self, content_items: List[ContentItem]
    ) -> List[ContentItem]:
        """Apply temporal distribution to mix fresh and evergreen content."""
        if len(content_items) <= 3:
            return content_items

        now = datetime.now()

        # Categorize by age
        very_fresh = []  # < 24 hours
        fresh = []  # 1-3 days
        recent = []  # 3-7 days
        evergreen = []  # > 7 days

        for item in content_items:
            if item.published_at:
                age = now - item.published_at
                if age < timedelta(days=1):
                    very_fresh.append(item)
                elif age < timedelta(days=3):
                    fresh.append(item)
                elif age < timedelta(days=7):
                    recent.append(item)
                else:
                    evergreen.append(item)
            else:
                recent.append(item)

        # Optimal mix: 40% very fresh, 30% fresh, 20% recent, 10% evergreen
        result = []
        total = len(content_items)

        targets = [
            (very_fresh, int(total * 0.4)),
            (fresh, int(total * 0.3)),
            (recent, int(total * 0.2)),
            (evergreen, int(total * 0.1)),
        ]

        for category, target_count in targets:
            result.extend(category[:target_count])

        # Fill remaining slots with highest scoring items
        remaining = total - len(result)
        all_remaining = very_fresh + fresh + recent + evergreen
        all_remaining = [item for item in all_remaining if item not in result]
        all_remaining.sort(key=lambda x: x.score, reverse=True)
        result.extend(all_remaining[:remaining])

        return result

    def generate_content_hash(self, content: str) -> str:
        """Generate a hash for content deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def deduplicate_content(
        self, content_items: List[ContentItem], similarity_threshold: float = 0.8
    ) -> List[ContentItem]:
        """Remove duplicate or highly similar content items."""
        if len(content_items) <= 1:
            return content_items

        seen_hashes = set()
        unique_items = []

        for item in content_items:
            # Generate content hash
            content_hash = self.generate_content_hash(item.title + item.summary)

            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_items.append(item)
            else:
                logger.info(f"Duplicate content detected: {item.title}")

        return unique_items
