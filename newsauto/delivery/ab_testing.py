"""
A/B testing system for newsletter optimization.
Tests subject lines, content variations, and send times to maximize engagement.
"""

import hashlib
import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class TestType(Enum):
    """Types of A/B tests."""

    SUBJECT_LINE = "subject_line"
    CONTENT_VARIANT = "content_variant"
    SEND_TIME = "send_time"
    FROM_NAME = "from_name"
    CTA_BUTTON = "cta_button"
    TEMPLATE = "template"
    FREQUENCY = "frequency"


class TestStatus(Enum):
    """Status of an A/B test."""

    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class WinnerCriteria(Enum):
    """Criteria for determining test winner."""

    OPEN_RATE = "open_rate"
    CLICK_RATE = "click_rate"
    CONVERSION_RATE = "conversion_rate"
    REVENUE = "revenue"
    ENGAGEMENT_SCORE = "engagement_score"


@dataclass
class TestVariant:
    """Individual variant in an A/B test."""

    variant_id: str
    name: str
    content: Dict[str, Any]

    # Assignment
    subscriber_count: int = 0
    subscriber_ids: List[int] = field(default_factory=list)

    # Metrics
    sends: int = 0
    opens: int = 0
    clicks: int = 0
    conversions: int = 0
    unsubscribes: int = 0
    revenue: float = 0.0

    # Calculated rates
    open_rate: float = 0.0
    click_rate: float = 0.0
    conversion_rate: float = 0.0
    ctr: float = 0.0  # Click-through rate (clicks/opens)

    # Statistical
    confidence_level: float = 0.0
    is_winner: bool = False

    def calculate_rates(self):
        """Calculate engagement rates."""
        if self.sends > 0:
            self.open_rate = self.opens / self.sends
            self.click_rate = self.clicks / self.sends
            self.conversion_rate = self.conversions / self.sends
        if self.opens > 0:
            self.ctr = self.clicks / self.opens


@dataclass
class ABTest:
    """Complete A/B test configuration and results."""

    test_id: str
    name: str
    test_type: TestType
    status: TestStatus

    # Test configuration
    newsletter_id: int
    segment_ids: List[str] = field(default_factory=list)
    test_size: float = 0.2  # Percentage of audience for test
    min_sample_size: int = 100  # Per variant
    max_runtime_hours: int = 48
    confidence_threshold: float = 0.95
    winner_criteria: WinnerCriteria = WinnerCriteria.OPEN_RATE

    # Variants
    control: TestVariant = None
    variants: List[TestVariant] = field(default_factory=list)

    # Timeline
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    winner: Optional[TestVariant] = None
    statistical_significance: float = 0.0
    improvement_percentage: float = 0.0

    # Metadata
    tags: List[str] = field(default_factory=list)
    notes: Optional[str] = None


