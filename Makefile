# Newsauto Makefile
# Convenient commands for development and deployment

.PHONY: help install setup run test clean docker-up docker-down migrate

# Default target
help:
	@echo "Newsauto - Newsletter Automation System"
	@echo ""
	@echo "Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make setup        - Initial setup (install + db init + ollama)"
	@echo "  make run          - Run the application"
	@echo "  make test         - Run tests"
	@echo "  make docker-up    - Start Docker containers"
	@echo "  make docker-down  - Stop Docker containers"
	@echo "  make migrate      - Run database migrations"
	@echo "  make clean        - Clean cache and temp files"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt

# Complete setup
setup: install
	@echo "🚀 Setting up Newsauto..."
	@./scripts/setup_ollama.sh
	@python -m newsauto.cli init
	@alembic upgrade head
	@echo "✅ Setup complete!"

# Run application
run:
	@./scripts/startup.sh app

# Run all services
run-all:
	@./scripts/startup.sh all

# Run scheduler only
run-scheduler:
	@./scripts/startup.sh scheduler

# Run tests
test:
	@echo "🧪 Running tests..."
	pytest tests/ -v --cov=newsauto --cov-report=term-missing

# Run specific test file
test-file:
	pytest tests/$(FILE) -v

# Docker commands
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-build:
	docker-compose build

# Development Docker
docker-dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Database migrations
migrate:
	alembic upgrade head

migrate-new:
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

migrate-rollback:
	alembic downgrade -1

# Database operations
db-reset:
	@echo "⚠️  This will delete all data!"
	@read -p "Are you sure? (y/N): " confirm; \
	if [ "$$confirm" = "y" ]; then \
		rm -f data/newsletter.db; \
		python -m newsauto.cli init; \
		alembic upgrade head; \
		echo "✅ Database reset complete"; \
	fi

# Ollama commands
ollama-setup:
	@./scripts/setup_ollama.sh

ollama-pull:
	ollama pull mistral:7b-instruct
	ollama pull deepseek-r1:1.5b

# CLI commands
cli-newsletter:
	python -m newsauto.cli create-newsletter \
		--name "$(NAME)" \
		--frequency "$(FREQ)" \
		--description "$(DESC)"

cli-subscriber:
	python -m newsauto.cli add-subscriber \
		--email "$(EMAIL)" \
		--newsletter-id "$(NL_ID)"

cli-fetch:
	python -m newsauto.cli fetch-content

cli-report:
	python -m newsauto.cli generate-report

# Linting and formatting
lint:
	@echo "🔍 Running linters..."
	ruff check newsauto/
	mypy newsauto/ --ignore-missing-imports

format:
	@echo "✨ Formatting code..."
	black newsauto/ tests/
	isort newsauto/ tests/

# Security scan
security:
	@echo "🔒 Running security scan..."
	pip-audit
	bandit -r newsauto/

# Clean cache and temporary files
clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	@echo "✅ Cleanup complete"

# Development helpers
dev-server:
	uvicorn newsauto.api.main:app --reload --host 0.0.0.0 --port 8000

dev-shell:
	python -i -c "from newsauto.core.database import *; from newsauto.models import *; db = next(get_db())"

# Production deployment
deploy:
	@echo "📦 Preparing for deployment..."
	docker-compose -f docker-compose.yml build
	docker-compose -f docker-compose.yml up -d
	@echo "✅ Deployment complete"

# Monitoring
monitor:
	@echo "📊 System Status:"
	@curl -s http://localhost:8000/api/v1/health | python -m json.tool

metrics:
	@curl -s http://localhost:8000/metrics

logs:
	tail -f logs/newsauto.log

# Backup and restore
backup:
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	mkdir -p backups; \
	cp data/newsletter.db backups/newsletter_$$timestamp.db; \
	echo "✅ Backup created: backups/newsletter_$$timestamp.db"

restore:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make restore FILE=backups/newsletter_TIMESTAMP.db"; \
	else \
		cp $(FILE) data/newsletter.db; \
		echo "✅ Database restored from $(FILE)"; \
	fi

# Quick start for new users
quickstart: setup
	@echo ""
	@echo "🎉 Newsauto is ready!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Edit .env file with your configuration"
	@echo "2. Run 'make run' to start the application"
	@echo "3. Visit http://localhost:8000/docs for API documentation"
	@echo ""

# Version management
version:
	@python -c "from newsauto.core.config import get_settings; print(f'Newsauto v{get_settings().app_version}')"

# Generate documentation
docs:
	@echo "📚 Generating documentation..."
	pdoc --html --output-dir docs newsauto --force

# Quality control commands
quality-check:
	@echo "🔍 Running quality check..."
	python scripts/quality_score.py --sample-rate 0.10 --days-back 1

quality-report:
	@echo "📊 Generating quality report..."
	python scripts/quality_score.py --sample-rate 0.20 --days-back 7 --output json

quality-content:
	@echo "🎯 Checking specific content..."
	@read -p "Content ID: " id; \
	python scripts/quality_score.py --content-id $$id

# Self-healing commands
self-heal-check:
	@echo "🏥 Running health checks..."
	python -c "import asyncio; from newsauto.monitoring.health_checks import ComprehensiveHealthCheck; \
	check = ComprehensiveHealthCheck(); \
	print(asyncio.run(check.check_all()))"

self-heal-start:
	@echo "🔄 Starting self-healing monitoring..."
	python -c "import asyncio; from newsauto.automation.self_heal import start_self_healing; \
	asyncio.run(start_self_healing())"

self-heal-test:
	@echo "🧪 Testing self-healing mechanisms..."
	python -m pytest tests/test_self_healing.py -v

# Alert system commands
alert-test:
	@echo "📢 Testing alert system..."
	python -c "import asyncio; from newsauto.monitoring.alert_manager import send_alert, AlertSeverity; \
	asyncio.run(send_alert('Test Alert', 'This is a test alert', AlertSeverity.INFO))"

alert-history:
	@echo "📜 Recent alerts..."
	python -c "from newsauto.monitoring.alert_manager import get_alert_manager; \
	import json; print(json.dumps(get_alert_manager().get_recent_alerts(24), indent=2))"

# GitHub Projects board
board:
	@echo "📋 Development Board Status"
	@echo "Use /board command in Claude Code for detailed view"
	@echo "Or visit your GitHub Projects board"

# Database migration for quality scores
migrate-quality:
	@echo "🗄️  Applying quality score migrations..."
	alembic upgrade head

.DEFAULT_GOAL := help