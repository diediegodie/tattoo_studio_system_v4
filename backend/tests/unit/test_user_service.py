"""
Unit tests for UserService following SOLID principles and existing test patterns.

This module tests the UserService business logic with comprehensive coverage:
- Google OAuth user creation/update
- Local authentication
- User management operations
- Artist registration
- Error handling and edge cases
"""

from typing import Dict, Optional
from unittest.mock import Mock, patch

import pytest

# Test configuration and imports
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()

try:
    from app.core.security import hash_password, verify_password
    from app.domain.entities import User as DomainUser
    from app.services.user_service import UserService
    from tests.factories.repository_factories import UserRepositoryFactory

    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    IMPORTS_AVAILABLE = False


@pytest.fixture
def mock_repo() -> Mock:
    """Create a mock user repository implementing the interface."""
    return UserRepositoryFactory.create_mock_full()


@pytest.fixture
def service(mock_repo) -> Optional["UserService"]:
    """Initialize UserService with mocked repository."""
    if not IMPORTS_AVAILABLE:
        return None
    return UserService(mock_repo)


from .test_user_service_artist import *
from .test_user_service_auth import *

# Import from split modules
from .test_user_service_google_oauth import *
from .test_user_service_management import *
from .test_user_service_password import *
from .test_user_service_retrieval import *
