"""
Authentication fixtures for integration testing.

This module provides authentication-related fixtures including JWT tokens,
mock users, and authenticated test clients.
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Set up test environment paths
from tests.config.test_paths import setup_test_environment

setup_test_environment()

try:
    # Quick availability check for Flask and SQLAlchemy. Do NOT import
    # application modules that may create engines at module import time.
    from datetime import datetime, timedelta, timezone

    import flask  # type: ignore
    import jwt
    from sqlalchemy import text  # type: ignore

    FLASK_IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Flask integration dependencies not available: {e}")
    FLASK_IMPORTS_AVAILABLE = False


@pytest.fixture
def auth_headers():
    """Create authentication headers for protected endpoints."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    # Create a mock JWT token
    payload = {
        "user_id": 123,
        "email": "test@example.com",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }

    # Import jwt locally to avoid relying on a module-level name that may be
    # unbound during static analysis or in environments where top-level imports
    # were skipped.
    try:
        import jwt as _jwt  # local import
    except Exception:
        pytest.skip("PyJWT is not available in the test environment")

    token = _jwt.encode(payload, "test-jwt-secret", algorithm="HS256")
    # PyJWT may return bytes in some versions; ensure we return a str token.
    if isinstance(token, bytes):
        token = token.decode("utf-8")

    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture
def mock_authenticated_user():
    """Create a mock authenticated user for testing."""
    user = Mock()
    user.id = 123
    user.email = "test@example.com"
    user.name = "Test User"
    user.google_id = "google123"
    user.avatar_url = "https://example.com/avatar.jpg"
    user.is_active = True
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def authenticated_client(client, db_session, mock_authenticated_user):
    """Create an authenticated test client with Flask-Login session."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    # Create a test user in the database
    from app.db.base import User

    test_user = User(
        name="Test User",
        email="test@example.com",
        google_id="test123",
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    # Create a custom client class that includes authentication methods
    class AuthenticatedClient:
        def __init__(self, client, user, mock_user):
            self.client = client
            self.user = user
            self.mock_user = mock_user

        def get(self, *args, **kwargs):
            with patch("flask_login.current_user", self.mock_user):
                self.mock_user.is_authenticated = True
                self.mock_user.id = self.user.id
                with self.client.application.test_request_context():
                    with self.client.session_transaction() as sess:
                        sess["user_id"] = self.user.id
                        sess["_user_id"] = str(self.user.id)
                        sess["logged_in"] = True
                return self.client.get(*args, **kwargs)

        def post(self, *args, **kwargs):
            with patch("flask_login.current_user", self.mock_user):
                self.mock_user.is_authenticated = True
                self.mock_user.id = self.user.id
                with self.client.application.test_request_context():
                    with self.client.session_transaction() as sess:
                        sess["user_id"] = self.user.id
                        sess["_user_id"] = str(self.user.id)
                        sess["logged_in"] = True
                return self.client.post(*args, **kwargs)

        def put(self, *args, **kwargs):
            with patch("flask_login.current_user", self.mock_user):
                self.mock_user.is_authenticated = True
                self.mock_user.id = self.user.id
                with self.client.application.test_request_context():
                    with self.client.session_transaction() as sess:
                        sess["user_id"] = self.user.id
                        sess["_user_id"] = str(self.user.id)
                        sess["logged_in"] = True
                return self.client.put(*args, **kwargs)

        def patch(self, *args, **kwargs):
            with patch("flask_login.current_user", self.mock_user):
                self.mock_user.is_authenticated = True
                self.mock_user.id = self.user.id
                with self.client.application.test_request_context():
                    with self.client.session_transaction() as sess:
                        sess["user_id"] = self.user.id
                        sess["_user_id"] = str(self.user.id)
                        sess["logged_in"] = True
                return self.client.patch(*args, **kwargs)

        def delete(self, *args, **kwargs):
            with patch("flask_login.current_user", self.mock_user):
                self.mock_user.is_authenticated = True
                self.mock_user.id = self.user.id
                with self.client.application.test_request_context():
                    with self.client.session_transaction() as sess:
                        sess["user_id"] = self.user.id
                        sess["_user_id"] = str(self.user.id)
                        sess["logged_in"] = True
                return self.client.delete(*args, **kwargs)

        # Add convenience methods for authenticated requests
        def authenticated_get(self, *args, **kwargs):
            return self.get(*args, **kwargs)

        def authenticated_post(self, *args, **kwargs):
            return self.post(*args, **kwargs)

        def authenticated_put(self, *args, **kwargs):
            return self.put(*args, **kwargs)

        def authenticated_patch(self, *args, **kwargs):
            return self.patch(*args, **kwargs)

        def authenticated_delete(self, *args, **kwargs):
            return self.delete(*args, **kwargs)

    return AuthenticatedClient(client, test_user, mock_authenticated_user)
