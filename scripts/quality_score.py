#!/usr/bin/env python3
"""
Content Quality Scoring Engine

Analyzes generated newsletter content for quality issues:
- Hallucination detection
- Factual accuracy
- Sentiment analysis
- Style consistency
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import Session

from newsauto.core.database import SessionLocal
from newsauto.models.content import ContentItem
from newsauto.models.edition import Edition
from newsauto.quality.hallucination_detector import HallucinationDetector
from newsauto.quality.factual_checker import FactualChecker
from newsauto.quality.sentiment_analyzer import SentimentAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QualityScorer:
    """Main quality scoring orchestrator."""

    def __init__(self, db: Session):
        self.db = db
        self.hallucination_detector = HallucinationDetector()
        self.factual_checker = FactualChecker()
        self.sentiment_analyzer = SentimentAnalyzer()

        # Quality thresholds
        self.min_quality_score = 0.85
        self.hallucination_threshold = 0.20
        self.factual_threshold = 0.70
        self.sentiment_min = -0.30

    async def score_content(self, content_item: ContentItem) -> Dict:
        """
        Score a single content item across all quality dimensions.

        Args:
            content_item: Content to score

        Returns:
            Quality score dict
        """
        try:
            logger.info(f"Scoring content item {content_item.id}: {content_item.title}")

            # Run all checks in parallel
            hallucination_task = self.hallucination_detector.check(
                content_item.summary or content_item.content,
                content_item.content,
            )
            factual_task = self.factual_checker.check(
                content_item.summary or "", content_item.url
            )
            sentiment_task = self.sentiment_analyzer.analyze(
                content_item.summary or content_item.content
            )

            hallucination_result, factual_result, sentiment_result = await asyncio.gather(
                hallucination_task, factual_task, sentiment_task, return_exceptions=True
            )

            # Handle errors
            hallucination_score = (
                hallucination_result if isinstance(hallucination_result, float) else 0.0
            )
            factual_score = factual_result if isinstance(factual_result, float) else 1.0
            sentiment_score = (
                sentiment_result if isinstance(sentiment_result, float) else 0.0
            )

            # Calculate composite quality score (weighted average)
            quality_score = (
                hallucination_score * 0.4  # 40% weight on avoiding hallucinations
                + factual_score * 0.35  # 35% weight on factual accuracy
                + (1.0 - abs(sentiment_score)) * 0.25  # 25% weight on neutral sentiment
            )

            # Determine if needs review
            needs_review = (
                quality_score < self.min_quality_score
                or (1.0 - hallucination_score) > self.hallucination_threshold
                or factual_score < self.factual_threshold
                or sentiment_score < self.sentiment_min
            )

            result = {
                "content_id": content_item.id,
                "quality_score": round(quality_score, 3),
                "hallucination_score": round(hallucination_score, 3),
                "factual_score": round(factual_score, 3),
                "sentiment_score": round(sentiment_score, 3),
                "needs_review": needs_review,
                "flags": self._generate_flags(
                    hallucination_score, factual_score, sentiment_score
                ),
                "scored_at": datetime.utcnow().isoformat(),
            }

            logger.info(
                f"Content {content_item.id} scored: {quality_score:.2f} "
                f"(needs_review={needs_review})"
            )

            return result

        except Exception as e:
            logger.error(f"Error scoring content {content_item.id}: {e}")
            return {
                "content_id": content_item.id,
                "quality_score": 0.0,
                "error": str(e),
                "needs_review": True,
            }

    def _generate_flags(
        self, hallucination_score: float, factual_score: float, sentiment_score: float
    ) -> List[str]:
        """Generate quality warning flags."""
        flags = []

        if (1.0 - hallucination_score) > self.hallucination_threshold:
            flags.append("HIGH_HALLUCINATION_RISK")

        if factual_score < self.factual_threshold:
            flags.append("LOW_FACTUAL_ACCURACY")

        if sentiment_score < self.sentiment_min:
            flags.append("NEGATIVE_SENTIMENT")

        if sentiment_score > 0.80:
            flags.append("OVERLY_POSITIVE")

        return flags

    async def sample_and_score_recent_content(
        self, sample_rate: float = 0.10, days_back: int = 1
    ) -> Dict:
        """
        Sample recent content and score for quality.

        Args:
            sample_rate: Percentage of content to sample (0.0-1.0)
            days_back: How many days back to look

        Returns:
            Scoring results summary
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # Get recent content items
        stmt = (
            select(ContentItem)
            .where(ContentItem.created_at >= cutoff_date)
            .where(ContentItem.summary.isnot(None))
            .order_by(ContentItem.created_at.desc())
        )

        result = self.db.execute(stmt)
        all_content = list(result.scalars())

        if not all_content:
            logger.warning("No recent content found to score")
            return {"total": 0, "sampled": 0, "flagged": 0}

        # Sample content
        import random

        sample_size = max(1, int(len(all_content) * sample_rate))
        sampled_content = random.sample(all_content, min(sample_size, len(all_content)))

        logger.info(
            f"Sampling {len(sampled_content)} of {len(all_content)} items ({sample_rate*100:.0f}%)"
        )

        # Score all sampled content
        tasks = [self.score_content(item) for item in sampled_content]
        results = await asyncio.gather(*tasks)

        # Analyze results
        flagged_items = [r for r in results if r.get("needs_review", False)]
        low_quality = [r for r in results if r.get("quality_score", 0) < 0.75]

        avg_quality = (
            sum(r.get("quality_score", 0) for r in results) / len(results)
            if results
            else 0.0
        )

        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_content": len(all_content),
            "sampled": len(sampled_content),
            "flagged": len(flagged_items),
            "low_quality_count": len(low_quality),
            "average_quality_score": round(avg_quality, 3),
            "flagged_items": [
                {
                    "content_id": r["content_id"],
                    "quality_score": r["quality_score"],
                    "flags": r.get("flags", []),
                }
                for r in flagged_items
            ],
        }

        logger.info(
            f"Quality check complete: {len(flagged_items)}/{len(sampled_content)} flagged, "
            f"avg score: {avg_quality:.3f}"
        )

        return summary


