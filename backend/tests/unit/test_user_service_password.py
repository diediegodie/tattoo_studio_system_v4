"""
Unit tests for UserService password management functionality.

This module tests password-related operations:
- Setting passwords with proper hashing
- Error handling when user doesn't exist
"""

import pytest
from unittest.mock import Mock, patch
from typing import Optional

# Test configuration and imports
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()

try:
    from app.services.user_service import UserService
    from tests.factories.repository_factories import UserRepositoryFactory
    from app.domain.entities import User as DomainUser

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
class TestUserServicePasswordManagement:
    """Test password-related functionality."""

    @patch("app.services.user_service.hash_password")
    def test_set_password_success(self, mock_hash, service, mock_repo):
        """Test successful password setting."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        user_id = 1
        [REDACTED_PASSWORD]"
        hashed_[REDACTED_PASSWORD]"

        # Mock user exists
        existing_user = DomainUser(
            id=user_id, email="user@example.com", name="Test User", is_active=True
        )
        mock_repo.get_by_id.return_value = existing_user
        mock_hash.return_value = hashed_password

        # Mock the repository to be a UserRepository instance
        mock_repo.set_[REDACTED_PASSWORD]

        # Mock isinstance to return True
        with patch("app.services.user_service.isinstance", return_value=True):
            result = service.set_password(user_id, password)

        assert result is True
        mock_repo.get_by_id.assert_called_once_with(user_id)
        mock_hash.assert_called_once_with(password)
        mock_repo.set_password.assert_called_once_with(user_id, hashed_password)

    def test_set_password_user_not_found(self, service, mock_repo):
        """Test password setting when user doesn't exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        user_id = 999
        mock_repo.get_by_id.return_value = None

        result = service.set_password(user_id, "password")

        assert result is False
        mock_repo.get_by_id.assert_called_once_with(user_id)
