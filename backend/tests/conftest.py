"""
Central pytest configuration for the tattoo studio system tests.

This file provides common fixtures, test markers, and setup
for both unit and integration tests following SOLID principles.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock

# Set up test environment paths BEFORE any other imports
from tests.config.test_paths import setup_test_environment

# Set up the test environment immediately
print("Configuring test environment in conftest.py...")
setup_test_environment()

# Import after path setup - graceful handling for interface segregation
try:
    from repositories.user_repo import UserRepository
    from services.user_service import UserService

    IMPORTS_AVAILABLE = True
except ImportError as e:
    # Handle import errors gracefully for test discovery
    print(f"Warning: Could not import modules: {e}")
    UserRepository = None
    UserService = None
    IMPORTS_AVAILABLE = False

# Test database configuration
TEST_DATABASE_URL = "sqlite:///:memory:"  # In-memory SQLite for fast tests

# Import integration and auth fixtures for availability across all test modules
# These are made available here for convenience but can also be imported directly
try:
    # Import all fixtures from our fixture modules
    from tests.fixtures.integration_fixtures import *
    from tests.fixtures.auth_fixtures import *

    print("Integration and authentication fixtures loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import advanced fixtures: {e}")
    print("Basic fixtures will still be available")


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
    """
    Create a mock UserRepository for testing.

    Follows Interface Segregation Principle by providing
    only the required repository interface methods.
    """
    if IMPORTS_AVAILABLE and UserRepository is not None:
        repo = Mock(spec=UserRepository)
    else:
        repo = Mock()

    # Repository interface methods - following Single Responsibility
    repo.db = mock_db_session
    repo.get_by_id = Mock()
    repo.get_by_email = Mock()
    repo.get_by_google_id = Mock()
    repo.create = Mock()
    repo.update = Mock()
    repo.set_[REDACTED_PASSWORD]
    return repo


@pytest.fixture
def mock_user_service(mock_user_repository):
    """
    Create a mock UserService for testing.

    Follows Dependency Inversion Principle by depending
    on repository abstraction, not concrete implementation.
    """
    if IMPORTS_AVAILABLE and UserService is not None:
        service = Mock(spec=UserService)
    else:
        service = Mock()

    # Service interface methods - following Single Responsibility
    service.repo = mock_user_repository
    service.create_or_update_from_google = Mock()
    service.set_[REDACTED_PASSWORD]
    service.authenticate_local = Mock()
    return service


# Test markers for different test categories
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "auth: mark test as authentication-related")
    config.addinivalue_line("markers", "security: mark test as security-related")
    config.addinivalue_line("markers", "api: mark test as API endpoint test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


# Test collection customization
def pytest_collection_modifyitems(config, items):
    """Modify test items during collection."""
    # Add markers based on test file location
    for item in items:
        # Add unit marker for tests in unit/ directory
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Add integration marker for tests in integration/ directory
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Add auth marker for authentication tests
        if "auth" in str(item.fspath) or "auth" in item.name:
            item.add_marker(pytest.mark.auth)

        # Add security marker for security tests
        if "security" in str(item.fspath) or "security" in item.name:
            item.add_marker(pytest.mark.security)


# Session-level fixtures for performance
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
