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
def repo(mock_db_session) -> Optional["UserRepository"]:
    """Initialize UserRepository with mocked database session."""
    if not IMPORTS_AVAILABLE:
        return None
    return UserRepository(mock_db_session)


# Import from split modules
from .test_user_repo_retrieval import *
from .test_user_repo_creation import *
from .test_user_repo_updates import *
from .test_user_repo_deletion import *
from .test_user_repo_password import *
from .test_user_repo_mapping import *
