"""
Sentiment Analysis for content quality.

Detects sentiment bias in generated content to ensure neutral, professional tone.
"""

import logging
import re
from typing import Dict

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analyzes sentiment of generated content."""

    def __init__(self):
        # Positive sentiment words/phrases
        self.positive_words = {
            "amazing",
            "excellent",
            "fantastic",
            "wonderful",
            "great",
            "outstanding",
            "remarkable",
            "brilliant",
            "perfect",
            "incredible",
            "extraordinary",
            "exceptional",
            "superb",
            "magnificent",
            "spectacular",
            "phenomenal",
            "revolutionary",
            "groundbreaking",
            "game-changing",
        }

        # Negative sentiment words/phrases
        self.negative_words = {
            "terrible",
            "awful",
            "horrible",
            "disappointing",
            "disastrous",
            "catastrophic",
            "failure",
            "failed",
            "worst",
            "problem",
            "issue",
            "concern",
            "controversy",
            "scandal",
            "crisis",
            "nightmare",
            "disaster",
            "devastating",
            "alarming",
            "shocking",
        }

        # Intensifiers (multiply sentiment)
        self.intensifiers = {
            "very",
            "extremely",
            "highly",
            "incredibly",
            "absolutely",
            "totally",
            "completely",
        }

    async def analyze(self, text: str) -> float:
        """
        Analyze sentiment of text.

        Args:
            text: Text to analyze

        Returns:
            Score from -1.0 (very negative) to +1.0 (very positive)
            Target range for newsletter content: -0.2 to +0.2 (neutral)
        """
        try:
            if not text:
                return 0.0  # Neutral

            text_lower = text.lower()

            # Count positive and negative words
            positive_count = self._count_sentiment_words(text_lower, self.positive_words)
            negative_count = self._count_sentiment_words(text_lower, self.negative_words)

            # Total sentiment-bearing words
            total_sentiment = positive_count + negative_count

            if total_sentiment == 0:
                return 0.0  # Neutral if no sentiment words

            # Calculate net sentiment
            net_sentiment = (positive_count - negative_count) / total_sentiment

            # Normalize to -1.0 to +1.0 range
            # Apply sigmoid-like function to smooth extremes
            sentiment_score = net_sentiment * (1 - abs(net_sentiment) * 0.3)

            logger.debug(
                f"Sentiment analysis: pos={positive_count}, neg={negative_count}, "
                f"score={sentiment_score:.3f}"
            )

            return round(sentiment_score, 3)

        except Exception as e:
            logger.error(f"Error in sentiment analysis: {e}")
            return 0.0  # Neutral on error

    def _count_sentiment_words(self, text: str, word_set: set) -> float:
        """Count sentiment words with intensity weighting."""
        count = 0.0
        words = text.split()

        for i, word in enumerate(words):
            # Clean word
            cleaned = re.sub(r"[^\w]", "", word)

            if cleaned in word_set:
                # Check for intensifier in previous word
                intensity = 1.0
                if i > 0:
                    prev_word = re.sub(r"[^\w]", "", words[i - 1])
                    if prev_word in self.intensifiers:
                        intensity = 1.5

                count += intensity

        return count

    def get_detailed_analysis(self, text: str) -> Dict:
        """
        Get detailed sentiment analysis.

        Returns:
            Dict with sentiment breakdown
        """
        text_lower = text.lower()

        positive_count = self._count_sentiment_words(text_lower, self.positive_words)
        negative_count = self._count_sentiment_words(text_lower, self.negative_words)

        total_sentiment = positive_count + negative_count
        net_sentiment = (
            (positive_count - negative_count) / total_sentiment if total_sentiment > 0 else 0
        )
        sentiment_score = net_sentiment * (1 - abs(net_sentiment) * 0.3)

        # Find specific sentiment words used
        words = text_lower.split()
        positive_words_found = [
            w for w in words if re.sub(r"[^\w]", "", w) in self.positive_words
        ]
        negative_words_found = [
            w for w in words if re.sub(r"[^\w]", "", w) in self.negative_words
        ]

        return {
            "sentiment_score": round(sentiment_score, 3),
            "positive_count": int(positive_count),
            "negative_count": int(negative_count),
            "positive_words": positive_words_found[:10],  # Limit to 10
            "negative_words": negative_words_found[:10],
            "classification": self._classify_sentiment(sentiment_score),
            "is_neutral": abs(sentiment_score) < 0.2,
            "bias_warning": abs(sentiment_score) > 0.5,
        }

    def _classify_sentiment(self, score: float) -> str:
        """Classify sentiment from score."""
        if score >= 0.5:
            return "very_positive"
        elif score >= 0.2:
            return "positive"
        elif score >= -0.2:
            return "neutral"
        elif score >= -0.5:
            return "negative"
        else:
            return "very_negative"

    def check_professional_tone(self, text: str) -> Dict:
        """
        Check if text maintains professional, neutral tone.

        Returns:
            Dict with tone analysis
        """
        sentiment_score = asyncio.run(self.analyze(text))

        # Professional tone should be neutral (-0.3 to +0.3)
        is_professional = abs(sentiment_score) < 0.3

        # Check for unprofessional patterns
        unprofessional_patterns = [
            r"!\s*!+",  # Multiple exclamation marks
            r"\?!",  # Interrobang
            r"[A-Z]{3,}",  # SHOUTING
            r"!!+",  # Excessive excitement
            r"\.\.\.+",  # Trailing ellipsis
        ]

        issues = []
        for pattern in unprofessional_patterns:
            if re.search(pattern, text):
                issues.append(pattern)

        return {
            "is_professional": is_professional and len(issues) == 0,
            "sentiment_score": sentiment_score,
            "tone_issues": issues,
            "recommendation": self._get_tone_recommendation(sentiment_score, issues),
        }

    def _get_tone_recommendation(self, sentiment_score: float, issues: list) -> str:
        """Get recommendation for improving tone."""
        if abs(sentiment_score) > 0.5:
            if sentiment_score > 0:
                return "Tone is overly positive. Use more neutral language."
            else:
                return "Tone is overly negative. Balance with factual observations."
        elif issues:
            return "Avoid excessive punctuation and capitalization for professional tone."
        else:
            return "Tone is appropriate and professional."


# Import asyncio for the check_professional_tone method
import asyncio
