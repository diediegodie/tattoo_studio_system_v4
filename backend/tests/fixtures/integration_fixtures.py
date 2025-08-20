"""
Integration test fixtures and utilities for Flask testing.

This module provides Flask application configuration, test client setup,
database transaction isolation, and authentication fixtures for integration tests.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from pathlib import Path

# Set up test environment paths
from tests.config.test_paths import setup_test_environment

setup_test_environment()

try:
    from app.app import create_app
    from db.session import SessionLocal, engine
    from sqlalchemy import text
    import jwt
    from datetime import datetime, timedelta

    FLASK_IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Flask integration dependencies not available: {e}")
    FLASK_IMPORTS_AVAILABLE = False


@pytest.fixture(scope="session")
def test_database():
    """Create a test database for the session."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    # Configure test database URL
    test_db_url = f"sqlite:///{db_path}"

    yield test_db_url

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def app(test_database):
    """Create a Flask application configured for testing."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    # Configure app for testing
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_URL": test_database,
            "SECRET_KEY": "test-secret-key",
            "JWT_SECRET_KEY": "test-jwt-secret",
            "WTF_CSRF_ENABLED": False,  # Disable CSRF for testing
        }
    )

    # Create application context
    with app.app_context():
        # Create all tables
        from sqlalchemy import create_engine
        from db.base import Base

        test_engine = create_engine(test_database)
        Base.metadata.create_all(test_engine)

        yield app

        # Cleanup tables
        Base.metadata.drop_all(test_engine)


@pytest.fixture(scope="function")
def client(app):
    """Create a test client for the Flask application."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    return app.test_client()


@pytest.fixture(scope="function")
def runner(app):
    """Create a test runner for the Flask application."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    return app.test_cli_runner()


@pytest.fixture(scope="function")
def db_session(app):
    """Create a database session with transaction isolation."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    # Create a new database session
    session = SessionLocal()

    # Begin a transaction
    transaction = session.begin()

    try:
        yield session
    finally:
        # Always rollback the transaction to isolate tests
        transaction.rollback()
        session.close()


@pytest.fixture
def auth_headers():
    """Create authentication headers for protected endpoints."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    # Create a mock JWT token
    payload = {
        "user_id": 123,
        "email": "test@example.com",
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
    }

    token = jwt.encode(payload, "test-jwt-secret", algorithm="HS256")

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
    user.created_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    return user


@pytest.fixture
def authenticated_client(client, auth_headers):
    """Create a test client with authentication setup."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    def make_authenticated_request(method, url, **kwargs):
        """Make an authenticated request."""
        headers = kwargs.pop("headers", {})
        headers.update(auth_headers)
        kwargs["headers"] = headers

        return getattr(client, method.lower())(url, **kwargs)

    client.authenticated_get = lambda url, **kwargs: make_authenticated_request(
        "GET", url, **kwargs
    )
    client.authenticated_post = lambda url, **kwargs: make_authenticated_request(
        "POST", url, **kwargs
    )
    client.authenticated_put = lambda url, **kwargs: make_authenticated_request(
        "PUT", url, **kwargs
    )
    client.authenticated_delete = lambda url, **kwargs: make_authenticated_request(
        "DELETE", url, **kwargs
    )

    return client


@pytest.fixture
def sample_client_data():
    """Create sample client data for testing."""
    return {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "+1234567890",
        "submission_id": "jotform_123456",
        "birth_date": "1990-01-15",
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_appointment_data():
    """Create sample appointment data for testing."""
    return {
        "client_id": 1,
        "date": "2024-12-25",
        "time": "14:00",
        "service": "Tatuagem Pequena",
        "status": "agendado",
        "notes": "First tattoo session",
    }


@pytest.fixture
def mock_jotform_response():
    """Create mock JotForm API response data."""
    return {
        "responseCode": 200,
        "message": "success",
        "content": [
            {
                "id": "123456",
                "form_id": "242871033645151",
                "ip": "192.168.1.1",
                "created_at": "2024-01-15 10:30:00",
                "status": "ACTIVE",
                "answers": {
                    "3": {"answer": "John Doe"},
                    "4": {"answer": "john.doe@example.com"},
                    "5": {"answer": "+1234567890"},
                    "6": {"answer": "1990-01-15"},
                },
            }
        ],
    }


@pytest.fixture
def database_transaction_isolator(db_session):
    """Provide database transaction isolation for tests."""

    def create_savepoint():
        """Create a savepoint for nested transaction isolation."""
        return db_session.begin_nested()

    def rollback_to_savepoint(savepoint):
        """Rollback to a specific savepoint."""
        savepoint.rollback()

    def commit_savepoint(savepoint):
        """Commit a savepoint."""
        savepoint.commit()

    return {
        "session": db_session,
        "create_savepoint": create_savepoint,
        "rollback_to_savepoint": rollback_to_savepoint,
        "commit_savepoint": commit_savepoint,
    }


class FlaskTestResponse:
    """Helper class for testing Flask responses."""

    @staticmethod
    def assert_json_response(response, expected_status=200):
        """Assert that response is JSON with expected status."""
        assert response.status_code == expected_status
        assert response.content_type == "application/json"
        return response.get_json()

    @staticmethod
    def assert_html_response(response, expected_status=200):
        """Assert that response is HTML with expected status."""
        assert response.status_code == expected_status
        assert "text/html" in response.content_type
        return response.get_data(as_text=True)

    @staticmethod
    def assert_redirect_response(response, expected_location=None):
        """Assert that response is a redirect."""
        assert response.status_code in [301, 302, 303, 307, 308]
        if expected_location:
            assert expected_location in response.location
        return response.location


@pytest.fixture
def response_helper():
    """Provide response testing helper."""
    return FlaskTestResponse()
