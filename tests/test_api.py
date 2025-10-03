"""Tests for API endpoints."""


class TestAuthAPI:
    """Test authentication endpoints."""

    def test_register(self, client):
        """Test user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "password123",
                "full_name": "New User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "id" in data

    def test_login(self, client, test_user):
        """Test user login."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "testpass123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "wrong@example.com", "password": "wrongpass"},
        )

        assert response.status_code == 401

    def test_get_current_user(self, client, auth_headers):
        """Test getting current user."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"


class TestNewsletterAPI:
    """Test newsletter endpoints."""

    def test_create_newsletter(self, client, auth_headers):
        """Test creating newsletter."""
        response = client.post(
            "/api/v1/newsletters/",
            headers=auth_headers,
            json={
                "name": "New Newsletter",
                "description": "Description here",
                "niche": "Technology",
                "settings": {"frequency": "weekly", "target_audience": "General"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Newsletter"
        assert data["settings"]["frequency"] == "weekly"

    def test_list_newsletters(self, client, auth_headers, test_newsletter):
        """Test listing newsletters."""
        response = client.get("/api/v1/newsletters/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(n["id"] == test_newsletter.id for n in data)

    def test_get_newsletter(self, client, auth_headers, test_newsletter):
        """Test getting specific newsletter."""
        response = client.get(
            f"/api/v1/newsletters/{test_newsletter.id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_newsletter.id
        assert data["name"] == test_newsletter.name

    def test_update_newsletter(self, client, auth_headers, test_newsletter):
        """Test updating newsletter."""
        response = client.put(
            f"/api/v1/newsletters/{test_newsletter.id}",
            headers=auth_headers,
            json={"name": "Updated Newsletter", "frequency": "daily"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Newsletter"
        assert data["frequency"] == "daily"

    def test_delete_newsletter(self, client, auth_headers, test_newsletter):
        """Test deleting newsletter."""
        response = client.delete(
            f"/api/v1/newsletters/{test_newsletter.id}", headers=auth_headers
        )

        assert response.status_code == 200

        # Verify deletion
        response = client.get(
            f"/api/v1/newsletters/{test_newsletter.id}", headers=auth_headers
        )
        assert response.status_code == 404


class TestSubscriberAPI:
    """Test subscriber endpoints."""

    def test_create_subscriber(self, client, auth_headers, test_newsletter):
        """Test creating subscriber."""
        response = client.post(
            "/api/v1/subscribers/",
            headers=auth_headers,
            json={
                "email": "newsub@example.com",
                "name": "New Subscriber",
                "newsletter_ids": [test_newsletter.id],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newsub@example.com"
        assert data["status"] == "pending"

    def test_list_subscribers(self, client, auth_headers, test_subscriber):
        """Test listing subscribers."""
        response = client.get("/api/v1/subscribers/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_search_subscribers(self, client, auth_headers, test_subscriber):
        """Test searching subscribers."""
        response = client.get(
            f"/api/v1/subscribers/?search={test_subscriber.email[:5]}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(s["email"] == test_subscriber.email for s in data)

    def test_update_subscriber(self, client, auth_headers, test_subscriber):
        """Test updating subscriber."""
        response = client.put(
            f"/api/v1/subscribers/{test_subscriber.id}",
            headers=auth_headers,
            json={"name": "Updated Name", "preferences": {"frequency": "weekly"}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["preferences"]["frequency"] == "weekly"

    def test_unsubscribe(self, client, test_subscriber, test_newsletter, db_session):
        """Test unsubscribe endpoint."""
        # Create subscription
        from newsauto.models.subscriber import NewsletterSubscriber

        subscription = NewsletterSubscriber(
            newsletter_id=test_newsletter.id, subscriber_id=test_subscriber.id
        )
        db_session.add(subscription)
        db_session.commit()

        # Unsubscribe
        response = client.post(
            f"/api/v1/subscribers/{test_subscriber.id}/unsubscribe",
            json={"newsletter_id": test_newsletter.id},
        )

        assert response.status_code == 200


class TestContentAPI:
    """Test content endpoints."""

    def test_list_content(self, client, auth_headers):
        """Test listing content."""
        response = client.get("/api/v1/content/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_fetch_content(self, client, auth_headers, mock_ollama_client):
        """Test fetching content."""
        response = client.post(
            "/api/v1/content/fetch", headers=auth_headers, json={"limit": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Content fetching started"

    def test_get_content_item(self, client, auth_headers, db_session):
        """Test getting specific content item."""
        from newsauto.models.content import ContentItem

        content = ContentItem(
            url="https://test.com/article",
            title="Test Article",
            content="Content",
            source="test.com",
        )
        db_session.add(content)
        db_session.commit()

        response = client.get(f"/api/v1/content/{content.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == content.id
        assert data["title"] == "Test Article"


class TestEditionAPI:
    """Test edition endpoints."""

    def test_generate_edition(
        self, client, auth_headers, test_newsletter, mock_ollama_client
    ):
        """Test generating newsletter edition."""
        response = client.post(
            "/api/v1/editions/generate",
            headers=auth_headers,
            json={
                "newsletter_id": test_newsletter.id,
                "test_mode": True,
                "max_articles": 5,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["newsletter_id"] == test_newsletter.id
        assert data["test_mode"] is True
        assert data["status"] == "draft"

    def test_preview_edition(self, client, auth_headers, test_newsletter, db_session):
        """Test previewing edition."""
        from newsauto.models.edition import Edition, EditionStatus

        edition = Edition(
            newsletter_id=test_newsletter.id,
            subject="Test Edition",
            status=EditionStatus.DRAFT,
            content={"sections": []},
        )
        db_session.add(edition)
        db_session.commit()

        response = client.get(
            f"/api/v1/editions/{edition.id}/preview", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "html" in data
        assert data["subject"] == "Test Edition"


class TestAnalyticsAPI:
    """Test analytics endpoints."""

    def test_get_overview(self, client, auth_headers):
        """Test getting analytics overview."""
        response = client.get(
            "/api/v1/analytics/overview?period=week", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "subscribers" in data
        assert "engagement" in data
        assert data["period"] == "week"

    def test_get_growth(self, client, auth_headers):
        """Test getting growth data."""
        response = client.get("/api/v1/analytics/growth?days=7", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["period_days"] == 7

    def test_get_engagement(self, client, auth_headers):
        """Test getting engagement metrics."""
        response = client.get("/api/v1/analytics/engagement", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "total_sent" in data
        assert "avg_open_rate" in data
        assert "avg_click_rate" in data


class TestHealthAPI:
    """Test health check endpoints."""

    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_readiness_check(self, client):
        """Test readiness check."""
        response = client.get("/api/v1/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["database"] == "connected"
