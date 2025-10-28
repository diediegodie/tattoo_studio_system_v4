"""
Central pyte# Add /app to sys.path for relative imports to work in Docker
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/backend') configuration for the tattoo studio system tests.

This file provides common fixtures, test markers, and setup
for both unit and integration tests following SOLID principles.
"""

import os
import sys
import uuid
from pathlib import Path
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import OAuth provider constant for test helpers
try:
    from app.config.oauth_provider import (
        PROVIDER_GOOGLE,
        PROVIDER_GOOGLE_LOGIN,
        PROVIDER_GOOGLE_CALENDAR,
    )
except ImportError:
    # Fallback if import fails during test discovery
    PROVIDER_GOOGLE = "google"
    PROVIDER_GOOGLE_LOGIN = "google_login"
    PROVIDER_GOOGLE_CALENDAR = "google_calendar"

# Add backend directories to sys.path for imports to work
backend_root = Path(__file__).parent.parent  # backend/
backend_app = backend_root / "app"  # backend/app/

sys.path.insert(0, str(backend_app))
sys.path.insert(0, str(backend_root))

# Test database configuration (set early so import-time engines use it)
TEST_DATABASE_URL = "sqlite:///:memory:"  # In-memory SQLite for fast tests
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["TESTING"] = "true"  # Set testing environment variable
os.environ["DISABLE_AUTH_REDIRECTS"] = (
    "1"  # Disable auth redirects in tests (401 instead of 302)
)
os.environ["RATE_LIMIT_ENABLED"] = "0"  # Disable rate limiting in tests
os.environ["JOTFORM_API_KEY"] = "test-api-key"  # Set test JotForm credentials
os.environ["JOTFORM_FORM_ID"] = "test-form-id"

# Base URL for API integration tests (configurable for Docker Compose)
# In CI (Docker Compose), set BASE_URL=http://app:5000 to reach the app service
# Locally, defaults to http://localhost:5000
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")

# Set up test environment paths BEFORE any other imports
from tests.config.test_paths import setup_test_environment

# Set up the test environment immediately
print("Configuring test environment in conftest.py...")
setup_test_environment()

# Ensure application models are imported and tables are created for the test DB.
# IMPORTANT: Import only via 'app.db.*' to avoid loading the same module twice under
# different names, which would create separate in-memory SQLite engines.
try:
    import importlib

    # Import models so Base.metadata is populated (single canonical import path)
    importlib.import_module("app.db.base")

    # Call create_tables on the app.db.session module (safe no-op if not present)
    app_db_session_mod = importlib.import_module("app.db.session")
    if hasattr(app_db_session_mod, "create_tables"):
        print("Creating database tables for tests (app.db.session)...")
        app_db_session_mod.create_tables()
        print("Database tables created successfully")
except Exception as e:
    # Don't fail test collection for table creation problems; show a warning.
    print(f"Warning: could not create test tables: {e}")

# Import after path setup - graceful handling for interface segregation
try:
    import importlib

    # Dynamically import modules to avoid static import resolution errors in editors/linters
    UserRepository = None
    UserService = None

    try:
        repo_mod = importlib.import_module("repositories.user_repo")
        UserRepository = getattr(repo_mod, "UserRepository", None)
    except Exception as e:
        # Do not fail test discovery on import problems; log for debugging.
        print(f"Warning: Could not import repositories.user_repo: {e}")

    try:
        service_mod = importlib.import_module("services.user_service")
        UserService = getattr(service_mod, "UserService", None)
    except Exception as e:
        print(f"Warning: Could not import services.user_service: {e}")

    IMPORTS_AVAILABLE = UserRepository is not None and UserService is not None
except Exception as e:
    # Handle import errors gracefully for test discovery
    print(f"Warning: Could not import modules: {e}")
    UserRepository = None
    UserService = None
    IMPORTS_AVAILABLE = False


# Import integration and auth fixtures for availability across all test modules
try:
    from fixtures.auth_fixtures import *
    from fixtures.integration_fixtures import *

    print("Integration and authentication fixtures loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import advanced fixtures: {e}")
    print("Basic fixtures will still be available")


# Import complex fixtures and markers from config modules
try:
    from config.fixtures import *
    from config.markers import *

    print("Complex fixtures and markers loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import config modules: {e}")
    print("Basic fixtures will still be available")


