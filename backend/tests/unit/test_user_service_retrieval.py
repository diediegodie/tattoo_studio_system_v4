"""
Unit tests for UserService user retrieval functionality.

This module tests user retrieval operations:
- Getting users by ID (success and not found cases)
- Getting users by email (success and not found cases)
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
class TestUserServiceUserRetrieval:
    """Test user retrieval operations."""

    def test_get_user_by_id_success(self, service, mock_repo):
        """Test successful user retrieval by ID."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        user_id = 1
        expected_user = DomainUser(
            id=user_id, email="user@example.com", name="Test User", is_active=True
        )
        mock_repo.get_by_id.return_value = expected_user

        result = service.get_user_by_id(user_id)

        assert result == expected_user
        mock_repo.get_by_id.assert_called_once_with(user_id)

    def test_get_user_by_id_not_found(self, service, mock_repo):
        """Test user retrieval by ID when user doesn't exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        user_id = 999
        mock_repo.get_by_id.return_value = None

        result = service.get_user_by_id(user_id)

        assert result is None
        mock_repo.get_by_id.assert_called_once_with(user_id)

    def test_get_user_by_email_success(self, service, mock_repo):
        """Test successful user retrieval by email."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        email = "user@example.com"
        expected_user = DomainUser(id=1, email=email, name="Test User", is_active=True)
        mock_repo.get_by_email.return_value = expected_user

        result = service.get_user_by_email(email)

        assert result == expected_user
        mock_repo.get_by_email.assert_called_once_with(email)

    def test_get_user_by_email_not_found(self, service, mock_repo):
        """Test user retrieval by email when user doesn't exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        email = "nonexistent@example.com"
        mock_repo.get_by_email.return_value = None

        result = service.get_user_by_email(email)

        assert result is None
        mock_repo.get_by_email.assert_called_once_with(email)
