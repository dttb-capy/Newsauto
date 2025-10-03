#!/bin/bash

# Newsauto Startup Script
# This script sets up and starts the Newsauto application

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    echo -e "${2}${1}${NC}"
}

print_message "🚀 Starting Newsauto Newsletter Automation System" "$GREEN"

# Check if running in Docker
if [ -f /.dockerenv ]; then
    print_message "Running in Docker container" "$YELLOW"
    IS_DOCKER=true
else
    IS_DOCKER=false
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python
if ! command_exists python3; then
    print_message "Error: Python 3 is not installed" "$RED"
    exit 1
fi

print_message "✓ Python $(python3 --version)" "$GREEN"

# Check if virtual environment exists (if not in Docker)
if [ "$IS_DOCKER" = false ]; then
    if [ ! -d "venv" ]; then
        print_message "Creating virtual environment..." "$YELLOW"
        python3 -m venv venv
    fi

    print_message "Activating virtual environment..." "$YELLOW"
    source venv/bin/activate
fi

# Install/Update dependencies
print_message "Installing dependencies..." "$YELLOW"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        print_message "Creating .env file from template..." "$YELLOW"
        cp .env.example .env
        print_message "⚠️  Please edit .env file with your configuration" "$YELLOW"
    else
        print_message "Warning: No .env file found" "$YELLOW"
    fi
else
    print_message "✓ .env file found" "$GREEN"
fi

# Create necessary directories
print_message "Creating data directories..." "$YELLOW"
mkdir -p data logs data/cache

# Initialize database
print_message "Initializing database..." "$YELLOW"

# Check if database exists
if [ -f "data/newsletter.db" ]; then
    print_message "Database already exists" "$GREEN"

    # Run migrations
    print_message "Running database migrations..." "$YELLOW"
    alembic upgrade head
else
    print_message "Creating new database..." "$YELLOW"
    python -m newsauto.cli init

    # Generate initial migration
    print_message "Generating initial migration..." "$YELLOW"
    alembic revision --autogenerate -m "Initial migration"
    alembic upgrade head
fi

# Check Ollama connection
print_message "Checking Ollama connection..." "$YELLOW"
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    print_message "✓ Ollama is running" "$GREEN"

    # Check for required models
    print_message "Checking LLM models..." "$YELLOW"

    # Function to check if model exists
    check_model() {
        curl -s http://localhost:11434/api/tags | grep -q "\"$1\"" && return 0 || return 1
    }

    # Check and pull models if needed
    models=("mistral:7b-instruct" "deepseek-r1:1.5b")
    for model in "${models[@]}"; do
        if check_model "$model"; then
            print_message "  ✓ $model" "$GREEN"
        else
            print_message "  ⚠️  $model not found. Pull it with: ollama pull $model" "$YELLOW"
        fi
    done
else
    print_message "⚠️  Ollama is not running. Please start it with: ollama serve" "$YELLOW"
fi

# Check SMTP configuration
if [ -n "$SMTP_HOST" ]; then
    print_message "✓ SMTP configured: $SMTP_HOST" "$GREEN"
else
    print_message "⚠️  SMTP not configured. Email sending will not work." "$YELLOW"
fi

# Create default newsletter if none exists
print_message "Checking newsletters..." "$YELLOW"
python -c "
from newsauto.core.database import get_db
from newsauto.models.newsletter import Newsletter
db = next(get_db())
count = db.query(Newsletter).count()
if count == 0:
    print('No newsletters found. Creating default newsletter...')
    from newsauto.models.user import User
    # Create default user if needed
    user = db.query(User).first()
    if not user:
        user = User(email='admin@example.com', username='admin', full_name='Admin User')
        user.set_password('admin123')
        db.add(user)
        db.commit()
        print('Created default admin user (admin@example.com / admin123)')

    # Create default newsletter
    newsletter = Newsletter(
        name='Daily Tech Digest',
        description='Your daily dose of tech news',
        user_id=user.id,
        frequency='daily',
        target_audience='Tech enthusiasts',
        status='active'
    )
    db.add(newsletter)
    db.commit()
    print(f'Created default newsletter: {newsletter.name}')
else:
    print(f'Found {count} newsletter(s)')
"

# Start services based on arguments
case "${1:-app}" in
    app)
        print_message "Starting API server..." "$GREEN"
        print_message "📍 API: http://localhost:8000" "$GREEN"
        print_message "📍 Docs: http://localhost:8000/docs" "$GREEN"
        print_message "Press Ctrl+C to stop" "$YELLOW"
        python main.py
        ;;

    scheduler)
        print_message "Starting scheduler service..." "$GREEN"
        python -m newsauto.cli start-scheduler
        ;;

    worker)
        print_message "Starting background worker..." "$GREEN"
        python -m newsauto.automation.tasks
        ;;

    all)
        print_message "Starting all services..." "$GREEN"

        # Start scheduler in background
        python -m newsauto.cli start-scheduler &
        SCHEDULER_PID=$!

        # Start API server
        python main.py &
        API_PID=$!

        print_message "Services started:" "$GREEN"
        print_message "  - API Server (PID: $API_PID)" "$GREEN"
        print_message "  - Scheduler (PID: $SCHEDULER_PID)" "$GREEN"

        # Wait for any process to exit
        wait -n

        # Kill remaining processes on exit
        kill $SCHEDULER_PID $API_PID 2>/dev/null
        ;;

    test)
        print_message "Running tests..." "$GREEN"
        pytest tests/ -v
        ;;

    *)
        print_message "Usage: $0 [app|scheduler|worker|all|test]" "$YELLOW"
        exit 1
        ;;
esac