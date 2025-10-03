# 🤖 LLM Integration Guide

## Overview

Newsauto uses a multi-model approach with local LLMs for zero-cost operation. The system intelligently routes content to different models based on content type, length, and performance requirements.

## Supported Models

### Primary Models (via Ollama)

| Model | VRAM | Speed | Best For | Context Window |
|-------|------|-------|----------|----------------|
| **Mistral 7B Instruct** | 4.1GB | 60-80 tok/s | General summarization | 32K |
| **DeepSeek R1 7B** | 4.5GB | 50-70 tok/s | Analysis & insights | 32K |
| **Llama 3.2** | 4.7GB | 55-75 tok/s | Versatile content | 128K |
| **Qwen 2.5 7B** | 4.3GB | 60-80 tok/s | Technical content | 32K |
| **Phi-3 Mini** | 2.3GB | 100+ tok/s | Quick classification | 4K |

### Specialized Models (via HuggingFace)

| Model | VRAM | Purpose | Library |
|-------|------|---------|---------|
| **BART-large-CNN** | 1.6GB | News summarization | Transformers |
| **T5-large** | 3GB | Multi-task | Transformers |
| **Pegasus-XSUM** | 2.2GB | Abstractive summaries | Transformers |

## Installation

### 1. Install Ollama

```bash
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version

# Start Ollama service
ollama serve
```

### 2. Pull Required Models

```bash
# Primary model for general summarization
ollama pull mistral:7b-instruct

# Analytical model for insights
ollama pull deepseek-r1:7b

# Fast classifier
ollama pull phi-3

# Optional: Additional models
ollama pull llama3.2:latest
ollama pull qwen2.5:7b
```

### 3. Install Python Dependencies

```bash
pip install ollama transformers torch accelerate
```

### 4. Verify GPU Setup

```python
import torch
print(f"CUDA Available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
```

## Configuration

### Environment Variables

```bash
# .env file
OLLAMA_HOST=http://localhost:11434
OLLAMA_TIMEOUT=120
OLLAMA_GPU_LAYERS=-1  # Use all GPU layers
OLLAMA_CONTEXT_SIZE=4096
HF_MODEL_CACHE=/path/to/models
CUDA_VISIBLE_DEVICES=0
```

### Model Configuration

```python
# config/llm_config.py
LLM_CONFIG = {
    "models": {
        "mistral": {
            "name": "mistral:7b-instruct",
            "type": "ollama",
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 500,
            "timeout": 60,
            "batch_size": 4
        },
        "deepseek": {
            "name": "deepseek-r1:7b",
            "type": "ollama",
            "temperature": 0.5,
            "top_p": 0.95,
            "max_tokens": 800,
            "timeout": 90
        },
        "bart": {
            "name": "facebook/bart-large-cnn",
            "type": "huggingface",
            "max_length": 150,
            "min_length": 50,
            "device": "cuda:0"
        }
    },
    "routing": {
        "news": "bart",
        "technical": "deepseek",
        "general": "mistral",
        "classification": "phi-3"
    },
    "cache": {
        "enabled": True,
        "ttl_days": 7,
        "max_size_gb": 10
    }
}
```

## Implementation

### Basic LLM Client

```python
# llm/ollama_client.py
import ollama
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, host: str = "http://localhost:11434"):
        self.client = ollama.Client(host=host)
        self.verify_connection()

    def verify_connection(self):
        """Check if Ollama is running and accessible"""
        try:
            models = self.client.list()
            logger.info(f"Connected to Ollama. Available models: {models}")
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise

    def summarize(
        self,
        text: str,
        model: str = "mistral:7b-instruct",
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> str:
        """Generate a summary of the given text"""

        prompt = f"""Summarize the following article in a concise, engaging way
        for a newsletter audience. Focus on key insights and actionable information.

        Article:
        {text}

        Summary:"""

        response = self.client.chat(
            model=model,
            messages=[
                {
                    'role': 'system',
                    'content': 'You are a professional newsletter editor.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            options={
                'temperature': temperature,
                'num_predict': max_tokens
            }
        )

        return response['message']['content']
```

### Model Router

