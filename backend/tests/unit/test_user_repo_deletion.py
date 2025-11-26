"""
Unit tests for UserRepository deletion operations.

This module tests user deletion operations with comprehensive coverage:
- Successful user deletion
- Deletion when user not found
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
