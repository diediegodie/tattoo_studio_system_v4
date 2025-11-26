"""
Unit tests for UserRepository creation operations.

This module tests user creation operations with comprehensive coverage:
- Successful user creation
- Creation with empty email handling
- Error handling and edge cases
"""

from unittest.mock import Mock, patch

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
