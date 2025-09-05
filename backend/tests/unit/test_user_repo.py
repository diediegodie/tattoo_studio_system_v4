"""
Unit tests for UserRepository following SOLID principles and existing test patterns.

This module tests the UserRepository data access logic with comprehensive coverage:
- CRUD operations with proper domain entity mapping
- Google OAuth user lookup
- Artist role filtering
- Password management
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Optional

# Test configuration and imports
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()

try:
    from app.repositories.user_repo import UserRepository
    from app.domain.entities import User as DomainUser
    from app.db.base import User as DbUser

    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    IMPORTS_AVAILABLE = False


@pytest.fixture
def mock_db_session() -> Mock:
    """Create a mock database session."""
    return Mock()


@pytest.fixture
def repo(mock_db_session) -> UserRepository:
    """Initialize UserRepository with mocked database session."""
    return UserRepository(mock_db_session)


@pytest.mark.unit
@pytest.mark.repositories
@pytest.mark.user
class TestUserRepositoryRetrieval:
    """Test user retrieval operations."""

    def test_get_by_id_success(self, repo, mock_db_session):
        """Test successful user retrieval by ID."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        user_id = 1

        # Mock database user
        db_user = Mock()
        db_user.id = user_id
        db_user.email = "user@example.com"
        db_user.name = "Test User"
        db_user.google_id = "google123"
        db_user.avatar_url = "avatar.jpg"
        db_user.role = "client"
        db_user.is_active = True
        db_user.created_at = None
        db_user.updated_at = None

        # Mock query chain
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = db_user
        mock_db_session.query.return_value = mock_query

        result = repo.get_by_id(user_id)

        assert result is not None
        assert isinstance(result, DomainUser)
        assert result.id == user_id
        assert result.email == "user@example.com"
        assert result.name == "Test User"
        mock_db_session.query.assert_called_once_with(DbUser)
        mock_query.filter_by.assert_called_once_with(id=user_id)

    def test_get_by_id_not_found(self, repo, mock_db_session):
        """Test user retrieval by ID when user doesn't exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        user_id = 999

        # Mock query chain returning None
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        result = repo.get_by_id(user_id)

        assert result is None
        mock_db_session.query.assert_called_once_with(DbUser)
        mock_query.filter_by.assert_called_once_with(id=user_id)

    def test_get_by_email_success(self, repo, mock_db_session):
        """Test successful user retrieval by email."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        email = "user@example.com"

        # Mock database user
        db_user = Mock()
        db_user.id = 1
        db_user.email = email
        db_user.name = "Test User"
        db_user.google_id = None
        db_user.avatar_url = None
        db_user.role = "client"
        db_user.is_active = True
        db_user.created_at = None
        db_user.updated_at = None

        # Mock query chain
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = db_user
        mock_db_session.query.return_value = mock_query

        result = repo.get_by_email(email)

        assert result is not None
        assert isinstance(result, DomainUser)
        assert result.email == email
        mock_query.filter_by.assert_called_once_with(email=email)

    def test_get_by_email_not_found(self, repo, mock_db_session):
        """Test user retrieval by email when user doesn't exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        email = "nonexistent@example.com"

        # Mock query chain returning None
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        result = repo.get_by_email(email)

        assert result is None

    def test_get_by_google_id_success(self, repo, mock_db_session):
        """Test successful user retrieval by Google ID."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        google_id = "google123"

        # Mock database user
        db_user = Mock()
        db_user.id = 1
        db_user.email = "user@example.com"
        db_user.name = "Test User"
        db_user.google_id = google_id
        db_user.avatar_url = "avatar.jpg"
        db_user.role = "client"
        db_user.is_active = True
        db_user.created_at = None
        db_user.updated_at = None

        # Mock query chain
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = db_user
        mock_db_session.query.return_value = mock_query

        result = repo.get_by_google_id(google_id)

        assert result is not None
        assert isinstance(result, DomainUser)
        assert result.google_id == google_id
        mock_query.filter_by.assert_called_once_with(google_id=google_id)

    def test_get_by_google_id_not_found(self, repo, mock_db_session):
        """Test user retrieval by Google ID when user doesn't exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        google_id = "nonexistent"

        # Mock query chain returning None
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        result = repo.get_by_google_id(google_id)

        assert result is None

    def test_get_all_artists_success(self, repo, mock_db_session):
        """Test successful retrieval of all artists."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock database artists
        db_artist1 = Mock()
        db_artist1.id = 1
        db_artist1.email = "artist1@example.com"
        db_artist1.name = "Artist One"
        db_artist1.google_id = None
        db_artist1.avatar_url = None
        db_artist1.role = "artist"
        db_artist1.is_active = True
        db_artist1.created_at = None
        db_artist1.updated_at = None

        db_artist2 = Mock()
        db_artist2.id = 2
        db_artist2.email = "artist2@example.com"
        db_artist2.name = "Artist Two"
        db_artist2.google_id = None
        db_artist2.avatar_url = None
        db_artist2.role = "artist"
        db_artist2.is_active = True
        db_artist2.created_at = None
        db_artist2.updated_at = None

        # Mock query chain
        mock_query = Mock()
        mock_filtered = Mock()
        mock_filtered.order_by.return_value.all.return_value = [db_artist1, db_artist2]
        mock_query.filter_by.return_value = mock_filtered
        mock_db_session.query.return_value = mock_query

        result = repo.get_all_artists()

        assert len(result) == 2
        assert all(isinstance(artist, DomainUser) for artist in result)
        assert result[0].name == "Artist One"
        assert result[1].name == "Artist Two"
        mock_query.filter_by.assert_called_once_with(role="artist")
        mock_filtered.order_by.assert_called_once()

    def test_get_all_artists_empty(self, repo, mock_db_session):
        """Test retrieval of artists when no artists exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock query chain returning empty list
        mock_query = Mock()
        mock_filtered = Mock()
        mock_filtered.order_by.return_value.all.return_value = []
        mock_query.filter_by.return_value = mock_filtered
        mock_db_session.query.return_value = mock_query

        result = repo.get_all_artists()

        assert result == []


@pytest.mark.unit
@pytest.mark.repositories
@pytest.mark.user
class TestUserRepositoryCreation:
    """Test user creation operations."""

    def test_create_success(self, repo, mock_db_session):
        """Test successful user creation."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Domain user to create
        domain_user = DomainUser(
            email="newuser@example.com",
            name="New User",
            google_id="google123",
            avatar_url="avatar.jpg",
            role="client",
            is_active=True,
        )

        # Mock database user creation
        db_user = Mock()
        db_user.id = 1
        db_user.email = "newuser@example.com"
        db_user.name = "New User"
        db_user.google_id = "google123"
        db_user.avatar_url = "avatar.jpg"
        db_user.role = "client"
        db_user.is_active = True

        # Mock the DbUser constructor and session methods
        with patch("app.repositories.user_repo.DbUser") as MockDbUser:
            mock_db_instance = Mock()
            MockDbUser.return_value = mock_db_instance

            # Mock session operations
            mock_db_session.add.return_value = None
            mock_db_session.commit.return_value = None
            mock_db_session.refresh.return_value = None

            # Set up the mock to behave like the created user
            mock_db_instance.id = 1
            mock_db_instance.email = "newuser@example.com"
            mock_db_instance.name = "New User"
            mock_db_instance.google_id = "google123"
            mock_db_instance.avatar_url = "avatar.jpg"
            mock_db_instance.role = "client"
            mock_db_instance.is_active = True

            result = repo.create(domain_user)

            assert result is not None
            assert result.id == 1
            assert result.email == "newuser@example.com"
            MockDbUser.assert_called_once()
            mock_db_session.add.assert_called_once_with(mock_db_instance)
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once_with(mock_db_instance)

    def test_create_with_empty_email(self, repo, mock_db_session):
        """Test user creation with empty email (should set to None)."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Domain user with empty email - use artist role since artists don't require email
        domain_user = DomainUser(
            email="", name="New User", role="artist", is_active=True
        )

        with patch("app.repositories.user_repo.DbUser") as MockDbUser:
            mock_db_instance = Mock()
            MockDbUser.return_value = mock_db_instance

            mock_db_session.add.return_value = None
            mock_db_session.commit.return_value = None
            mock_db_session.refresh.return_value = None
            mock_db_instance.id = 1

            result = repo.create(domain_user)

            # Verify that empty email was converted to None
            assert mock_db_instance.email is None
            assert result.id == 1


@pytest.mark.unit
@pytest.mark.repositories
@pytest.mark.user
class TestUserRepositoryUpdates:
    """Test user update operations."""

    def test_update_success(self, repo, mock_db_session):
        """Test successful user update."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Domain user to update
        domain_user = DomainUser(
            id=1,
            email="updated@example.com",
            name="Updated User",
            google_id="google456",
            avatar_url="newavatar.jpg",
            role="client",
            is_active=True,
        )

        # Mock existing database user
        db_user = Mock()
        db_user.id = 1
        db_user.email = "old@example.com"
        db_user.name = "Old User"
        db_user.google_id = "google123"
        db_user.avatar_url = "oldavatar.jpg"
        db_user.role = "client"
        db_user.is_active = True

        # Mock query chain
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = db_user
        mock_db_session.query.return_value = mock_query

        # Mock session operations
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None

        result = repo.update(domain_user)

        assert result is not None
        assert isinstance(result, DomainUser)
        assert result.email == "updated@example.com"
        mock_query.filter_by.assert_called_once_with(id=1)
        mock_db_session.add.assert_called_once_with(db_user)
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once_with(db_user)

    def test_update_user_not_found(self, repo, mock_db_session):
        """Test user update when user doesn't exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        domain_user = DomainUser(
            id=999, email="user@example.com", name="Test User", is_active=True
        )

        # Mock query chain returning None
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        with pytest.raises(ValueError, match="User with ID 999 not found"):
            repo.update(domain_user)

    def test_update_without_id(self, repo, mock_db_session):
        """Test user update without ID."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        domain_user = DomainUser(
            email="user@example.com", name="Test User", is_active=True
        )

        with pytest.raises(ValueError, match="User ID is required for update"):
            repo.update(domain_user)


