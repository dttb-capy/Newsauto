"""Ollama client for LLM integration."""

import logging
from typing import Any, Dict, List, Optional

import ollama
from ollama import ResponseError

from newsauto.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OllamaClient:
    """Client for interacting with Ollama server."""

    def __init__(self, host: str = None, timeout: int = None):
        """Initialize Ollama client.

        Args:
            host: Ollama server host URL
            timeout: Request timeout in seconds
        """
        self.host = host or settings.ollama_host
        self.timeout = timeout or settings.ollama_timeout
        self.client = ollama.Client(host=self.host, timeout=self.timeout)
        self.verify_connection()

    def verify_connection(self) -> bool:
        """Verify connection to Ollama server.

        Returns:
            True if connected, False otherwise
        """
        try:
            models = self.client.list()
            available_models = [m["name"] for m in models.get("models", [])]
            logger.info(f"Connected to Ollama. Available models: {available_models}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Ollama at {self.host}: {e}")
            return False

    def list_models(self) -> List[str]:
        """List available models.

        Returns:
            List of model names
        """
        try:
            response = self.client.list()
            return [model["name"] for model in response.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    def pull_model(self, model: str) -> bool:
        """Pull a model from Ollama registry.

        Args:
            model: Model name to pull

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Pulling model: {model}")
            self.client.pull(model)
            logger.info(f"Successfully pulled model: {model}")
            return True
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return False

    def summarize(
        self,
        text: str,
        model: str = None,
        max_tokens: int = None,
        temperature: float = None,
        system_prompt: str = None,
    ) -> Optional[str]:
        """Generate a summary of the given text.

        Args:
            text: Text to summarize
            model: Model to use
            max_tokens: Maximum tokens in response
            temperature: Temperature for generation
            system_prompt: System prompt to use

        Returns:
            Summary text or None if failed
        """
        model = model or settings.primary_model
        max_tokens = max_tokens or settings.default_max_tokens
        temperature = temperature or settings.default_temperature

        if not system_prompt:
            system_prompt = (
                "You are a professional newsletter editor. "
                "Summarize content in a concise, engaging way for newsletter readers. "
                "Focus on key insights and actionable information."
            )

        prompt = f"""Summarize the following article for a newsletter audience.
Keep it concise but informative (2-4 sentences).

Article:
{text}

Summary:"""

        try:
            response = self.client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            )
            return response["message"]["content"].strip()

        except ResponseError as e:
            logger.error(f"Ollama API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during summarization: {e}")
            return None

    def extract_key_points(
        self,
        text: str,
        model: str = None,
        max_points: int = 5,
    ) -> List[str]:
        """Extract key points from text.

        Args:
            text: Text to analyze
            model: Model to use
            max_points: Maximum number of points

        Returns:
            List of key points
        """
        model = model or settings.primary_model

        prompt = f"""Extract the {max_points} most important points from this article.
Format as a numbered list.

Article:
{text}

Key Points:"""

        try:
            response = self.client.chat(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Extract key points clearly and concisely.",
                    },
                    {"role": "user", "content": prompt},
                ],
                options={"temperature": 0.3},
            )

            # Parse the response into a list
            content = response["message"]["content"]
            points = []
            for line in content.split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    # Remove numbering and bullets
                    point = line.lstrip("0123456789.-) ").strip()
                    if point:
                        points.append(point)

            return points[:max_points]

        except Exception as e:
            logger.error(f"Failed to extract key points: {e}")
            return []

    def classify_content(
        self,
        text: str,
        categories: List[str],
        model: str = None,
    ) -> Optional[Dict[str, Any]]:
        """Classify content into categories.

        Args:
            text: Text to classify
            categories: List of possible categories
            model: Model to use

        Returns:
            Classification dict with category, topics, sentiment
        """
        model = model or settings.classification_model
        categories_str = ", ".join(categories)

        prompt = f"""Classify this text into ONE of these categories: {categories_str}

Text: {text[:500]}

Category (respond with just the category name):"""

        try:
            response = self.client.generate(
                model=model,
                prompt=prompt,
                options={
                    "temperature": 0.1,
                    "num_predict": 20,
                },
            )

            category = response["response"].strip().lower()

            # Find best matching category
            selected_category = categories[0]  # Default
            for cat in categories:
                if cat.lower() in category or category in cat.lower():
                    selected_category = cat
                    break

            # Return classification dict
            return {
                "category": selected_category,
                "topics": [],  # Could be enhanced with topic extraction
                "sentiment": "neutral",  # Could call analyze_sentiment
            }

        except Exception as e:
            logger.error(f"Failed to classify content: {e}")
            # Return default classification
            return {
                "category": categories[0] if categories else "General",
                "topics": [],
                "sentiment": "neutral",
            }

    def generate_title(
        self,
        text: str,
        model: str = None,
        style: str = "engaging",
    ) -> Optional[str]:
        """Generate a title for content.

        Args:
            text: Content to generate title for
            model: Model to use
            style: Style of title (engaging, professional, clickbait)

        Returns:
            Generated title or None
        """
        model = model or settings.primary_model

        style_prompts = {
            "engaging": "Create an engaging, informative title",
            "professional": "Create a professional, straightforward title",
            "clickbait": "Create an attention-grabbing title that creates curiosity",
        }

        prompt = f"""{style_prompts.get(style, style_prompts['engaging'])} for this article.
The title should be 5-10 words.

Article:
{text[:1000]}

Title:"""

        try:
            response = self.client.generate(
                model=model,
                prompt=prompt,
                options={
                    "temperature": 0.7,
                    "num_predict": 30,
                },
            )

            title = response["response"].strip()
            # Remove quotes if present
            title = title.strip("\"'")
            return title

        except Exception as e:
            logger.error(f"Failed to generate title: {e}")
            return None

    def generate(
        self,
        prompt: str,
        model: str = None,
        max_tokens: int = None,
        temperature: float = None,
    ) -> Optional[str]:
        """Generate text completion.

        Args:
            prompt: Prompt for generation
            model: Model to use
            max_tokens: Maximum tokens in response
            temperature: Temperature for generation

        Returns:
            Generated text or None
        """
        model = model or settings.primary_model
        max_tokens = max_tokens or settings.default_max_tokens
        temperature = temperature or settings.default_temperature

        try:
            response = self.client.generate(
                model=model,
                prompt=prompt,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            )

            return response["response"].strip()

        except Exception as e:
            logger.error(f"Failed to generate text: {e}")
            return None

    def analyze_sentiment(
        self,
        text: str,
        model: str = None,
    ) -> Optional[Dict[str, Any]]:
        """Analyze sentiment of text.

        Args:
            text: Text to analyze
            model: Model to use

        Returns:
            Sentiment analysis results
        """
        model = model or settings.primary_model

        prompt = f"""Analyze the sentiment of this text.
Respond with: positive, negative, or neutral
Also provide a confidence score (0-100).

Text: {text[:500]}

Sentiment:"""

        try:
            response = self.client.chat(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a sentiment analysis expert.",
                    },
                    {"role": "user", "content": prompt},
                ],
                options={"temperature": 0.1},
            )

            content = response["message"]["content"].lower()

            # Parse response
            sentiment = "neutral"
            confidence = 50

            if "positive" in content:
                sentiment = "positive"
            elif "negative" in content:
                sentiment = "negative"

            # Try to extract confidence
            import re

            numbers = re.findall(r"\d+", content)
            if numbers:
                confidence = min(100, max(0, int(numbers[0])))

            return {"sentiment": sentiment, "confidence": confidence}

        except Exception as e:
            logger.error(f"Failed to analyze sentiment: {e}")
            return None

    def batch_summarize(
        self,
        texts: List[str],
        model: str = None,
        max_workers: int = 4,
    ) -> List[Optional[str]]:
        """Summarize multiple texts in batch.

        Args:
            texts: List of texts to summarize
            model: Model to use
            max_workers: Maximum parallel workers

        Returns:
            List of summaries
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        summaries = [None] * len(texts)

        def summarize_with_index(index: int, text: str) -> tuple:
            summary = self.summarize(text, model=model)
            return index, summary

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(summarize_with_index, i, text): i
                for i, text in enumerate(texts)
            }

            for future in as_completed(futures):
                try:
                    index, summary = future.result()
                    summaries[index] = summary
                except Exception as e:
                    logger.error(f"Error in batch summarization: {e}")

        return summaries