# =====================================================
# BASIC MOCK FIXTURES
# =====================================================


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = Mock()
    user.id = 123
    user.email = "test@example.com"
    user.name = "Test User"
    user.google_id = "google123"
    user.avatar_url = "https://example.com/avatar.jpg"
    user.password_hash = None
    user.is_active = True
    user.created_at = None
    user.updated_at = None
    return user


@pytest.fixture
def mock_google_user_info():
    """Create mock Google OAuth user info for testing."""
    return {
        "id": "google123456",
        "email": "google.user@gmail.com",
        "name": "Google Test User",
        "picture": "https://lh3.googleusercontent.com/test-avatar",
    }


@pytest.fixture
def mock_db_session():
    """Create a mock database session for testing."""
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.refresh = Mock()
    session.rollback = Mock()
    session.close = Mock()
    session.query = Mock()
    return session


@pytest.fixture
def mock_user_repository(mock_db_session):
    """Create a mock UserRepository for testing."""
    if IMPORTS_AVAILABLE and UserRepository is not None:
        repo = Mock(spec=UserRepository)
    else:
        repo = Mock()

    repo.db = mock_db_session
    repo.get_by_id = Mock()
    repo.get_by_email = Mock()
    repo.get_by_google_id = Mock()
    repo.create = Mock()
    repo.update = Mock()
    repo.set_password = Mock()
    return repo


@pytest.fixture
def mock_user_service(mock_user_repository):
    """Create a mock UserService for testing."""
    if IMPORTS_AVAILABLE and UserService is not None:
        service = Mock(spec=UserService)
    else:
        service = Mock()

    service.repo = mock_user_repository
    service.create_or_update_from_google = Mock()
    service.set_password = Mock()
    service.authenticate_local = Mock()
    return service


# =====================================================
# FLASK APPLICATION FIXTURES
# =====================================================


@pytest.fixture(scope="session")
def app_config():
    """Provide test application configuration."""
    return {
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "JWT_SECRET_KEY": "test-jwt-secret",
        "DATABASE_URL": TEST_DATABASE_URL,
        "GOOGLE_OAUTH_CLIENT_ID": "test-google-client-id",
        "GOOGLE_OAUTH_CLIENT_SECRET": "test-google-client-secret",
    }


@pytest.fixture
def app():
    """Create a Flask application for testing with proper configuration."""
    try:
        import importlib

        main_mod = importlib.import_module("app.main")
        create_app = getattr(main_mod, "create_app", None)
        if create_app is None:
            raise ImportError("create_app not found in 'app.main' module")

        # Set environment variables for testing
        import os

        # Don't set LOGIN_DISABLED globally - let individual tests control this
        # os.environ["LOGIN_DISABLED"] = "true"
        os.environ["TESTING"] = "true"
        os.environ["SECRET_KEY"] = "test-secret-key"
        os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"

        app = create_app()

        # Ensure test configuration is applied
        app.config.update(
            {
                "TESTING": True,
                "WTF_CSRF_ENABLED": False,  # Disable CSRF for testing
                # "LOGIN_DISABLED": True,  # Don't disable login globally
                "SECRET_KEY": "test-secret-key",
                "JWT_SECRET_KEY": "test-jwt-secret",
                "PROPAGATE_EXCEPTIONS": True,  # Show exceptions in tests
            }
        )

        return app
    except Exception as e:
        print(f"Warning: Could not create real Flask app: {e}")
        # Return a mock app if the real one can't be imported
        mock_app = Mock()
        mock_app.config = {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "JWT_SECRET_KEY": "test-jwt-secret",
        }

        # Create a mock test client that supports context manager
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get = Mock()
        mock_client.post = Mock()
        mock_client.put = Mock()
        mock_client.delete = Mock()

        mock_app.test_client = Mock(return_value=mock_client)

        # Create a mock app_context that supports context manager
        mock_app_context = Mock()
        mock_app_context.__enter__ = Mock(return_value=mock_app_context)
        mock_app_context.__exit__ = Mock(return_value=None)
        mock_app.app_context = Mock(return_value=mock_app_context)

        return mock_app


