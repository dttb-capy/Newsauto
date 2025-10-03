"""Model router for intelligent LLM selection."""

import logging
from enum import Enum
from typing import Any, Dict, List

from newsauto.core.config import get_settings
from newsauto.llm.cache import LLMCache
from newsauto.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)
settings = get_settings()


class ContentType(Enum):
    """Content type enumeration."""

    NEWS = "news"
    TECHNICAL = "technical"
    RESEARCH = "research"
    GENERAL = "general"
    OPINION = "opinion"
    TUTORIAL = "tutorial"


class ModelRouter:
    """Routes content to appropriate LLM models based on type and requirements."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize model router.

        Args:
            config: Router configuration
        """
        self.config = config or self._default_config()
        self.ollama_client = OllamaClient()
        self.cache = LLMCache()

        # Model routing map
        self.routing_map = {
            ContentType.NEWS: settings.primary_model,
            ContentType.TECHNICAL: settings.analytical_model,
            ContentType.RESEARCH: settings.analytical_model,
            ContentType.GENERAL: settings.primary_model,
            ContentType.OPINION: settings.primary_model,
            ContentType.TUTORIAL: settings.analytical_model,
        }

    def _default_config(self) -> Dict[str, Any]:
        """Get default router configuration."""
        return {
            "enable_cache": settings.llm_cache_enabled,
            "max_retries": 3,
            "fallback_model": settings.primary_model,
        }

    def classify_content(self, text: str) -> ContentType:
        """Classify content type using fast model.

        Args:
            text: Text to classify

        Returns:
            Content type
        """
        # Use first 500 chars for classification
        sample = text[:500]

        # Simple heuristic classification (can be replaced with LLM)
        technical_keywords = [
            "code",
            "api",
            "function",
            "algorithm",
            "implementation",
            "bug",
            "feature",
            "framework",
            "library",
            "deploy",
        ]
        research_keywords = [
            "study",
            "research",
            "paper",
            "findings",
            "experiment",
            "hypothesis",
            "methodology",
            "results",
            "conclusion",
        ]
        news_keywords = [
            "breaking",
            "announced",
            "released",
            "launches",
            "reports",
            "according to",
            "sources",
            "yesterday",
            "today",
        ]
        tutorial_keywords = [
            "how to",
            "guide",
            "tutorial",
            "step by step",
            "learn",
            "example",
            "walkthrough",
            "getting started",
        ]

        text_lower = sample.lower()

        # Count keyword matches
        scores = {
            ContentType.TECHNICAL: sum(
                1 for k in technical_keywords if k in text_lower
            ),
            ContentType.RESEARCH: sum(1 for k in research_keywords if k in text_lower),
            ContentType.NEWS: sum(1 for k in news_keywords if k in text_lower),
            ContentType.TUTORIAL: sum(1 for k in tutorial_keywords if k in text_lower),
        }

        # Return type with highest score, default to general
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)

        # Use LLM for more accurate classification if needed
        categories = [t.value for t in ContentType]
        result = self.ollama_client.classify_content(
            sample, categories, model=settings.classification_model
        )

        if result:
            try:
                return ContentType(result)
            except ValueError:
                pass

        return ContentType.GENERAL

    def select_model(self, content_type: ContentType, length: int = 0) -> str:
        """Select appropriate model based on content type and length.

        Args:
            content_type: Type of content
            length: Content length in characters

        Returns:
            Model name
        """
        # Override for very long content
        if length > 10000:
            # Use model with larger context window
            return settings.primary_model

        return self.routing_map.get(content_type, settings.primary_model)

    def route_and_summarize(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
        force_model: str = None,
    ) -> Dict[str, Any]:
        """Route content to appropriate model and generate summary.

        Args:
            text: Text to summarize
            metadata: Additional metadata
            force_model: Force specific model

        Returns:
            Summary result with metadata
        """
        # Check cache first
        cache_key = self.cache.generate_key(text, "summary")
        cached = self.cache.get(cache_key)
        if cached:
            logger.debug("Cache hit for summary")
            return cached

        # Classify content
        content_type = self.classify_content(text)

        # Select model
        model = force_model or self.select_model(content_type, len(text))

        logger.info(f"Routing {content_type.value} content to model: {model}")

        # Generate summary with retry logic
        summary = None
        for attempt in range(self.config["max_retries"]):
            try:
                summary = self.ollama_client.summarize(text, model=model)
                if summary:
                    break
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.config["max_retries"] - 1:
                    # Use fallback model on final attempt
                    model = self.config["fallback_model"]

        if not summary:
            logger.error("Failed to generate summary after all attempts")
            summary = self._extractive_fallback(text)

        # Extract key points
        key_points = self.ollama_client.extract_key_points(text, model=model)

        # Generate title
        title = self.ollama_client.generate_title(text, model=model)

        result = {
            "summary": summary,
            "key_points": key_points,
            "title": title,
            "content_type": content_type.value,
            "model_used": model,
            "metadata": metadata or {},
        }

        # Cache the result
        if self.config["enable_cache"]:
            self.cache.set(cache_key, result)

        return result

    def _extractive_fallback(self, text: str) -> str:
        """Simple extractive summarization fallback.

        Args:
            text: Text to summarize

        Returns:
            Extractive summary
        """
        sentences = text.split(". ")
        if len(sentences) <= 3:
            return text

        # Return first 3 sentences
        return ". ".join(sentences[:3]) + "."

    def batch_process(
        self,
        items: List[Dict[str, Any]],
        batch_size: int = 4,
    ) -> List[Dict[str, Any]]:
        """Process multiple content items in batch.

        Args:
            items: List of items with 'content' key
            batch_size: Batch size for processing

        Returns:
            List of processed items with summaries
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = [None] * len(items)

        def process_item(index: int, item: Dict[str, Any]) -> tuple:
            text = item.get("content", "")
            metadata = {k: v for k, v in item.items() if k != "content"}

            result = self.route_and_summarize(text, metadata)
            return index, {**item, **result}

        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = {
                executor.submit(process_item, i, item): i
                for i, item in enumerate(items)
            }

            for future in as_completed(futures):
                try:
                    index, processed = future.result()
                    results[index] = processed
                except Exception as e:
                    logger.error(f"Error processing item: {e}")
                    # Keep original item on error
                    results[futures[future]] = items[futures[future]]

        return results

    def analyze_trends(
        self,
        items: List[Dict[str, Any]],
        model: str = None,
    ) -> Dict[str, Any]:
        """Analyze trends across multiple content items.

        Args:
            items: List of content items with summaries
            model: Model to use for analysis

        Returns:
            Trend analysis
        """
        model = model or settings.analytical_model

        # Prepare content for analysis
        summaries = [item.get("summary", "") for item in items if item.get("summary")]
        if not summaries:
            return {"trends": [], "insights": []}

        combined = "\n\n".join(summaries[:20])  # Limit to 20 items

        prompt = f"""Analyze these article summaries and identify:
1. Common themes and trends
2. Contradictions or debates
3. Emerging topics
4. Key takeaways

Summaries:
{combined}

Analysis:"""

        try:
            response = self.ollama_client.client.chat(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a trend analyst. Identify patterns and insights.",
                    },
                    {"role": "user", "content": prompt},
                ],
                options={"temperature": 0.5},
            )

            analysis = response["message"]["content"]

            # Parse into structured format
            trends = []
            insights = []

            for line in analysis.split("\n"):
                line = line.strip()
                if line.startswith("- ") or line.startswith("• "):
                    if "trend" in line.lower() or "theme" in line.lower():
                        trends.append(line[2:])
                    else:
                        insights.append(line[2:])

            return {
                "trends": trends[:5],
                "insights": insights[:5],
                "full_analysis": analysis,
            }

        except Exception as e:
            logger.error(f"Failed to analyze trends: {e}")
            return {"trends": [], "insights": [], "error": str(e)}
