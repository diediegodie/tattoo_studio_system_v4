"""
Unit tests for UserService artist management functionality.

This module tests artist registration and management operations:
- Artist registration with and without email
- Error handling for empty names and existing emails
- Artist creation and retrieval failures
- Listing all artists
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
class TestUserServiceArtistManagement:
    """Test artist registration and management."""

    def test_register_artist_success_with_email(self, service, mock_repo):
        """Test successful artist registration with email."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        name = "Jane Artist"
        email = "jane.artist@example.com"

        # Mock no existing user with this email
        mock_repo.get_by_email.return_value = None

        # Mock created artist
        created_artist_db = DomainUser(
            id=1, name=name, email=email, role="artist", is_active=True
        )
        mock_repo.create.return_value = created_artist_db
        mock_repo.get_by_id.return_value = created_artist_db

        result = service.register_artist(name, email)

        assert result is not None
        assert result.name == name
        assert result.email == email
        assert result.role == "artist"
        assert result.is_active is True
        mock_repo.get_by_email.assert_called_once_with(email)
        mock_repo.create.assert_called_once()
        mock_repo.get_by_id.assert_called_once_with(1)

    def test_register_artist_success_without_email(self, service, mock_repo):
        """Test successful artist registration without email."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        name = "Jane Artist"

        # Mock created artist
        created_artist_db = DomainUser(
            id=1, name=name, email="", role="artist", is_active=True
        )
        mock_repo.create.return_value = created_artist_db
        mock_repo.get_by_id.return_value = created_artist_db

        result = service.register_artist(name)

        assert result is not None
        assert result.name == name
        assert result.email == ""
        assert result.role == "artist"
        mock_repo.get_by_email.assert_not_called()
        mock_repo.create.assert_called_once()
        mock_repo.get_by_id.assert_called_once_with(1)

    def test_register_artist_empty_name(self, service, mock_repo):
        """Test artist registration with empty name."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        with pytest.raises(ValueError, match="Artist name is required"):
            service.register_artist("")

        with pytest.raises(ValueError, match="Artist name is required"):
            service.register_artist("   ")

    def test_register_artist_email_already_exists(self, service, mock_repo):
        """Test artist registration when email already exists."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        name = "Jane Artist"
        email = "existing@example.com"

        # Mock existing user
        existing_user = DomainUser(
            id=1, email=email, name="Existing User", is_active=True
        )
        mock_repo.get_by_email.return_value = existing_user

        with pytest.raises(ValueError, match=f"Email {email} is already registered"):
            service.register_artist(name, email)

    def test_register_artist_creation_failure(self, service, mock_repo):
        """Test artist registration when creation fails."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        name = "Jane Artist"
        email = "jane.artist@example.com"

        # Mock creation returns None
        mock_repo.get_by_email.return_value = None
        mock_repo.create.return_value = None

        with pytest.raises(ValueError, match="Failed to create artist"):
            service.register_artist(name, email)

    def test_register_artist_retrieval_failure(self, service, mock_repo):
        """Test artist registration when retrieval after creation fails."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        name = "Jane Artist"
        email = "jane.artist@example.com"

        # Mock creation succeeds but retrieval fails
        created_artist_db = DomainUser(
            id=1, name=name, email=email, role="artist", is_active=True
        )
        mock_repo.get_by_email.return_value = None
        mock_repo.create.return_value = created_artist_db
        mock_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Failed to retrieve created artist"):
            service.register_artist(name, email)

    def test_list_artists_success(self, service, mock_repo):
        """Test successful retrieval of all artists."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock artists list
        artists = [
            DomainUser(
                id=1,
                name="Artist One",
                email="one@example.com",
                role="artist",
                is_active=True,
            ),
            DomainUser(
                id=2,
                name="Artist Two",
                email="two@example.com",
                role="artist",
                is_active=True,
            ),
        ]
        mock_repo.get_all_artists.return_value = artists

        result = service.list_artists()

        assert result == artists
        mock_repo.get_all_artists.assert_called_once()
