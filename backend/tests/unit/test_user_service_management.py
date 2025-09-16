"""
Unit tests for UserService user management functionality.

This module tests user management operations:
- User deactivation (success and not found cases)
"""

import pytest
from unittest.mock import Mock
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
class TestUserServiceUserManagement:
    """Test user management operations."""

    def test_deactivate_user_success(self, service, mock_repo):
        """Test successful user deactivation."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        user_id = 1
        existing_user = DomainUser(
            id=user_id, email="user@example.com", name="Test User", is_active=True
        )
        mock_repo.get_by_id.return_value = existing_user
        mock_repo.update.return_value = existing_user

        result = service.deactivate_user(user_id)

        assert result is True
        assert existing_user.is_active is False
        mock_repo.get_by_id.assert_called_once_with(user_id)
        mock_repo.update.assert_called_once_with(existing_user)

    def test_deactivate_user_not_found(self, service, mock_repo):
        """Test deactivation when user doesn't exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        user_id = 999
        mock_repo.get_by_id.return_value = None

        result = service.deactivate_user(user_id)

        assert result is False
        mock_repo.get_by_id.assert_called_once_with(user_id)
        mock_repo.update.assert_not_called()
