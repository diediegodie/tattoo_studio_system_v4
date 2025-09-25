"""
Unit tests for UserService local authentication functionality.

This module tests local authentication operations:
- Successful authentication with valid credentials
- Error handling when user doesn't exist
"""

from typing import Optional
from unittest.mock import Mock

import pytest
# Test configuration and imports
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()

try:
    from app.domain.entities import User as DomainUser
    from app.services.user_service import UserService
    from tests.factories.repository_factories import UserRepositoryFactory

    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    IMPORTS_AVAILABLE = False


@pytest.fixture
def mock_repo() -> Mock:
    """Create a mock user repository implementing the interface."""
    return UserRepositoryFactory.create_mock_full()


@pytest.fixture
def service(mock_repo) -> UserService:
    """Initialize UserService with mocked repository."""
    return UserService(mock_repo)


@pytest.mark.unit
@pytest.mark.services
@pytest.mark.user
class TestUserServiceAuthentication:
    """Test local authentication functionality."""

    def test_authenticate_local_success(self, service, mock_repo):
        """Test successful local authentication."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        email = "user@example.com"
        [REDACTED_PASSWORD]"

        # Mock user exists
        existing_user = DomainUser(id=1, email=email, name="Test User", is_active=True)
        mock_repo.get_by_email.return_value = existing_user

        result = service.authenticate_local(email, password)

        assert result is not None
        assert result.email == email
        mock_repo.get_by_email.assert_called_once_with(email)

    def test_authenticate_local_user_not_found(self, service, mock_repo):
        """Test authentication when user doesn't exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        email = "nonexistent@example.com"
        mock_repo.get_by_email.return_value = None

        result = service.authenticate_local(email, "password")

        assert result is None
        mock_repo.get_by_email.assert_called_once_with(email)
