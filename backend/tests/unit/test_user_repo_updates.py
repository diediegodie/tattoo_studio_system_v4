"""
Unit tests for UserRepository update operations.

This module tests user update operations with comprehensive coverage:
- Successful user updates
- Update when user not found
- Update without ID validation
- Error handling and edge cases
"""

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
