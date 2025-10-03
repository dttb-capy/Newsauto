# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Newsauto is a zero-cost automated newsletter platform using local LLMs via Ollama for content aggregation, summarization, and distribution. Built with FastAPI, SQLAlchemy, and designed for RTX GPU acceleration.

## Essential Commands

### Development Setup & Run
```bash
# Quick start (all-in-one)
make quickstart

# Manual setup
./scripts/setup_ollama.sh         # Install Ollama + pull models
make setup                         # Install deps + init DB
make run                          # Start API server
make run-all                      # Start API + scheduler

# Docker
docker-compose up                 # Production setup
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up  # Dev with hot reload
```

### Testing
```bash
# Run tests
make test                         # All tests with coverage
pytest tests/test_api.py -v      # Specific test file
pytest -k "test_create_newsletter" -v  # Specific test
pytest -m "not slow"              # Skip slow tests

# Test individual components
python -m newsauto.cli fetch-content  # Test content fetching
python -m newsauto.cli generate-report # Test analytics
```

### Code Quality
```bash
make lint                         # Run ruff + mypy
make format                       # Black + isort
pytest --cov=newsauto --cov-report=html  # Coverage report
```

### Database Operations
```bash
# Migrations
alembic upgrade head              # Apply migrations
alembic revision --autogenerate -m "message"  # New migration
make db-reset                     # Reset database (destructive!)

# Backup/restore
make backup                       # Creates timestamped backup
make restore FILE=backups/newsletter_TIMESTAMP.db
```

### Newsletter Operations
```bash
# CLI operations
python -m newsauto.cli create-newsletter --name "Tech Daily" --frequency daily
python -m newsauto.cli add-subscriber --email user@example.com --newsletter-id 1
python -m newsauto.cli fetch-content --all-sources
python -m newsauto.cli process-scheduled
python -m newsauto.cli generate-report
```

## Critical Architecture Patterns

### Multi-Layer Processing Pipeline
```
Content Flow: Sources → Scrapers → Deduplicator → Scorer → Cache → LLM Router → Generator → Delivery
Each stage is async and can be scaled independently.
```

### LLM Model Routing Strategy
The system intelligently routes content to different models based on type and resource availability:
- **Mistral 7B**: General purpose, default model
- **DeepSeek R1**: Analytical/technical content requiring reasoning
- **Phi-3/Llama 3.2**: Fast processing for simple tasks
- **BART**: News summarization (via HuggingFace if no GPU)

Model selection happens in `newsauto/llm/ollama_client.py:_select_model()`

### Database Architecture
- **SQLAlchemy with async support**: All models in `newsauto/models/`
- **JSON fields for flexibility**: Settings, preferences, metadata stored as JSON
- **Soft deletes**: Status fields instead of hard deletes
- **Relationship patterns**: M2M via association tables (subscribers ↔ newsletters)

### Caching Strategy
- **LLM responses**: 7-day TTL in `newsauto/llm/cache_manager.py`
- **Content deduplication**: URL hash-based in `newsauto/scrapers/base_scraper.py`
- **API responses**: Redis when available, fallback to in-memory

### Email Delivery System
Dual-mode delivery in `newsauto/email/`:
- **Development**: MailHog on port 1025
- **Production**: SMTP (Gmail) or transactional API (Resend/SendGrid)
- **Tracking**: Pixel tracking + click tracking with analytics

## Key Integration Points

### Ollama Server
Must be running before starting the application:
```bash
ollama serve                      # Start Ollama
curl http://localhost:11434/api/tags  # Verify connection
```

### FastAPI Application Structure
- **Lifespan management**: `newsauto/api/main.py` handles startup/shutdown
- **Middleware stack**: CORS → Authentication → Rate Limiting → Metrics
- **Route organization**: Separate routers per domain in `newsauto/api/routes/`
- **Dependency injection**: Database sessions, auth, via FastAPI DI