@pytest.mark.unit
@pytest.mark.repositories
@pytest.mark.user
class TestUserRepositoryDeletion:
    """Test user deletion operations."""

    def test_delete_success(self, repo, mock_db_session):
        """Test successful user deletion."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        user_id = 1

        # Mock existing database user
        db_user = Mock()
        db_user.id = user_id

        # Mock query chain
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = db_user
        mock_db_session.query.return_value = mock_query

        # Mock session operations
        mock_db_session.delete.return_value = None
        mock_db_session.commit.return_value = None

        result = repo.delete(user_id)

        assert result is True
        mock_query.filter_by.assert_called_once_with(id=user_id)
        mock_db_session.delete.assert_called_once_with(db_user)
        mock_db_session.commit.assert_called_once()

    def test_delete_user_not_found(self, repo, mock_db_session):
        """Test user deletion when user doesn't exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        user_id = 999

        # Mock query chain returning None
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        result = repo.delete(user_id)

        assert result is False
        mock_db_session.delete.assert_not_called()
        mock_db_session.commit.assert_not_called()


@pytest.mark.unit
@pytest.mark.repositories
@pytest.mark.user
class TestUserRepositoryPassword:
    """Test password management operations."""

    def test_set_password_success(self, repo, mock_db_session):
        """Test successful password setting."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        user_id = 1
        password_hash = "hashed_password_123"

        # Mock existing database user
        db_user = Mock()
        db_user.id = user_id

        # Mock query chain
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = db_user
        mock_db_session.query.return_value = mock_query

        # Mock session operations
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None

        result = repo.set_password(user_id, password_hash)

        assert result is True
        assert db_user.password_hash == password_hash
        mock_query.filter_by.assert_called_once_with(id=user_id)
        mock_db_session.add.assert_called_once_with(db_user)
        mock_db_session.commit.assert_called_once()

    def test_set_password_user_not_found(self, repo, mock_db_session):
        """Test password setting when user doesn't exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        user_id = 999
        password_hash = "hashed_password_123"

        # Mock query chain returning None
        mock_query = Mock()
        mock_query.filter_by.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        result = repo.set_password(user_id, password_hash)

        assert result is False
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()