async def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Content Quality Scorer")
    parser.add_argument(
        "--sample-rate",
        type=float,
        default=0.10,
        help="Percentage of content to sample (default: 0.10)",
    )
    parser.add_argument(
        "--days-back",
        type=int,
        default=1,
        help="Days of content to analyze (default: 1)",
    )
    parser.add_argument(
        "--content-id", type=int, help="Score specific content item by ID"
    )
    parser.add_argument(
        "--output",
        choices=["json", "text"],
        default="text",
        help="Output format",
    )

    args = parser.parse_args()

    db = SessionLocal()
    scorer = QualityScorer(db)

    try:
        if args.content_id:
            # Score specific item
            stmt = select(ContentItem).where(ContentItem.id == args.content_id)
            result = db.execute(stmt)
            item = result.scalar_one_or_none()

            if not item:
                logger.error(f"Content item {args.content_id} not found")
                return 1

            score_result = await scorer.score_content(item)

            if args.output == "json":
                import json

                print(json.dumps(score_result, indent=2))
            else:
                print(f"\n📊 Quality Score for Content #{args.content_id}")
                print(f"   Title: {item.title}")
                print(f"   Overall Score: {score_result['quality_score']:.3f}")
                print(f"   Hallucination: {score_result['hallucination_score']:.3f}")
                print(f"   Factual: {score_result['factual_score']:.3f}")
                print(f"   Sentiment: {score_result['sentiment_score']:.3f}")
                print(
                    f"   Needs Review: {'⚠️  YES' if score_result['needs_review'] else '✅ No'}"
                )
                if score_result.get("flags"):
                    print(f"   Flags: {', '.join(score_result['flags'])}")

        else:
            # Sample and score recent content
            summary = await scorer.sample_and_score_recent_content(
                sample_rate=args.sample_rate, days_back=args.days_back
            )

            if args.output == "json":
                import json

                print(json.dumps(summary, indent=2))
            else:
                print("\n📊 Content Quality Report")
                print(f"   Time: {summary['timestamp']}")
                print(f"   Total Content: {summary['total_content']}")
                print(f"   Sampled: {summary['sampled']}")
                print(f"   Average Score: {summary['average_quality_score']:.3f}")
                print(
                    f"   Flagged for Review: {summary['flagged']} ({summary['flagged']/summary['sampled']*100:.1f}%)"
                )
                print(f"   Low Quality: {summary['low_quality_count']}")

                if summary["flagged_items"]:
                    print("\n⚠️  Flagged Items:")
                    for item in summary["flagged_items"]:
                        print(
                            f"     • Content #{item['content_id']}: "
                            f"{item['quality_score']:.2f} - {', '.join(item['flags'])}"
                        )

                # Exit with error code if quality threshold breached
                if (
                    summary["average_quality_score"] < 0.75
                    or summary["flagged"] / summary["sampled"] > 0.15
                ):
                    print(
                        "\n❌ Quality threshold breached! Please review flagged content."
                    )
                    return 1

        return 0

    except Exception as e:
        logger.error(f"Error in quality scoring: {e}", exc_info=True)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
