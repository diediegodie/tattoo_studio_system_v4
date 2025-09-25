"""
Unit tests for UserService Google OAuth functionality.

This module tests the Google OAuth user creation and update operations:
- New user creation from Google profile
- Existing user updates via Google ID
- Linking Google accounts to existing users by email
- Error handling for incomplete Google profile data
"""

from typing import Dict, Optional
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
class TestUserServiceGoogleOAuth:
    """Test Google OAuth user creation and update functionality."""

    def test_create_or_update_from_google_success_new_user(self, service, mock_repo):
        """Test successful creation of new user from Google profile."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        google_info = {
            "id": "123456789",
            "email": "john.doe@gmail.com",
            "name": "John Doe",
            "picture": "https://example.com/avatar.jpg",
        }

        # Mock repository to return None (user doesn't exist)
        mock_repo.get_by_google_id.return_value = None
        mock_repo.get_by_email.return_value = None

        # Mock successful creation
        mock_created_user = DomainUser(
            id=1,
            email=google_info["email"],
            name=google_info["name"],
            google_id=google_info["id"],
            avatar_url=google_info["picture"],
            is_active=True,
        )
        mock_repo.create.return_value = mock_created_user

        result = service.create_or_update_from_google(google_info)

        assert result is not None
        assert result.email == google_info["email"]
        assert result.name == google_info["name"]
        assert result.google_id == google_info["id"]
        assert result.avatar_url == google_info["picture"]
        mock_repo.get_by_google_id.assert_called_once_with("123456789")
        mock_repo.get_by_email.assert_called_once_with(google_info["email"])
        mock_repo.create.assert_called_once()

    def test_create_or_update_from_google_success_existing_by_google_id(
        self, service, mock_repo
    ):
        """Test updating existing user found by Google ID."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        google_info = {
            "id": "123456789",
            "email": "john.doe@gmail.com",
            "name": "John Doe Updated",
            "picture": "https://example.com/avatar2.jpg",
        }

        # Mock existing user
        existing_user = DomainUser(
            id=1,
            email="old.email@gmail.com",
            name="John Doe",
            google_id="123456789",
            avatar_url="https://example.com/old.jpg",
            is_active=True,
        )
        mock_repo.get_by_google_id.return_value = existing_user

        # Mock update
        updated_user = DomainUser(
            id=1,
            email=google_info["email"],
            name=google_info["name"],
            google_id=google_info["id"],
            avatar_url=google_info["picture"],
            is_active=True,
        )
        mock_repo.update.return_value = updated_user

        result = service.create_or_update_from_google(google_info)

        assert result is not None
        assert result.email == google_info["email"]
        assert result.name == google_info["name"]
        assert result.avatar_url == google_info["picture"]
        mock_repo.get_by_google_id.assert_called_once_with("123456789")
        mock_repo.update.assert_called_once()
        mock_repo.create.assert_not_called()

    def test_create_or_update_from_google_success_link_existing_by_email(
        self, service, mock_repo
    ):
        """Test linking Google account to existing user by email."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        google_info = {
            "id": "123456789",
            "email": "john.doe@gmail.com",
            "name": "John Doe",
            "picture": "https://example.com/avatar.jpg",
        }

        # Mock user exists by email but not Google ID
        existing_user = DomainUser(
            id=1,
            email=google_info["email"],
            name="John Doe",
            google_id=None,
            avatar_url=None,
            is_active=True,
        )
        mock_repo.get_by_google_id.return_value = None
        mock_repo.get_by_email.return_value = existing_user

        # Mock update
        updated_user = DomainUser(
            id=1,
            email=google_info["email"],
            name=google_info["name"],
            google_id=google_info["id"],
            avatar_url=google_info["picture"],
            is_active=True,
        )
        mock_repo.update.return_value = updated_user

        result = service.create_or_update_from_google(google_info)

        assert result is not None
        assert result.google_id == google_info["id"]
        assert result.avatar_url == google_info["picture"]
        mock_repo.get_by_google_id.assert_called_once_with("123456789")
        mock_repo.get_by_email.assert_called_once_with(google_info["email"])
        mock_repo.update.assert_called_once()
        mock_repo.create.assert_not_called()

    def test_create_or_update_from_google_missing_required_fields(
        self, service, mock_repo
    ):
        """Test error when Google info is missing required fields."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Missing ID
        incomplete_info = {"email": "john.doe@gmail.com", "name": "John Doe"}

        with pytest.raises(ValueError, match="Incomplete Google profile data"):
            service.create_or_update_from_google(incomplete_info)

        # Missing email
        incomplete_info = {"id": "123456789", "name": "John Doe"}

        with pytest.raises(ValueError, match="Incomplete Google profile data"):
            service.create_or_update_from_google(incomplete_info)

        # Missing name
        incomplete_info = {"id": "123456789", "email": "john.doe@gmail.com"}

        with pytest.raises(ValueError, match="Incomplete Google profile data"):
            service.create_or_update_from_google(incomplete_info)
