#!/bin/bash
# Test with real external services
# WARNING: Requires actual services running

set -e

echo "================================"
echo "  Real Services Testing Suite   "
echo "================================"
echo ""
echo "⚠️  WARNING: This will make real API calls!"
echo ""

# Check if Ollama is running
check_ollama() {
    echo -n "Checking Ollama... "
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✓ Running"
        return 0
    else
        echo "✗ Not running"
        echo "  Start with: ollama serve"
        return 1
    fi
}

# Check if MailHog is running
check_mailhog() {
    echo -n "Checking MailHog... "
    if curl -s http://localhost:8025/api/v2/messages > /dev/null 2>&1; then
        echo "✓ Running"
        return 0
    else
        echo "✗ Not running (optional)"
        echo "  Start with: docker run -p 1025:1025 -p 8025:8025 mailhog/mailhog"
        return 0
    fi
}

# Check internet connectivity
check_internet() {
    echo -n "Checking internet... "
    if ping -c 1 google.com > /dev/null 2>&1; then
        echo "✓ Connected"
        return 0
    else
        echo "✗ No connection"
        return 1
    fi
}

echo "Pre-flight checks:"
echo "------------------"
check_ollama
OLLAMA_OK=$?
check_mailhog
check_internet || exit 1

echo ""
echo "Select test mode:"
echo "1) Quick test (Ollama + RSS only)"
echo "2) Full test (All services)"
echo "3) Specific service test"
echo "4) Benchmark mode (performance test)"
echo ""
read -p "Choice [1-4]: " choice

case $choice in
    1)
        echo "Running quick real service tests..."
        python -m pytest tests/test_integration_real.py::TestRealIntegration::test_real_ollama_summarization -v
        python -m pytest tests/test_integration_real.py::TestRealIntegration::test_real_rss_feed -v
        ;;
    2)
        echo "Running full real service tests..."
        python -m pytest tests/test_integration_real.py -v -m real_services
        ;;
    3)
        echo "Select service:"
        echo "a) Ollama LLM"
        echo "b) RSS Feeds"
        echo "c) Email (MailHog)"
        echo "d) Reddit API"
        echo "e) HackerNews API"
        read -p "Choice [a-e]: " service
        case $service in
            a) python -m pytest tests/test_integration_real.py::TestRealIntegration::test_real_ollama_summarization -v ;;
            b) python -m pytest tests/test_integration_real.py::TestRealIntegration::test_real_rss_feed -v ;;
            c) python -m pytest tests/test_integration_real.py::TestRealIntegration::test_real_email_send -v ;;
            d) python -c "from newsauto.scrapers.reddit import RedditScraper; import asyncio; asyncio.run(RedditScraper().test_connection())" ;;
            e) python -c "from newsauto.scrapers.hackernews import HackerNewsScraper; import asyncio; asyncio.run(HackerNewsScraper().test_connection())" ;;
        esac
        ;;
    4)
        echo "Running performance benchmark..."
        python -c "
import asyncio
import time
from newsauto.scrapers.aggregator import ContentAggregator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from newsauto.models.base import Base

async def benchmark():
    engine = create_engine('sqlite:///test_bench.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    aggregator = ContentAggregator(session)

    start = time.time()
    content = await aggregator.fetch_from_sources(['hackernews', 'rss'])
    elapsed = time.time() - start

    print(f'Fetched {len(content)} articles in {elapsed:.2f} seconds')
    print(f'Rate: {len(content)/elapsed:.1f} articles/second')

    session.close()

asyncio.run(benchmark())
"
        ;;
esac

echo ""
echo "================================"
echo "Real service testing complete!"
echo ""
echo "💡 TIP: For development, use mocked tests:"
echo "   make test"
echo ""
echo "📊 View test coverage:"
echo "   pytest --cov=newsauto tests/ --cov-report=html"
echo "   open htmlcov/index.html"