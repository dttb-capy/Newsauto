"""Configuration management for Newsauto."""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "Newsauto"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = "sqlite:///./data/newsletter.db"

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_timeout: int = 120
    ollama_gpu_layers: int = -1
    ollama_context_size: int = 4096

    # Models
    primary_model: str = "mistral:7b-instruct"
    analytical_model: str = "deepseek-r1:7b"
    classification_model: str = "phi-3"
    default_temperature: float = 0.7
    default_max_tokens: int = 500

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: str = "Newsletter <noreply@newsauto.io>"
    smtp_tls: bool = True

    # Alternative email
    resend_api_key: Optional[str] = None

    # Reddit (optional)
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    reddit_user_agent: str = "Newsauto/1.0"

    # Cache
    cache_dir: Path = Path("./data/cache")
    cache_ttl_days: int = 7
    llm_cache_enabled: bool = True

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_reload: bool = False

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 100

    # Frontend
    frontend_url: str = "http://localhost:8000"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Tracking
    tracking_base_url: str = "http://localhost:8000/track"
    unsubscribe_base_url: str = "http://localhost:8000/unsubscribe"

    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090

    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/newsauto.log"
    log_format: str = "json"

    # Scheduler
    scheduler_enabled: bool = True
    default_send_time: str = "08:00"
    timezone: str = "America/New_York"

    # Security
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    bcrypt_rounds: int = 12

    # Feature Flags
    enable_registration: bool = True
    enable_analytics: bool = True
    enable_ab_testing: bool = False
    enable_personalization: bool = True

    # Limits
    max_content_items_per_fetch: int = 100
    max_subscribers_per_newsletter: int = 10000
    max_newsletters_per_user: int = 10
    max_summary_length: int = 500

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Create directories if they don't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        Path("./data").mkdir(exist_ok=True)
        Path("./logs").mkdir(exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
