"""
Unit tests for UserService following SOLID principles and existing test patterns.

This module tests the UserService business logic with comprehensive coverage:
- Google OAuth user creation/update
- Local authentication
- User management operations
- Artist registration
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Optional

# Test configuration and imports
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()

try:
    from app.services.user_service import UserService
    from tests.factories.repository_factories import UserRepositoryFactory
    from app.domain.entities import User as DomainUser
    from app.core.security import hash_password, verify_password

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


@pytest.mark.unit
@pytest.mark.services
@pytest.mark.user
class TestUserServicePasswordManagement:
    """Test password-related functionality."""

    @patch("services.user_service.hash_password")
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

        # Mock the concrete repository method
        with patch("repositories.user_repo.UserRepository") as MockRepo:
            mock_concrete_repo = Mock()
            mock_concrete_repo.set_password.return_value = True
            MockRepo.return_value = mock_concrete_repo

            # Mock isinstance check
            with patch("services.user_service.UserRepository", MockRepo):
                result = service.set_password(user_id, password)

        assert result is True
        mock_repo.get_by_id.assert_called_once_with(user_id)
        mock_hash.assert_called_once_with(password)

    def test_set_password_user_not_found(self, service, mock_repo):
        """Test password setting when user doesn't exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        user_id = 999
        mock_repo.get_by_id.return_value = None

        result = service.set_password(user_id, "password")

        assert result is False
        mock_repo.get_by_id.assert_called_once_with(user_id)


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
