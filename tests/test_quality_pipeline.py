"""Tests for quality control pipeline."""

import pytest
from newsauto.quality.hallucination_detector import HallucinationDetector
from newsauto.quality.factual_checker import FactualChecker
from newsauto.quality.sentiment_analyzer import SentimentAnalyzer


class TestHallucinationDetector:
    """Test hallucination detection."""

    @pytest.fixture
    def detector(self):
        return HallucinationDetector()

    @pytest.mark.asyncio
    async def test_no_hallucination(self, detector):
        """Test content without hallucinations."""
        summary = "The company released a new product."
        source = "Today, the company announced the release of a new product."

        score = await detector.check(summary, source)
        assert score > 0.7, "Should have high score for accurate summary"

    @pytest.mark.asyncio
    async def test_hallucinated_numbers(self, detector):
        """Test detection of hallucinated numbers."""
        summary = "The product costs $500 and has 95% user satisfaction."
        source = "The company released a new product today."

        score = await detector.check(summary, source)
        assert score < 0.6, "Should detect hallucinated numbers"

    @pytest.mark.asyncio
    async def test_hallucinated_entities(self, detector):
        """Test detection of hallucinated entities."""
        summary = "CEO John Smith announced the partnership with Microsoft."
        source = "The company announced a new partnership today."

        score = await detector.check(summary, source)
        assert score < 0.7, "Should detect hallucinated entities"


class TestFactualChecker:
    """Test factual accuracy checking."""

    @pytest.fixture
    def checker(self):
        return FactualChecker()

    @pytest.mark.asyncio
    async def test_trusted_source(self, checker):
        """Test credibility of trusted sources."""
        url = "https://www.nytimes.com/article"
        score = await checker.check("Test summary", url)
        assert score > 0.8, "Trusted sources should have high score"

    @pytest.mark.asyncio
    async def test_unknown_source(self, checker):
        """Test credibility of unknown sources."""
        url = "https://random-blog.com/post"
        score = await checker.check("Test summary", url)
        assert 0.4 <= score <= 0.7, "Unknown sources should have medium score"

    def test_credibility_report(self, checker):
        """Test credibility report generation."""
        report = checker.get_credibility_report("https://www.reuters.com/article")
        assert report["is_trusted_source"] == True
        assert report["credibility_score"] >= 0.9


class TestSentimentAnalyzer:
    """Test sentiment analysis."""

    @pytest.fixture
    def analyzer(self):
        return SentimentAnalyzer()

    @pytest.mark.asyncio
    async def test_neutral_sentiment(self, analyzer):
        """Test neutral content."""
        text = "The company released quarterly earnings today."
        score = await analyzer.analyze(text)
        assert -0.2 <= score <= 0.2, "Should detect neutral sentiment"

    @pytest.mark.asyncio
    async def test_positive_sentiment(self, analyzer):
        """Test overly positive content."""
        text = "This amazing revolutionary product is absolutely incredible and fantastic!"
        score = await analyzer.analyze(text)
        assert score > 0.5, "Should detect positive sentiment"

    @pytest.mark.asyncio
    async def test_negative_sentiment(self, analyzer):
        """Test overly negative content."""
        text = "This terrible disaster is a complete failure and catastrophe."
        score = await analyzer.analyze(text)
        assert score < -0.5, "Should detect negative sentiment"

    def test_professional_tone(self, analyzer):
        """Test professional tone checking."""
        professional = "The company reported a 10% increase in revenue."
        unprofessional = "The company's results are AMAZING!!! WOW!!!"

        report1 = analyzer.check_professional_tone(professional)
        report2 = analyzer.check_professional_tone(unprofessional)

        assert report1["is_professional"] == True
        assert report2["is_professional"] == False
