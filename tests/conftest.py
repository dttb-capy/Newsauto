"""Pytest configuration and fixtures."""

import asyncio
import tempfile
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from newsauto.api.main import app
from newsauto.core.config import Settings
from newsauto.core.database import Base

# Import all models to ensure they're registered with Base
from newsauto.models import all_models  # noqa: F401
from newsauto.models.newsletter import Newsletter
from newsauto.models.subscriber import Subscriber
from newsauto.models.user import User


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """Test settings."""
    return Settings(
        database_url="sqlite:///:memory:",
        secret_key="test-secret-key",
        debug=True,
        ollama_host="http://localhost:11434",
        smtp_host="localhost",
        smtp_port=1025,
        smtp_user="test",
        smtp_password="test",
        smtp_from="test@example.com",
    )


@pytest.fixture(scope="function")
def db_session(test_settings) -> Generator[Session, None, None]:
    """Create test database session."""
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        test_settings.database_url,
        connect_args=(
            {"check_same_thread": False}
            if "sqlite" in test_settings.database_url
            else {}
        ),
        poolclass=StaticPool if "sqlite" in test_settings.database_url else None,
    )

    # Create tables
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_settings) -> TestClient:
    """Create test client."""
    import contextlib

    from sqlalchemy.pool import StaticPool

    from newsauto.core.config import get_settings
    from newsauto.core.database import get_db

    # Create separate engine for each test client
    engine = create_engine(
        test_settings.database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create tables
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Override database dependency
    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Override settings dependency
    def override_get_settings():
        return test_settings

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings

    # Create test client without lifespan events
    @contextlib.asynccontextmanager
    async def override_lifespan(app):
        # Don't call init_db, tables are already created above
        yield

    app.router.lifespan_context = override_lifespan

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def test_user(db_session) -> User:
    """Create test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        is_active=True,
    )
    user.set_password("testpass123")

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


@pytest.fixture
def test_newsletter(db_session, test_user) -> Newsletter:
    """Create test newsletter."""
    newsletter = Newsletter(
        name="Test Newsletter",
        description="Test newsletter description",
        user_id=test_user.id,
        status="active",
        settings={
            "max_articles": 10,
            "frequency": "daily",
            "target_audience": "Test audience",
        },
    )

    db_session.add(newsletter)
    db_session.commit()
    db_session.refresh(newsletter)

    return newsletter


@pytest.fixture
def test_subscriber(db_session) -> Subscriber:
    """Create test subscriber."""
    subscriber = Subscriber(
        email="subscriber@example.com",
        name="Test Subscriber",
        status="active",
        preferences={},
        segments=["test"],
    )

    db_session.add(subscriber)
    db_session.commit()
    db_session.refresh(subscriber)

    return subscriber


@pytest.fixture
def auth_headers(test_user, test_settings) -> dict:
    """Create authentication headers."""
    from newsauto.api.routes.auth import create_access_token

    token = create_access_token(
        data={"sub": test_user.username}, settings=test_settings
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def mock_ollama_client(monkeypatch):
    """Mock Ollama client."""

    class MockOllamaClient:
        async def generate(self, prompt, model=None, max_tokens=None):
            return "Mock generated text"

        async def summarize(self, text, max_tokens=None):
            return "Mock summary"

        async def classify_content(self, text):
            return {
                "category": "Technology",
                "topics": ["AI", "Machine Learning"],
                "sentiment": "positive",
            }

    monkeypatch.setattr("newsauto.llm.ollama_client.OllamaClient", MockOllamaClient)
    return MockOllamaClient()


@pytest.fixture
def sample_content_data():
    """Sample content data for testing."""
    return [
        {
            "url": "https://example.com/article1",
            "title": "Test Article 1",
            "author": "Author 1",
            "content": "This is test content for article 1.",
            "published_at": "2024-01-01T00:00:00Z",
        },
        {
            "url": "https://example.com/article2",
            "title": "Test Article 2",
            "author": "Author 2",
            "content": "This is test content for article 2.",
            "published_at": "2024-01-02T00:00:00Z",
        },
    ]


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class MockSMTPServer:
    """Mock SMTP server for testing email sending."""

    def __init__(self):
        self.sent_emails = []
        self.is_connected = False

    async def connect(self):
        self.is_connected = True

    async def starttls(self):
        pass

    async def login(self, username, password):
        pass

    async def send_message(self, message):
        self.sent_emails.append(
            {
                "from": message.get("From"),
                "to": message.get("To"),
                "subject": message.get("Subject"),
                "body": str(message),
            }
        )

    async def quit(self):
        self.is_connected = False


@pytest.fixture
def mock_smtp_server(monkeypatch):
    """Mock SMTP server."""
    server = MockSMTPServer()

    def mock_smtp(*args, **kwargs):
        return server

    monkeypatch.setattr("aiosmtplib.SMTP", mock_smtp)
    return server