class ABTestingManager:
    """Manages A/B testing for newsletter optimization."""

    def __init__(self):
        """Initialize A/B testing manager."""
        self.active_tests: Dict[str, ABTest] = {}
        self.test_history: List[ABTest] = []
        self.subject_line_patterns = self._load_subject_patterns()

    def _load_subject_patterns(self) -> Dict[str, List[str]]:
        """Load successful subject line patterns."""
        return {
            # Executive/C-Suite patterns (highest engagement)
            "executive_authority": [
                "Board Brief: {topic} Strategic Impact",
                "CEO Playbook: {topic} in {timeframe}",
                "{company} Case Study: {result} ROI on {topic}",
                "Executive Summary: {topic} Market Disruption",
            ],
            "strategic_urgency": [
                "Action Required: {topic} Decision by {deadline}",
                "Q{quarter} Priority: {topic} Implementation",
                "Competitive Alert: {competitor}'s {topic} Strategy",
                "Market Shift: {topic} Implications for {year}",
            ],
            "financial_impact": [
                "{topic}: ${amount}M Revenue Opportunity",
                "Cut {percentage}% Costs with {topic} Strategy",
                "Portfolio Companies: {topic} Best Practices",
                "IRR Impact: How {topic} Drives {percentage}% Returns",
            ],
            "peer_insights": [
                "How {company} CEO Navigated {topic}",
                "Fortune 500 {topic} Strategies Revealed",
                "What {number} CTOs Say About {topic}",
                "Exclusive: {company}'s {topic} Transformation",
            ],
            "veteran_leadership": [
                "Mission-Critical: {topic} Strategic Brief",
                "After Action Review: {topic} Lessons",
                "Force Multiplier: {topic} for Scale",
                "Operational Excellence: {topic} Framework",
            ],
            "innovation_edge": [
                "First Mover: {topic} Market Analysis",
                "Disruption Alert: {topic} Changes Everything",
                "Next-Gen {topic}: {year} Roadmap",
                "{topic} 2.0: Beyond Current Limitations",
            ],
            # Technical leadership patterns
            "technical_leadership": [
                "Principal Engineer: {topic} at Scale",
                "Architecture Decision: {topic} Trade-offs",
                "Tech Debt: {topic} Remediation Strategy",
                "Engineering Excellence: {topic} Standards",
            ],
            # Traditional patterns (kept for testing)
            "urgency": [
                "⚡ {topic} - Act Now",
                "Last Chance: {topic}",
                "Breaking: {topic}",
                "🚨 Critical Update: {topic}",
            ],
            "curiosity": [
                "The {topic} Nobody's Talking About",
                "{number} {topic} Mistakes You're Making",
                "Why {company} Changed Their {topic} Strategy",
                "The Hidden Cost of {topic}",
            ],
            "benefit": [
                "Save {percentage}% on {topic}",
                "Boost Your {metric} by {number}x",
                "{number} Ways to Improve {topic}",
                "Master {topic} in {timeframe}",
            ],
            "social_proof": [
                "How {company} Achieved {result}",
                "{number}+ Engineers Love This {topic}",
                "What {authority} Says About {topic}",
                "Join {number} Developers Using {topic}",
            ],
        }

    def create_test(
        self,
        name: str,
        test_type: TestType,
        newsletter_id: int,
        variants_config: List[Dict[str, Any]],
        **kwargs,
    ) -> ABTest:
        """
        Create a new A/B test.

        Args:
            name: Test name
            test_type: Type of test
            newsletter_id: Newsletter to test
            variants_config: Configuration for each variant
            **kwargs: Additional test parameters

        Returns:
            Created ABTest instance
        """
        test_id = self._generate_test_id(name)

        # Create test instance
        test = ABTest(
            test_id=test_id,
            name=name,
            test_type=test_type,
            status=TestStatus.DRAFT,
            newsletter_id=newsletter_id,
            created_at=datetime.now(),
            **kwargs,
        )

        # Create variants
        for i, config in enumerate(variants_config):
            variant = TestVariant(
                variant_id=f"{test_id}_v{i}",
                name=config.get("name", f"Variant {chr(65+i)}"),
                content=config,
            )

            if i == 0:
                test.control = variant
            else:
                test.variants.append(variant)

        self.active_tests[test_id] = test
        return test

    def create_subject_line_test(
        self, newsletter_id: int, topic: str, patterns: Optional[List[str]] = None
    ) -> ABTest:
        """
        Create a subject line A/B test with smart variations.

        Args:
            newsletter_id: Newsletter ID
            topic: Main topic of the newsletter
            patterns: Optional specific patterns to test

        Returns:
            Created subject line test
        """
        if patterns is None:
            # Select diverse patterns
            patterns = [
                random.choice(self.subject_line_patterns["urgency"]),
                random.choice(self.subject_line_patterns["curiosity"]),
                random.choice(self.subject_line_patterns["benefit"]),
                random.choice(self.subject_line_patterns["technical"]),
            ]

        # Generate variants
        variants_config = []
        for i, pattern in enumerate(patterns):
            subject = self._generate_subject_line(pattern, topic)
            variants_config.append(
                {
                    "name": f"Pattern {chr(65+i)}",
                    "subject_line": subject,
                    "pattern_type": self._identify_pattern_type(pattern),
                }
            )

        return self.create_test(
            name=f"Subject Line Test - {topic}",
            test_type=TestType.SUBJECT_LINE,
            newsletter_id=newsletter_id,
            variants_config=variants_config,
            winner_criteria=WinnerCriteria.OPEN_RATE,
            test_size=0.2,
            min_sample_size=100,
        )

    def _generate_subject_line(self, pattern: str, topic: str) -> str:
        """Generate subject line from pattern."""
        replacements = {
            "{topic}": topic,
            "{number}": str(random.choice([3, 5, 7, 10])),
            "{percentage}": str(random.choice([20, 30, 40, 50, 60])),
            "{company}": random.choice(
                ["Stripe", "Netflix", "Palantir", "Anduril", "OpenAI", "SpaceX"]
            ),
            "{competitor}": random.choice(["Amazon", "Microsoft", "Google", "Meta"]),
            "{metric}": random.choice(
                ["Revenue", "EBITDA", "ARR", "NRR", "Efficiency"]
            ),
            "{timeframe}": random.choice(
                ["Q1 2025", "Next 90 Days", "FY2025", "This Quarter"]
            ),
            "{authority}": random.choice(
                ["McKinsey", "Gartner", "Fortune 500 CEOs", "Board Advisors"]
            ),
            "{category}": random.choice(
                [
                    "Strategic Brief",
                    "Executive Summary",
                    "Board Report",
                    "Market Analysis",
                ]
            ),
            "{version}": f"{random.randint(2,5)}.0",
            "{result}": random.choice(
                ["3x ROI", "$10M Savings", "50% Growth", "Market Leadership"]
            ),
            "{amount}": str(random.choice([10, 25, 50, 100, 250])),
            "{year}": "2025",
            "{quarter}": random.choice(["1", "2", "3", "4"]),
            "{deadline}": random.choice(
                ["EOQ", "March 31", "Board Meeting", "Earnings Call"]
            ),
            "{role}": random.choice(["CTO", "VP Engineering", "CISO", "CFO"]),
        }

        for key, value in replacements.items():
            pattern = pattern.replace(key, value)

        return pattern

    def _identify_pattern_type(self, pattern: str) -> str:
        """Identify the type of subject line pattern."""
        for pattern_type, patterns in self.subject_line_patterns.items():
            if pattern in patterns:
                return pattern_type
        return "custom"

    def assign_subscribers(
        self, test: ABTest, subscriber_ids: List[int], method: str = "random"
    ) -> Dict[str, List[int]]:
        """
        Assign subscribers to test variants.

        Args:
            test: ABTest instance
            subscriber_ids: List of subscriber IDs
            method: Assignment method (random, hash, sequential)

        Returns:
            Dictionary mapping variant IDs to subscriber lists
        """
        # Calculate test audience size
        test_audience_size = int(len(subscriber_ids) * test.test_size)
        test_audience = random.sample(subscriber_ids, test_audience_size)

        # Remaining subscribers get the winner after test completes
        holdout_audience = [s for s in subscriber_ids if s not in test_audience]

        # Divide test audience among variants
        all_variants = [test.control] + test.variants
        variant_size = test_audience_size // len(all_variants)

        assignments = {}

        if method == "random":
            random.shuffle(test_audience)
            for i, variant in enumerate(all_variants):
                start_idx = i * variant_size
                end_idx = (
                    start_idx + variant_size
                    if i < len(all_variants) - 1
                    else len(test_audience)
                )

                variant.subscriber_ids = test_audience[start_idx:end_idx]
                variant.subscriber_count = len(variant.subscriber_ids)
                assignments[variant.variant_id] = variant.subscriber_ids

        elif method == "hash":
            # Deterministic assignment based on subscriber ID
            for subscriber_id in test_audience:
                hash_val = int(hashlib.md5(str(subscriber_id).encode()).hexdigest(), 16)
                variant_idx = hash_val % len(all_variants)
                variant = all_variants[variant_idx]
                variant.subscriber_ids.append(subscriber_id)
                variant.subscriber_count += 1

            for variant in all_variants:
                assignments[variant.variant_id] = variant.subscriber_ids

        # Store holdout audience for later
        test.holdout_audience = holdout_audience

        return assignments

    def start_test(self, test_id: str) -> bool:
        """Start an A/B test."""
        test = self.active_tests.get(test_id)
        if not test:
            return False

        if test.status != TestStatus.DRAFT:
            logger.warning(f"Cannot start test {test_id} - status is {test.status}")
            return False

        # Validate minimum sample sizes
        all_variants = [test.control] + test.variants
        for variant in all_variants:
            if variant.subscriber_count < test.min_sample_size:
                logger.warning(f"Variant {variant.name} has insufficient subscribers")
                return False

        test.status = TestStatus.RUNNING
        test.started_at = datetime.now()

        logger.info(f"Started A/B test {test_id}")
        return True

    def record_event(
        self,
        test_id: str,
        variant_id: str,
        event_type: str,
        subscriber_id: int,
        value: Optional[float] = None,
    ):
        """
        Record an event for a test variant.

        Args:
            test_id: Test ID
            variant_id: Variant ID
            event_type: Type of event (send, open, click, etc.)
            subscriber_id: Subscriber who triggered event
            value: Optional value (e.g., revenue)
        """
        test = self.active_tests.get(test_id)
        if not test or test.status != TestStatus.RUNNING:
            return

        # Find variant
        variant = None
        if test.control.variant_id == variant_id:
            variant = test.control
        else:
            variant = next(
                (v for v in test.variants if v.variant_id == variant_id), None
            )

        if not variant:
            return

        # Update metrics
        if event_type == "send":
            variant.sends += 1
        elif event_type == "open":
            variant.opens += 1
        elif event_type == "click":
            variant.clicks += 1
        elif event_type == "conversion":
            variant.conversions += 1
            if value:
                variant.revenue += value
        elif event_type == "unsubscribe":
            variant.unsubscribes += 1

        # Recalculate rates
        variant.calculate_rates()

        # Check if test should complete
        self._check_test_completion(test)

    def _check_test_completion(self, test: ABTest):
        """Check if test should be completed."""
        # Check runtime limit
        if test.started_at:
            runtime = datetime.now() - test.started_at
            if runtime.total_seconds() > test.max_runtime_hours * 3600:
                self.complete_test(test.test_id)
                return

        # Check sample size and statistical significance
        all_variants = [test.control] + test.variants

        # All variants need minimum sends
        if all(v.sends >= test.min_sample_size for v in all_variants):
            # Calculate statistical significance
            significance = self.calculate_statistical_significance(test)
            if significance >= test.confidence_threshold:
                self.complete_test(test.test_id)

    def calculate_statistical_significance(self, test: ABTest) -> float:
        """
        Calculate statistical significance of test results.

        Uses chi-squared test for proportions.
        """
        all_variants = [test.control] + test.variants

        # Get metric based on winner criteria
        if test.winner_criteria == WinnerCriteria.OPEN_RATE:
            successes = [v.opens for v in all_variants]
            trials = [v.sends for v in all_variants]
        elif test.winner_criteria == WinnerCriteria.CLICK_RATE:
            successes = [v.clicks for v in all_variants]
            trials = [v.sends for v in all_variants]
        else:
            successes = [v.conversions for v in all_variants]
            trials = [v.sends for v in all_variants]

        # Perform chi-squared test
        if len(all_variants) == 2:
            # Two-sample proportion test
            p1 = successes[0] / trials[0] if trials[0] > 0 else 0
            p2 = successes[1] / trials[1] if trials[1] > 0 else 0

            pooled_p = (successes[0] + successes[1]) / (trials[0] + trials[1])
            se = math.sqrt(pooled_p * (1 - pooled_p) * (1 / trials[0] + 1 / trials[1]))

            if se > 0:
                z = abs(p1 - p2) / se
                p_value = 2 * (1 - stats.norm.cdf(z))
                significance = 1 - p_value
            else:
                significance = 0
        else:
            # Multi-variant chi-squared test
            observed = np.array(successes)
            expected_rate = sum(successes) / sum(trials)
            expected = np.array([expected_rate * t for t in trials])

            if all(e > 0 for e in expected):
                chi_squared = sum((o - e) ** 2 / e for o, e in zip(observed, expected))
                df = len(all_variants) - 1
                p_value = 1 - stats.chi2.cdf(chi_squared, df)
                significance = 1 - p_value
            else:
                significance = 0

        test.statistical_significance = significance
        return significance

    def complete_test(self, test_id: str) -> Optional[TestVariant]:
        """
        Complete a test and determine winner.

        Args:
            test_id: Test ID

        Returns:
            Winning variant if determined
        """
        test = self.active_tests.get(test_id)
        if not test:
            return None

        test.status = TestStatus.COMPLETED
        test.completed_at = datetime.now()

        # Determine winner
        all_variants = [test.control] + test.variants

        # Get metric for comparison
        if test.winner_criteria == WinnerCriteria.OPEN_RATE:
            metric_values = [(v, v.open_rate) for v in all_variants]
        elif test.winner_criteria == WinnerCriteria.CLICK_RATE:
            metric_values = [(v, v.click_rate) for v in all_variants]
        elif test.winner_criteria == WinnerCriteria.REVENUE:
            metric_values = [(v, v.revenue) for v in all_variants]
        else:
            metric_values = [(v, v.conversion_rate) for v in all_variants]

        # Sort by metric value
        metric_values.sort(key=lambda x: x[1], reverse=True)

        winner = metric_values[0][0]
        winner.is_winner = True
        test.winner = winner

        # Calculate improvement
        control_value = (
            test.control.open_rate
            if test.winner_criteria == WinnerCriteria.OPEN_RATE
            else test.control.click_rate
        )
        winner_value = metric_values[0][1]

        if control_value > 0:
            test.improvement_percentage = (
                (winner_value - control_value) / control_value
            ) * 100

        # Move to history
        self.test_history.append(test)
        del self.active_tests[test_id]

        logger.info(
            f"Test {test_id} completed. Winner: {winner.name} with {test.improvement_percentage:.1f}% improvement"
        )

        return winner

    def get_test_results(self, test_id: str) -> Dict[str, Any]:
        """Get comprehensive test results."""
        test = self.active_tests.get(test_id)
        if not test:
            test = next((t for t in self.test_history if t.test_id == test_id), None)

        if not test:
            return {}

        all_variants = [test.control] + test.variants

        return {
            "test_id": test.test_id,
            "name": test.name,
            "status": test.status.value,
            "type": test.test_type.value,
            "started_at": test.started_at.isoformat() if test.started_at else None,
            "completed_at": (
                test.completed_at.isoformat() if test.completed_at else None
            ),
            "winner": test.winner.name if test.winner else None,
            "statistical_significance": test.statistical_significance,
            "improvement_percentage": test.improvement_percentage,
            "variants": [
                {
                    "name": v.name,
                    "sends": v.sends,
                    "opens": v.opens,
                    "clicks": v.clicks,
                    "open_rate": v.open_rate,
                    "click_rate": v.click_rate,
                    "is_winner": v.is_winner,
                }
                for v in all_variants
            ],
        }

    def _generate_test_id(self, name: str) -> str:
        """Generate unique test ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        name_hash = hashlib.md5(name.encode()).hexdigest()[:8]
        return f"test_{timestamp}_{name_hash}"

    def get_winning_patterns(self) -> Dict[str, List[Dict]]:
        """Analyze test history to identify winning patterns."""
        patterns = {"subject_lines": [], "send_times": [], "content_types": []}

        for test in self.test_history:
            if test.winner and test.improvement_percentage > 10:
                if test.test_type == TestType.SUBJECT_LINE:
                    patterns["subject_lines"].append(
                        {
                            "pattern": test.winner.content.get("pattern_type"),
                            "improvement": test.improvement_percentage,
                            "sample_size": test.winner.sends,
                        }
                    )

        return patterns
