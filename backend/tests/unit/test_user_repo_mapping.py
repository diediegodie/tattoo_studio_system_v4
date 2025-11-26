"""
Unit tests for UserRepository domain mapping operations.

This module tests domain entity mapping operations with comprehensive coverage:
- Mapping with NULL database values
- Mapping with all database values present
- Error handling and edge cases
"""

from datetime import datetime
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