@pytest.mark.unit
@pytest.mark.repositories
@pytest.mark.user
class TestUserRepositoryDomainMapping:
    """Test domain entity mapping operations."""

    def test_to_domain_with_null_values(self, repo, mock_db_session):
        """Test domain mapping with NULL database values."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock database user with NULL values
        db_user = Mock()
        db_user.id = 1
        db_user.email = None
        db_user.name = "Test User"
        db_user.google_id = None
        db_user.avatar_url = None
        db_user.role = "artist"
        db_user.is_active = None
        db_user.created_at = None
        db_user.updated_at = None

        result = repo._to_domain(db_user)

        assert isinstance(result, DomainUser)
        assert result.id == 1
        assert result.email == ""  # NULL converted to empty string
        assert result.name == "Test User"
        assert result.google_id is None
        assert result.avatar_url is None
        assert result.role == "artist"
        assert result.is_active is None

    def test_to_domain_with_all_values(self, repo, mock_db_session):
        """Test domain mapping with all database values present."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        from datetime import datetime

        # Mock database user with all values
        db_user = Mock()
        db_user.id = 1
        db_user.email = "user@example.com"
        db_user.name = "Test User"
        db_user.google_id = "google123"
        db_user.avatar_url = "avatar.jpg"
        db_user.role = "artist"
        db_user.is_active = True
        db_user.created_at = datetime(2023, 1, 1)
        db_user.updated_at = datetime(2023, 1, 2)

        result = repo._to_domain(db_user)

        assert isinstance(result, DomainUser)
        assert result.id == 1
        assert result.email == "user@example.com"
        assert result.name == "Test User"
        assert result.google_id == "google123"
        assert result.avatar_url == "avatar.jpg"
        assert result.role == "artist"
        assert result.is_active is True
        assert result.created_at == datetime(2023, 1, 1)
        assert result.updated_at == datetime(2023, 1, 2)