### Background Task System
- **Scheduler**: `newsauto/automation/scheduler.py` for periodic tasks
- **Task queue**: AsyncIO-based in dev, Celery-ready for production
- **Cron jobs**: Can be set up via `make setup-cron`

## Configuration Management

### Environment Variables
```bash
# Critical settings (required)
DATABASE_URL=sqlite:///./data/newsletter.db  # or postgresql://...
OLLAMA_HOST=http://localhost:11434
SECRET_KEY=<generate-with-openssl-rand-hex-32>

# Model configuration
OLLAMA_PRIMARY_MODEL=mistral:7b-instruct
OLLAMA_FALLBACK_MODEL=deepseek-r1:1.5b
LLM_CACHE_TTL=604800  # 7 days

# Email (choose one approach)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=app-specific-password
```

### Settings Loading
All config via Pydantic Settings in `newsauto/core/config.py`:
- Loads from environment variables
- Falls back to `.env` file
- Type validation and defaults

## Testing Approach

### Test Organization
- **Unit tests**: Business logic in `tests/test_*.py`
- **API tests**: FastAPI endpoints in `tests/test_api.py`
- **Integration tests**: Full pipeline in `tests/test_integration.py`
- **Fixtures**: Reusable test data in `tests/conftest.py`

### Mocking Strategy
- **Ollama responses**: Mock in `conftest.py:mock_ollama_client`
- **SMTP server**: Mock in `conftest.py:mock_smtp_server`
- **External APIs**: Use `httpx_mock` for HTTP calls

## Performance Optimization Points

### Database Queries
- Use eager loading for relationships: `.options(joinedload(Model.relation))`
- Batch operations with `bulk_insert_mappings()`
- Index critical columns (already defined in models)

### LLM Processing
- Batch inference when possible
- Cache all LLM responses
- Use smaller models for classification tasks
- Implement fallback chain for model failures

### Content Processing
- Concurrent scraping with `asyncio.gather()`
- Deduplication before processing
- Score-based filtering to reduce LLM calls

## Deployment Patterns

### Local Development
```bash
# Terminal 1: Ollama
ollama serve

# Terminal 2: API
make run

# Terminal 3: Scheduler (optional)
python -m newsauto.cli start-scheduler
```

### Docker Production
All services defined in `docker-compose.yml`:
- newsauto: Main API
- ollama: LLM server
- postgres: Database
- redis: Cache
- scheduler: Background tasks
- nginx: Reverse proxy (production profile)

### GitHub Actions Automation
Workflow in `.github/workflows/newsletter.yml` for:
- Daily content fetch and newsletter generation
- Scheduled at optimal times per newsletter
- Uses repository secrets for sensitive config

## Common Development Tasks

### Adding a New Content Source
1. Create scraper in `newsauto/scrapers/new_source.py`
2. Inherit from `BaseScraper`
3. Implement `fetch_from_source()` method
4. Register in `ContentAggregator` in `aggregator.py`

### Adding a New LLM Model
1. Pull model: `ollama pull model-name`
2. Add to model routing in `ollama_client.py:_select_model()`
3. Update prompt templates if needed
4. Add fallback logic

### Creating a New API Endpoint
1. Create router in `newsauto/api/routes/`
2. Define Pydantic models for request/response
3. Implement business logic
4. Register router in `api/main.py`
5. Add tests in `tests/test_api.py`

### Database Schema Changes
1. Modify model in `newsauto/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review generated migration
4. Apply: `alembic upgrade head`

## Monitoring & Debugging

### Health Checks
```bash
curl http://localhost:8000/api/v1/health       # Overall health
curl http://localhost:8000/api/v1/health/ready  # Readiness
curl http://localhost:8000/metrics              # Prometheus metrics
```

### Logs
- Application logs: `logs/newsauto.log`
- Ollama logs: `journalctl -u ollama` or `docker logs newsauto-ollama`
- Database queries: Set `SQLALCHEMY_ECHO=true`

### Performance Profiling
- API endpoints have `X-Process-Time` header
- Slow query logging enabled by default
- Memory profiling: `python -m memory_profiler main.py`