@pytest.fixture
def client(app):
    """Create a test client for Flask application with proper context."""
    if hasattr(app, "test_client") and hasattr(app, "app_context"):
        with app.test_client() as client:
            with app.app_context():
                yield client
    else:
        # Mock client for when app is mocked
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.get_json.return_value = {"success": True}
        mock_client.post.return_value = mock_response
        mock_client.get.return_value = mock_response
        yield mock_client


@pytest.fixture
def app_context(app):
    """Provide Flask application context for tests that need it."""
    with app.app_context():
        yield app


@pytest.fixture
def request_context(app):
    """Provide Flask request context for tests that access request/session/g objects."""
    with app.test_request_context():
        yield


@pytest.fixture
def test_client(app):
    """Enhanced test client with both app and request context."""
    with app.test_client() as client:
        with app.app_context():
            yield client


# =====================================================
# OAUTH TEST HELPERS
# =====================================================


def google_oauth_endpoint(endpoint_suffix: str = "login") -> str:
    """
    Dynamically construct the Google OAuth endpoint name for url_for().

    DEPRECATED: Use google_login_endpoint() or google_calendar_endpoint() instead.

    Uses the PROVIDER_GOOGLE constant to ensure tests use the same
    blueprint name as the application runtime.

    Args:
        endpoint_suffix: The endpoint suffix (e.g., 'login', 'authorized')

    Returns:
        Full endpoint name for url_for() (e.g., 'google.login')

    Example:
        url_for(google_oauth_endpoint('login'))  # -> '/auth/login'
    """
    return f"{PROVIDER_GOOGLE}.{endpoint_suffix}"


def google_login_endpoint(endpoint_suffix: str = "login") -> str:
    """
    Construct Google Login blueprint endpoint for url_for().

    Args:
        endpoint_suffix: The endpoint suffix (e.g., 'login', 'authorized')

    Returns:
        Full endpoint name (e.g., 'google_login.login')

    Example:
        url_for(google_login_endpoint('login'))  # -> '/auth/google_login/login'
    """
    return f"{PROVIDER_GOOGLE_LOGIN}.{endpoint_suffix}"


def google_calendar_endpoint(endpoint_suffix: str = "login") -> str:
    """
    Construct Google Calendar blueprint endpoint for url_for().

    Args:
        endpoint_suffix: The endpoint suffix (e.g., 'login', 'authorized')

    Returns:
        Full endpoint name (e.g., 'google_calendar.login')

    Example:
        url_for(google_calendar_endpoint('login'))  # -> '/auth/calendar/google_calendar/login'
    """
    return f"{PROVIDER_GOOGLE_CALENDAR}.{endpoint_suffix}"


def google_oauth_session_state_key() -> str:
    """
    Return the Flask session key where Flask-Dance stores OAuth state.

    DEPRECATED: Use google_login_session_state_key() or google_calendar_session_state_key().

    Flask-Dance automatically uses the pattern: {blueprint_name}_oauth_state

    Returns:
        Session key string (e.g., 'google_oauth_state')
    """
    return f"{PROVIDER_GOOGLE}_oauth_state"


def google_login_session_state_key() -> str:
    """
    Return the Flask session key for Google Login OAuth state.

    Returns:
        Session key string (e.g., 'google_login_oauth_state')
    """
    return f"{PROVIDER_GOOGLE_LOGIN}_oauth_state"


def google_calendar_session_state_key() -> str:
    """
    Return the Flask session key for Google Calendar OAuth state.

    Returns:
        Session key string (e.g., 'google_calendar_oauth_state')
    """
    return f"{PROVIDER_GOOGLE_CALENDAR}_oauth_state"


@pytest.fixture
def oauth_token_factory():
    """
    Factory fixture for creating OAuth token dictionaries.

    Returns:
        Callable that creates token dicts with customizable fields

    Example:
        token = oauth_token_factory(expires_at=1234567890)
    """

    def _make_token(
        access_token: str = "test-access-token",
        refresh_token: str = "test-refresh-token",
        token_type: str = "Bearer",
        expires_at: int = 1750000000,
        **extra,
    ) -> dict:
        """Create a token dictionary with given values."""
        token = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": token_type,
            "expires_at": expires_at,
        }
        token.update(extra)
        return token

    return _make_token


# =====================================================
# BASIC MOCK FIXTURES
# =====================================================
