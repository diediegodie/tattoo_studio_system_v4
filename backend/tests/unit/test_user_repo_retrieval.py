"""
Unit tests for UserRepository retrieval operations.

This module tests user retrieval operations with comprehensive coverage:
- Get by ID operations
- Get by email operations
- Get by Google ID operations
- Error handling and edge cases
"""

from typing import Optional
from unittest.mock import Mock

import pytest
# Test configuration and imports
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()

try:
    from app.db.base import User as DbUser
    from app.domain.entities import User as DomainUser
    from app.repositories.user_repo import UserRepository

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