```python
# llm/model_router.py
from enum import Enum
from typing import Dict, Any
import hashlib

class ContentType(Enum):
    NEWS = "news"
    TECHNICAL = "technical"
    RESEARCH = "research"
    GENERAL = "general"

class ModelRouter:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ollama_client = OllamaClient()
        self.hf_models = {}
        self._init_hf_models()

    def _init_hf_models(self):
        """Initialize HuggingFace models"""
        from transformers import pipeline

        if "bart" in self.config["models"]:
            self.hf_models["bart"] = pipeline(
                "summarization",
                model="facebook/bart-large-cnn",
                device=0  # Use GPU
            )

    def classify_content(self, text: str) -> ContentType:
        """Classify content type using Phi-3"""
        prompt = f"Classify this text as: news, technical, research, or general.\nText: {text[:500]}\nCategory:"

        response = self.ollama_client.client.generate(
            model="phi-3",
            prompt=prompt,
            options={'temperature': 0.3, 'num_predict': 10}
        )

        category = response['response'].strip().lower()
        return ContentType(category if category in [t.value for t in ContentType] else "general")

    def route_and_summarize(self, text: str, metadata: Dict = None) -> Dict[str, Any]:
        """Route to appropriate model and generate summary"""

        # Classify content
        content_type = self.classify_content(text)

        # Select model based on content type
        if content_type == ContentType.NEWS and "bart" in self.hf_models:
            summary = self._summarize_with_bart(text)
            model_used = "bart-large-cnn"
        elif content_type == ContentType.TECHNICAL:
            summary = self.ollama_client.summarize(text, model="deepseek-r1:7b")
            model_used = "deepseek-r1:7b"
        else:
            summary = self.ollama_client.summarize(text, model="mistral:7b-instruct")
            model_used = "mistral:7b-instruct"

        return {
            "summary": summary,
            "content_type": content_type.value,
            "model_used": model_used,
            "metadata": metadata
        }

    def _summarize_with_bart(self, text: str) -> str:
        """Use BART for news summarization"""
        result = self.hf_models["bart"](
            text,
            max_length=150,
            min_length=50,
            do_sample=False
        )
        return result[0]['summary_text']
```

### Caching Layer

```python
# llm/cache.py
import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

class LLMCache:
    def __init__(self, cache_dir: str = "./data/llm_cache", ttl_days: int = 7):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(days=ttl_days)

    def _get_cache_key(self, text: str, model: str, params: dict) -> str:
        """Generate unique cache key"""
        content = f"{text}:{model}:{json.dumps(params, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, text: str, model: str, params: dict) -> Optional[str]:
        """Retrieve cached summary if exists and not expired"""
        cache_key = self._get_cache_key(text, model, params)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            with open(cache_file, 'r') as f:
                cached = json.load(f)

            cached_time = datetime.fromisoformat(cached['timestamp'])
            if datetime.now() - cached_time < self.ttl:
                return cached['summary']

        return None

    def set(self, text: str, model: str, params: dict, summary: str):
        """Cache the summary"""
        cache_key = self._get_cache_key(text, model, params)
        cache_file = self.cache_dir / f"{cache_key}.json"

        with open(cache_file, 'w') as f:
            json.dump({
                'summary': summary,
                'timestamp': datetime.now().isoformat(),
                'model': model,
                'text_hash': hashlib.md5(text.encode()).hexdigest()
            }, f)

    def clean_expired(self):
        """Remove expired cache entries"""
        now = datetime.now()
        for cache_file in self.cache_dir.glob("*.json"):
            with open(cache_file, 'r') as f:
                cached = json.load(f)

            cached_time = datetime.fromisoformat(cached['timestamp'])
            if now - cached_time > self.ttl:
                cache_file.unlink()
```

### Batch Processing

```python
# llm/batch_processor.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class BatchProcessor:
    def __init__(self, router: ModelRouter, max_workers: int = 4):
        self.router = router
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.cache = LLMCache()

    async def process_batch(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple articles in parallel"""

        loop = asyncio.get_event_loop()
        tasks = []

        for article in articles:
            task = loop.run_in_executor(
                self.executor,
                self._process_single,
                article
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        return results

    def _process_single(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single article with caching"""

        text = article.get('content', '')

        # Check cache first
        cached = self.cache.get(
            text,
            model="auto",
            params={"type": "summary"}
        )

        if cached:
            logger.debug(f"Cache hit for article: {article.get('title')}")
            return {
                **article,
                "summary": cached,
                "from_cache": True
            }

        # Generate new summary
        try:
            result = self.router.route_and_summarize(text, metadata=article)
            summary = result['summary']

            # Cache the result
            self.cache.set(
                text,
                model="auto",
                params={"type": "summary"},
                summary=summary
            )

            return {
                **article,
                "summary": summary,
                "model_used": result['model_used'],
                "content_type": result['content_type'],
                "from_cache": False
            }

        except Exception as e:
            logger.error(f"Failed to process article: {e}")
            return {
                **article,
                "summary": None,
                "error": str(e)
            }
```

