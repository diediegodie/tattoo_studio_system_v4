"""
Authentication fixtures for testing protected endpoints.

This module provides comprehensive authentication testing utilities,
including JWT token generation, user session management, and
authentication state mocking for different test scenarios.
"""

import pytest
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from tests.config.test_paths import setup_test_environment

setup_test_environment()

try:
    from app.core.security import create_access_token, verify_token
    from app.domain.entities import User

    AUTH_IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Authentication dependencies not available: {e}")
    AUTH_IMPORTS_AVAILABLE = False


@pytest.fixture(scope="function")
def jwt_secret():
    """Provide JWT secret key for testing."""
    import os

    return os.getenv("JWT_SECRET_KEY", "test-jwt-secret")


@pytest.fixture
def valid_jwt_token(jwt_secret):
    """Create a valid JWT token for testing."""
    if not AUTH_IMPORTS_AVAILABLE:
        pytest.skip("Authentication dependencies not available")

    payload = {
        "sub": "123",
        "email": "test@example.com",
        "name": "Test User",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    return jwt.encode(payload, jwt_secret, algorithm="HS256")


@pytest.fixture
def expired_jwt_token(jwt_secret):
    """Create an expired JWT token for testing."""
    if not AUTH_IMPORTS_AVAILABLE:
        pytest.skip("Authentication dependencies not available")

    payload = {
        "sub": "123",
        "email": "test@example.com",
        "name": "Test User",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        "type": "access",
    }

    return jwt.encode(payload, jwt_secret, algorithm="HS256")


@pytest.fixture
def invalid_jwt_token():
    """Create an invalid JWT token for testing."""
    return "invalid.jwt.token"


@pytest.fixture
def admin_jwt_token(jwt_secret):
    """Create a JWT token for admin user testing."""
    if not AUTH_IMPORTS_AVAILABLE:
        pytest.skip("Authentication dependencies not available")

    payload = {
        "sub": "1",
        "email": "admin@example.com",
        "name": "Admin User",
        "role": "admin",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    return jwt.encode(payload, jwt_secret, algorithm="HS256")


@pytest.fixture
def regular_user_jwt_token(jwt_secret):
    """Create a JWT token for regular user testing."""
    if not AUTH_IMPORTS_AVAILABLE:
        pytest.skip("Authentication dependencies not available")

    payload = {
        "sub": "456",
        "email": "user@example.com",
        "name": "Regular User",
        "role": "user",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }

    return jwt.encode(payload, jwt_secret, algorithm="HS256")


@pytest.fixture
def auth_headers_valid(valid_jwt_token):
    """Create valid authentication headers."""
    return {
        "Authorization": f"Bearer {valid_jwt_token}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def auth_headers_expired(expired_jwt_token):
    """Create authentication headers with expired token."""
    return {
        "Authorization": f"Bearer {expired_jwt_token}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def auth_headers_invalid(invalid_jwt_token):
    """Create authentication headers with invalid token."""
    return {
        "Authorization": f"Bearer {invalid_jwt_token}",
        "Content-Type": "application/json",
    }


@pytest.fixture
def auth_headers_missing():
    """Create headers without authentication."""
    return {"Content-Type": "application/json"}


@pytest.fixture
def mock_authenticated_user():
    """Create a mock authenticated user."""
    user = Mock()
    user.id = 123
    user.email = "test@example.com"
    user.name = "Test User"
    user.google_id = "google123"
    user.avatar_url = "https://example.com/avatar.jpg"
    user.is_active = True
    user.role = "user"
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    user = Mock()
    user.id = 1
    user.email = "admin@example.com"
    user.name = "Admin User"
    user.google_id = "admin123"
    user.avatar_url = "https://example.com/admin-avatar.jpg"
    user.is_active = True
    user.role = "admin"
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def mock_inactive_user():
    """Create a mock inactive user."""
    user = Mock()
    user.id = 789
    user.email = "inactive@example.com"
    user.name = "Inactive User"
    user.google_id = "inactive123"
    user.avatar_url = None
    user.is_active = False
    user.role = "user"
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def authentication_scenarios():
    """Provide various authentication scenarios for testing."""
    return {
        "valid_user": {
            "user_id": 123,
            "email": "test@example.com",
            "name": "Test User",
            "role": "user",
            "is_active": True,
        },
        "admin_user": {
            "user_id": 1,
            "email": "admin@example.com",
            "name": "Admin User",
            "role": "admin",
            "is_active": True,
        },
        "inactive_user": {
            "user_id": 789,
            "email": "inactive@example.com",
            "name": "Inactive User",
            "role": "user",
            "is_active": False,
        },
        "non_existent_user": {
            "user_id": 999,
            "email": "nonexistent@example.com",
            "name": "Non Existent User",
            "role": "user",
            "is_active": True,
        },
    }


@pytest.fixture
def mock_session_with_auth():
    """Create a mock session with authentication."""
    session = Mock()
    session.get.return_value = {
        "user_id": 123,
        "email": "test@example.com",
        "name": "Test User",
        "authenticated": True,
        "login_time": datetime.now(timezone.utc).isoformat(),
    }
    return session


@pytest.fixture
def mock_session_without_auth():
    """Create a mock session without authentication."""
    session = Mock()
    session.get.return_value = None
    return session


class AuthTestHelper:
    """Helper class for authentication testing."""

    @staticmethod
    def assert_requires_auth(response):
        """Assert that endpoint requires authentication."""
        assert response.status_code == 401
        if response.content_type == "application/json":
            data = response.get_json()
            assert "error" in data or "message" in data

    @staticmethod
    def assert_forbidden(response):
        """Assert that endpoint returns forbidden."""
        assert response.status_code == 403
        if response.content_type == "application/json":
            data = response.get_json()
            assert "error" in data or "message" in data

    @staticmethod
    def assert_authenticated_success(response, expected_status=200):
        """Assert that authenticated request succeeds."""
        assert response.status_code == expected_status
        return (
            response.get_json()
            if response.content_type == "application/json"
            else response.get_data(as_text=True)
        )

    @staticmethod
    def create_auth_headers(token):
        """Create authentication headers from token."""
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    @staticmethod
    def extract_token_payload(token, [REDACTED_SECRET]"):
        """Extract payload from JWT token for testing."""
        try:
            return jwt.decode(token, secret, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return None


@pytest.fixture
def auth_test_helper():
    """Provide authentication testing helper."""
    return AuthTestHelper()


@pytest.fixture
def protected_endpoint_tester(client, auth_test_helper):
    """Create a helper for testing protected endpoints."""

    def test_endpoint_protection(endpoint, method="GET", **kwargs):
        """Test that an endpoint is properly protected."""
        # Test without authentication
        response = getattr(client, method.lower())(endpoint, **kwargs)
        auth_test_helper.assert_requires_auth(response)

        # Test with invalid token
        headers = auth_test_helper.create_auth_headers("invalid.token")
        kwargs.setdefault("headers", {}).update(headers)
        response = getattr(client, method.lower())(endpoint, **kwargs)
        auth_test_helper.assert_requires_auth(response)

        return True

    return test_endpoint_protection


@pytest.fixture
def oauth_mock():
    """Mock OAuth authentication responses."""

    def mock_google_oauth_success():
        """Mock successful Google OAuth response."""
        return {
            "id": "google123",
            "email": "test@example.com",
            "verified_email": True,
            "name": "Test User",
            "given_name": "Test",
            "family_name": "User",
            "picture": "https://example.com/avatar.jpg",
            "locale": "en",
        }

    def mock_google_oauth_failure():
        """Mock failed Google OAuth response."""
        return {"error": "invalid_grant", "error_description": "Bad Request"}

    return {"success": mock_google_oauth_success, "failure": mock_google_oauth_failure}


@pytest.fixture
def database_auth_setup(db_session):
    """Set up authentication-related database state."""

    def create_test_user(email="test@example.com", is_active=True, role="user"):
        """Create a test user in the database."""
        # This would create actual user records for integration tests
        # Implementation depends on your User model and repository
        user_data = {
            "email": email,
            "name": f"Test User {email}",
            "google_id": f'google_{email.split("@")[0]}',
            "is_active": is_active,
            "role": role,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        return user_data

    def cleanup_test_users():
        """Clean up test users from database."""
        # Implementation for cleanup
        pass

    return {
        "create_user": create_test_user,
        "cleanup": cleanup_test_users,
        "session": db_session,
    }
