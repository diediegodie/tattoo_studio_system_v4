"""
Unit tests for UserRepository password operations.

This module tests password management operations with comprehensive coverage:
- Successful password setting
- Password setting when user not found
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
