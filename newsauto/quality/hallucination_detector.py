"""
Hallucination Detection for LLM-generated content.

Detects when LLM summaries contain information not present in source material.
"""

import logging
import re
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class HallucinationDetector:
    """Detects hallucinations in LLM-generated summaries."""

    def __init__(self):
        # Patterns that indicate potential hallucination
        self.hallucination_indicators = [
            r"according to (?:the|a) (?:report|study|research)",
            r"studies show",
            r"experts say",
            r"scientists discovered",
            r"\d{1,3}% of",
            r"(?:increased|decreased) by \d+%",
            r"in \d{4}",  # Specific years
            r"\$[\d,]+ (?:million|billion)",
            r"CEO (?:announced|stated|said)",
        ]

        # Compile patterns
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.hallucination_indicators]

    async def check(self, summary: str, source_content: str) -> float:
        """
        Check summary for hallucinations against source content.

        Args:
            summary: LLM-generated summary
            source_content: Original source content

        Returns:
            Score from 0.0 (high hallucination) to 1.0 (no hallucination)
        """
        try:
            if not summary or not source_content:
                return 0.5  # Neutral score if no content

            # Convert to lowercase for comparison
            summary_lower = summary.lower()
            source_lower = source_content.lower()

            # Score components
            scores = []

            # 1. Entity overlap check
            entity_score = self._check_entity_overlap(summary_lower, source_lower)
            scores.append(entity_score * 0.4)  # 40% weight

            # 2. Fact pattern check
            fact_score = self._check_fact_patterns(summary_lower, source_lower)
            scores.append(fact_score * 0.35)  # 35% weight

            # 3. Numeric consistency check
            numeric_score = self._check_numeric_consistency(summary_lower, source_lower)
            scores.append(numeric_score * 0.25)  # 25% weight

            # Aggregate score
            final_score = sum(scores)

            logger.debug(
                f"Hallucination check: entity={entity_score:.2f}, "
                f"fact={fact_score:.2f}, numeric={numeric_score:.2f}, "
                f"final={final_score:.2f}"
            )

            return round(final_score, 3)

        except Exception as e:
            logger.error(f"Error in hallucination detection: {e}")
            return 0.5  # Neutral score on error

    def _check_entity_overlap(self, summary: str, source: str) -> float:
        """Check if summary entities appear in source."""
        # Extract potential entities (capitalized words/phrases)
        summary_entities = set(self._extract_entities(summary))
        source_entities = set(self._extract_entities(source))

        if not summary_entities:
            return 1.0  # No entities to check

        # Calculate overlap
        overlap = summary_entities.intersection(source_entities)
        overlap_ratio = len(overlap) / len(summary_entities)

        return overlap_ratio

    def _extract_entities(self, text: str) -> List[str]:
        """Extract entity-like patterns from text."""
        # Simple entity extraction (capitalized words of 3+ chars)
        entities = []

        # Find capitalized words
        words = text.split()
        for word in words:
            # Remove punctuation
            cleaned = re.sub(r"[^\w\s]", "", word)
            if len(cleaned) >= 3 and cleaned[0].isupper():
                entities.append(cleaned.lower())

        # Also extract multi-word entities (2-3 consecutive capitalized words)
        pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b"
        multi_word = re.findall(pattern, text)
        entities.extend([e.lower() for e in multi_word])

        return entities

    def _check_fact_patterns(self, summary: str, source: str) -> float:
        """Check if factual claims in summary are supported by source."""
        hallucination_count = 0
        total_patterns = 0

        for pattern in self.patterns:
            # Find matches in summary
            summary_matches = pattern.findall(summary)
            total_patterns += len(summary_matches)

            for match in summary_matches:
                # Check if similar pattern exists in source
                # Allow for some variation
                match_escaped = re.escape(match[:20])  # First 20 chars
                if not re.search(match_escaped, source, re.IGNORECASE):
                    hallucination_count += 1

        if total_patterns == 0:
            return 1.0  # No factual patterns to check

        # Score based on non-hallucinated patterns
        score = 1.0 - (hallucination_count / total_patterns)
        return max(0.0, min(1.0, score))

    def _check_numeric_consistency(self, summary: str, source: str) -> float:
        """Check if numbers in summary match source."""
        # Extract numbers from both texts
        summary_numbers = self._extract_numbers(summary)
        source_numbers = self._extract_numbers(source)

        if not summary_numbers:
            return 1.0  # No numbers to check

        # Check how many summary numbers appear in source
        matching_count = sum(1 for num in summary_numbers if num in source_numbers)

        consistency_ratio = matching_count / len(summary_numbers)
        return consistency_ratio

    def _extract_numbers(self, text: str) -> Set[str]:
        """Extract numbers from text."""
        # Match integers, decimals, percentages, currency
        patterns = [
            r"\d+\.?\d*%",  # Percentages: 45%, 3.5%
            r"\$\d+(?:,\d{3})*(?:\.\d{2})?",  # Currency: $1,000, $5.50
            r"\d{4}",  # Years: 2024
            r"\d+\.?\d*",  # General numbers: 42, 3.14
        ]

        numbers = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            numbers.update(matches)

        return numbers

    def get_detailed_analysis(self, summary: str, source_content: str) -> Dict:
        """
        Get detailed hallucination analysis.

        Returns:
            Dict with detailed scores and flagged content
        """
        summary_lower = summary.lower()
        source_lower = source_content.lower()

        entity_score = self._check_entity_overlap(summary_lower, source_lower)
        fact_score = self._check_fact_patterns(summary_lower, source_lower)
        numeric_score = self._check_numeric_consistency(summary_lower, source_lower)

        # Find specific hallucinated content
        flagged_patterns = []
        for pattern in self.patterns:
            matches = pattern.findall(summary)
            for match in matches:
                if match[:20] not in source_lower:
                    flagged_patterns.append(match)

        return {
            "overall_score": round(entity_score * 0.4 + fact_score * 0.35 + numeric_score * 0.25, 3),
            "entity_score": round(entity_score, 3),
            "fact_score": round(fact_score, 3),
            "numeric_score": round(numeric_score, 3),
            "flagged_patterns": flagged_patterns[:5],  # Limit to 5
            "risk_level": self._classify_risk(entity_score, fact_score, numeric_score),
        }

    def _classify_risk(self, entity_score: float, fact_score: float, numeric_score: float) -> str:
        """Classify hallucination risk level."""
        avg_score = (entity_score + fact_score + numeric_score) / 3

        if avg_score >= 0.85:
            return "low"
        elif avg_score >= 0.70:
            return "medium"
        else:
            return "high"