## Prompt Engineering

### Newsletter-Specific Prompts

```python
# prompts/newsletter_prompts.py

PROMPTS = {
    "tech_summary": """
You are a tech newsletter editor. Summarize this article for busy tech professionals.
Focus on: practical implications, key innovations, and actionable insights.
Keep it concise (2-3 sentences) and engaging.

Article: {text}
Summary:
""",

    "research_summary": """
Summarize this research paper for a technical audience.
Include: main findings, methodology highlights, and real-world applications.
Use clear, precise language without oversimplification.

Paper: {text}
Summary:
""",

    "news_summary": """
Create a newsletter-style summary of this news article.
Highlight: key facts, why it matters, and what happens next.
Write in an engaging, conversational tone.

Article: {text}
Summary:
""",

    "trend_analysis": """
Analyze these articles for emerging trends and patterns.
Identify: common themes, contrarian views, and future implications.
Provide strategic insights for decision-makers.

Articles: {text}
Analysis:
""",

    "key_points": """
Extract the 3-5 most important points from this content.
Format as bullet points, each one sentence.
Focus on actionable or surprising information.

Content: {text}
Key Points:
"""
}
```

### Dynamic Prompt Selection

```python
def select_prompt(content_type: str, newsletter_type: str) -> str:
    """Select appropriate prompt based on content and newsletter type"""

    prompt_map = {
        ("news", "tech"): PROMPTS["tech_summary"],
        ("research", "academic"): PROMPTS["research_summary"],
        ("news", "general"): PROMPTS["news_summary"],
        ("multiple", "digest"): PROMPTS["trend_analysis"]
    }

    return prompt_map.get(
        (content_type, newsletter_type),
        PROMPTS["tech_summary"]  # Default
    )
```

## Performance Optimization

### GPU Memory Management

```python
# llm/gpu_manager.py
import torch
import gc

class GPUManager:
    @staticmethod
    def clear_cache():
        """Clear GPU memory cache"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()

    @staticmethod
    def get_memory_usage():
        """Get current GPU memory usage"""
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**3
            reserved = torch.cuda.memory_reserved() / 1024**3
            return {
                "allocated_gb": round(allocated, 2),
                "reserved_gb": round(reserved, 2)
            }
        return {"allocated_gb": 0, "reserved_gb": 0}

    @staticmethod
    def optimize_batch_size(vram_gb: float, model_size_gb: float) -> int:
        """Calculate optimal batch size based on available VRAM"""
        available = vram_gb - model_size_gb - 2  # Reserve 2GB
        batch_size = max(1, int(available / 0.5))  # ~0.5GB per item
        return min(batch_size, 8)  # Cap at 8
```

### Streaming Responses

```python
# llm/streaming.py
def stream_summary(text: str, model: str = "mistral:7b-instruct"):
    """Stream summary generation for real-time display"""

    client = ollama.Client()

    stream = client.chat(
        model=model,
        messages=[{
            'role': 'user',
            'content': f"Summarize: {text}"
        }],
        stream=True
    )

    for chunk in stream:
        if 'message' in chunk and 'content' in chunk['message']:
            yield chunk['message']['content']
```

## Monitoring & Metrics

