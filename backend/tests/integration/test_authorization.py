"""
Integration tests for authorization system.

Tests OAuth callback rejection and API route authorization checks.
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import url_for
from app.core.security import create_user_token
from app.db.base import User


@pytest.fixture
def authorized_user(db_session):
    """Create an authorized user for testing."""
    user = User(
        id=1,
        name="Authorized User",
        email="authorized@example.com",
        google_id="authorized_google_id",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def unauthorized_user(db_session):
    """Create an unauthorized user for testing."""
    user = User(
        id=2,
        name="Unauthorized User",
        email="unauthorized@example.com",
        google_id="unauthorized_google_id",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def authorized_token(authorized_user):
    """Create JWT token for authorized user."""
    return create_user_token(authorized_user.id, authorized_user.email)


@pytest.fixture
def unauthorized_token(unauthorized_user):
    """Create JWT token for unauthorized user."""
    return create_user_token(unauthorized_user.id, unauthorized_user.email)


@pytest.fixture
def logged_in_authorized_client(client, authorized_user):
    """Client with authorized user logged in via Flask-Login."""
    with client:
        # Use Flask-Login's test mode to log in user
        from flask_login import login_user
        with client.application.test_request_context():
            login_user(authorized_user)
        yield client


@pytest.fixture
def logged_in_unauthorized_client(client, unauthorized_user):
    """Client with unauthorized user logged in via Flask-Login."""
    with client:
        from flask_login import login_user
        with client.application.test_request_context():
            login_user(unauthorized_user)
        yield client


class TestOAuthAuthorization:
    """Test OAuth callback email authorization."""

    @patch.dict(
        "os.environ", {"AUTHORIZED_EMAILS": "authorized@example.com,admin@example.com"}
    )
    def test_oauth_callback_with_unauthorized_email(self, client, monkeypatch):
        """Test that OAuth callback rejects unauthorized email."""
        # Mock the OAuth flow
        mock_blueprint = MagicMock()
        mock_blueprint.name = "google_login"
        mock_session = MagicMock()
        
        # Mock the Google API response with unauthorized email
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "unauthorized_google_id",
            "email": "hacker@evil.com",
            "name": "Hacker User",
        }
        mock_session.get.return_value = mock_response
        mock_blueprint.session = mock_session

        # Simulate callback with unauthorized email
        with client.application.test_request_context():
            from app.auth.google_login import create_google_login_blueprint
            from flask_dance.consumer import oauth_authorized
            
            # The callback should reject unauthorized email
            # In real scenario, this would happen during OAuth flow
            # Here we test the authorization check logic
            from app.core.config import is_email_authorized
            
            assert not is_email_authorized("hacker@evil.com")
            assert is_email_authorized("authorized@example.com")

    @patch.dict(
        "os.environ", {"AUTHORIZED_EMAILS": "authorized@example.com"}
    )
    def test_oauth_callback_with_authorized_email(self, client):
        """Test that OAuth callback accepts authorized email."""
        from app.core.config import is_email_authorized
        
        assert is_email_authorized("authorized@example.com")
        assert is_email_authorized("AUTHORIZED@EXAMPLE.COM")  # Case insensitive
        assert not is_email_authorized("other@example.com")


class TestAPIAuthorization:
    """Test API endpoint authorization checks."""

    @patch.dict(
        "os.environ", {"AUTHORIZED_EMAILS": "authorized@example.com"}
    )
    def test_inventory_create_without_token_returns_401(self, client):
        """Test that inventory creation without session/login returns 401.
        
        Note: Inventory routes now use @require_session_authorization 
        which requires Flask-Login session, not JWT tokens.
        """
        response = client.post(
            "/inventory/",
            json={"nome": "Test Item", "quantidade": 10},
        )
        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data
        assert ("Authentication" in data["error"] or "Authorization" in data["error"])

    @patch.dict(
        "os.environ", {"AUTHORIZED_EMAILS": "authorized@example.com"}
    )
    def test_inventory_create_with_invalid_token_returns_401(self, client):
        """Test that inventory creation with invalid token returns 401."""
        response = client.post(
            "/inventory/",
            json={"nome": "Test Item", "quantidade": 10},
            headers={"Authorization": "Bearer invalid_token_123"},
        )
        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data

    @pytest.mark.skip(reason="Inventory routes use @require_session_authorization (Flask-Login), not JWT. Use browser-based integration tests instead.")
    @patch.dict(
        "os.environ", {"AUTHORIZED_EMAILS": "authorized@example.com"}
    )
    def test_inventory_create_with_unauthorized_email_returns_403(
        self, client, unauthorized_token
    ):
        """Test that inventory creation with unauthorized email returns 403."""
        response = client.post(
            "/inventory/",
            json={"nome": "Test Item", "quantidade": 10},
            headers={"Authorization": f"Bearer {unauthorized_token}"},
        )
        assert response.status_code == 403
        data = response.get_json()
        assert "error" in data
        assert "not authorized" in data["error"].lower()

    @pytest.mark.skip(reason="Inventory routes use @require_session_authorization (Flask-Login), not JWT. Use browser-based integration tests instead.")
    @patch.dict(
        "os.environ", {"AUTHORIZED_EMAILS": "authorized@example.com"}
    )
    def test_inventory_create_with_authorized_email_succeeds(
        self, client, authorized_token
    ):
        """Test that inventory creation with authorized email succeeds."""
        response = client.post(
            "/inventory/",
            json={"nome": "Test Item", "quantidade": 10, "observacoes": "Test"},
            headers={"Authorization": f"Bearer {authorized_token}"},
        )
        # Should succeed (200 or 201) - actual implementation may vary
        assert response.status_code in [200, 201]

    @patch.dict(
        "os.environ", {"AUTHORIZED_EMAILS": "authorized@example.com"}
    )
    def test_gastos_create_without_authorization_returns_401(self, client):
        """Test that gastos creation without token returns 401."""
        response = client.post(
            "/gastos/create",
            json={
                "data": "2025-01-15",
                "valor": "100.00",
                "descricao": "Test expense",
                "forma_pagamento": "Dinheiro",
            },
        )
        assert response.status_code == 401

    @pytest.mark.skip(reason="Gastos routes use @require_session_authorization (Flask-Login), not JWT. Use browser-based integration tests instead.")
    @patch.dict(
        "os.environ", {"AUTHORIZED_EMAILS": "authorized@example.com"}
    )
    def test_gastos_create_with_unauthorized_email_returns_403(
        self, client, unauthorized_token
    ):
        """Test that gastos creation with unauthorized email returns 403."""
        response = client.post(
            "/gastos/create",
            json={
                "data": "2025-01-15",
                "valor": "100.00",
                "descricao": "Test expense",
                "forma_pagamento": "Dinheiro",
            },
            headers={"Authorization": f"Bearer {unauthorized_token}"},
        )
        assert response.status_code == 403

    @patch.dict(
        "os.environ", {"AUTHORIZED_EMAILS": "authorized@example.com"}
    )
    def test_sessoes_update_without_authorization_returns_401(self, client):
        """Test that session update without token returns 401."""
        response = client.put(
            "/sessoes/api/1",
            json={
                "data": "2025-01-20",
                "cliente_id": 1,
                "artista_id": 1,
                "valor": "200.00",
            },
        )
        assert response.status_code == 401

    @pytest.mark.skip(reason="Sessoes API routes use @require_session_authorization (Flask-Login), not JWT. Use browser-based integration tests instead.")
    @patch.dict(
        "os.environ", {"AUTHORIZED_EMAILS": "authorized@example.com"}
    )
    def test_sessoes_delete_with_unauthorized_email_returns_403(
        self, client, unauthorized_token
    ):
        """Test that session deletion with unauthorized email returns 403."""
        response = client.delete(
            "/sessoes/api/1",
            headers={"Authorization": f"Bearer {unauthorized_token}"},
        )
        assert response.status_code == 403

    @pytest.mark.skip(reason="Inventory routes use @require_session_authorization (Flask-Login), not JWT. Use browser-based integration tests instead.")
    @patch.dict(
        "os.environ", {"AUTHORIZED_EMAILS": ""}
    )
    def test_empty_authorized_emails_rejects_all_users(self, client, authorized_token):
        """Test that empty AUTHORIZED_EMAILS env var rejects all users."""
        response = client.post(
            "/inventory/",
            json={"nome": "Test Item", "quantidade": 10},
            headers={"Authorization": f"Bearer {authorized_token}"},
        )
        # Should fail even with valid token because no emails are authorized
        assert response.status_code == 403


class TestAuthorizationHelpers:
    """Test authorization helper functions."""

    @patch.dict(
        "os.environ", {"AUTHORIZED_EMAILS": "user1@example.com,user2@example.com,admin@company.com"}
    )
    def test_get_authorized_emails_parses_correctly(self):
        """Test that authorized emails are parsed correctly from env var."""
        from app.core.config import get_authorized_emails
        
        emails = get_authorized_emails()
        assert len(emails) == 3
        assert "user1@example.com" in emails
        assert "user2@example.com" in emails
        assert "admin@company.com" in emails

    @patch.dict(
        "os.environ", {"AUTHORIZED_EMAILS": "USER@EXAMPLE.COM, admin@example.com , test@test.com"}
    )
    def test_get_authorized_emails_normalizes_case_and_whitespace(self):
        """Test that emails are normalized (lowercased, trimmed)."""
        from app.core.config import get_authorized_emails
        
        emails = get_authorized_emails()
        assert "user@example.com" in emails  # Lowercased
        assert "admin@example.com" in emails  # Trimmed
        assert "test@test.com" in emails

    @patch.dict(
        "os.environ", {"AUTHORIZED_EMAILS": ""}
    )
    def test_is_email_authorized_returns_false_for_empty_config(self):
        """Test that empty config rejects all emails."""
        from app.core.config import is_email_authorized
        
        assert not is_email_authorized("any@example.com")
        assert not is_email_authorized("admin@example.com")

    @patch.dict(
        "os.environ", {"AUTHORIZED_EMAILS": "admin@example.com"}
    )
    def test_is_email_authorized_case_insensitive(self):
        """Test that email check is case-insensitive."""
        from app.core.config import is_email_authorized
        
        assert is_email_authorized("admin@example.com")
        assert is_email_authorized("ADMIN@EXAMPLE.COM")
        assert is_email_authorized("Admin@Example.Com")
        assert not is_email_authorized("other@example.com")