```python
# llm/metrics.py
from dataclasses import dataclass
from datetime import datetime
import statistics

@dataclass
class LLMMetrics:
    model: str
    tokens_processed: int
    response_time_ms: float
    success: bool
    timestamp: datetime

class MetricsCollector:
    def __init__(self):
        self.metrics = []

    def record(self, metric: LLMMetrics):
        self.metrics.append(metric)

    def get_stats(self, model: str = None, hours: int = 24):
        """Get statistics for model performance"""

        # Filter metrics
        cutoff = datetime.now() - timedelta(hours=hours)
        filtered = [
            m for m in self.metrics
            if m.timestamp > cutoff and (model is None or m.model == model)
        ]

        if not filtered:
            return None

        response_times = [m.response_time_ms for m in filtered if m.success]

        return {
            "model": model,
            "total_requests": len(filtered),
            "success_rate": sum(1 for m in filtered if m.success) / len(filtered) * 100,
            "avg_response_time_ms": statistics.mean(response_times),
            "p95_response_time_ms": statistics.quantiles(response_times, n=20)[18],
            "total_tokens": sum(m.tokens_processed for m in filtered)
        }
```

## Fallback Strategies

```python
# llm/fallback.py
class FallbackHandler:
    def __init__(self, models: List[str]):
        self.models = models
        self.current_index = 0

    def get_next_model(self) -> Optional[str]:
        """Get next available model in fallback chain"""
        if self.current_index < len(self.models):
            model = self.models[self.current_index]
            self.current_index += 1
            return model
        return None

    def reset(self):
        """Reset to primary model"""
        self.current_index = 0

    async def summarize_with_fallback(self, text: str) -> str:
        """Try summarization with fallback models"""

        fallback = FallbackHandler([
            "mistral:7b-instruct",
            "llama3.2:latest",
            "phi-3",
            "simple-extractive"  # Non-LLM fallback
        ])

        while True:
            model = fallback.get_next_model()
            if not model:
                raise Exception("All models failed")

            try:
                if model == "simple-extractive":
                    # Fallback to extractive summarization
                    return self._extractive_summary(text)
                else:
                    return await self._try_model(text, model)
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
                continue
```

## Testing

```python
# tests/test_llm.py
import pytest
from llm.ollama_client import OllamaClient
from llm.model_router import ModelRouter

class TestLLMIntegration:
    def test_ollama_connection(self):
        """Test Ollama server connection"""
        client = OllamaClient()
        assert client.verify_connection()

    def test_mistral_summarization(self):
        """Test Mistral model summarization"""
        client = OllamaClient()
        text = "This is a test article about AI..."
        summary = client.summarize(text, model="mistral:7b-instruct")
        assert len(summary) > 0
        assert len(summary) < len(text)

    def test_content_classification(self):
        """Test content type classification"""
        router = ModelRouter(config={})

        tech_text = "New JavaScript framework released..."
        assert router.classify_content(tech_text) == ContentType.TECHNICAL

        news_text = "Breaking: Stock market reaches new high..."
        assert router.classify_content(news_text) == ContentType.NEWS

    def test_cache_functionality(self):
        """Test LLM response caching"""
        cache = LLMCache()

        # Store in cache
        cache.set("test text", "mistral", {}, "test summary")

        # Retrieve from cache
        cached = cache.get("test text", "mistral", {})
        assert cached == "test summary"
```

## Troubleshooting

### Common Issues

#### 1. Ollama Connection Failed
```bash
# Check if Ollama is running
systemctl status ollama

# Start Ollama
ollama serve

# Test with curl
curl http://localhost:11434/api/tags
```

#### 2. Out of Memory
```python
# Reduce batch size
config["batch_size"] = 1

# Use smaller model
ollama pull phi-3

# Clear GPU cache
torch.cuda.empty_cache()
```

#### 3. Slow Performance
```bash
# Check GPU utilization
nvidia-smi

# Use quantized models
ollama pull mistral:7b-instruct-q4_0

# Enable GPU layers
export OLLAMA_GPU_LAYERS=-1
```

## Best Practices

1. **Always use caching** for repeated content
2. **Monitor GPU memory** to prevent OOM errors
3. **Implement fallbacks** for model failures
4. **Use appropriate models** for content types
5. **Batch process** when possible
6. **Profile regularly** to identify bottlenecks
7. **Keep models updated** for better performance
8. **Test prompts** thoroughly for quality

## Additional Resources

- [Ollama Documentation](https://github.com/ollama/ollama)
- [HuggingFace Transformers](https://huggingface.co/docs/transformers)
- [Prompt Engineering Guide](https://www.promptingguide.ai/)
- [GPU Optimization Tips](https://pytorch.org/tutorials/recipes/recipes/tuning_guide.html)