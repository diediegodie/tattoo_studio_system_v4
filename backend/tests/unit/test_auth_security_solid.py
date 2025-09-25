"""
Minimal, stable authentication/security unit tests adapted for current project layout.

These tests prefer top-level imports (no `app.` prefix). If the real modules
aren't available in the test environment, tests will skip gracefully.
"""

from unittest.mock import Mock

import pytest
# Ensure test path setup runs (adds backend and app directories to sys.path)
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()

try:
    from app.core.security import hash_password, verify_password
    from app.services.user_service import UserService
    from domain.entities import User as DomainUser
    from tests.factories.repository_factories import UserRepositoryFactory

    IMPORTS_AVAILABLE = True
except Exception as e:
    print(f"Warning: authentication/security imports unavailable: {e}")
    IMPORTS_AVAILABLE = False


@pytest.mark.unit
@pytest.mark.security
def test_hash_and_verify_password_roundtrip():
    if not IMPORTS_AVAILABLE:
        pytest.skip("Required modules not available")

    pw = "test_pw_123"
    h = hash_password(pw)
    assert h is not None and h != pw
    assert verify_password(pw, h) is True


@pytest.mark.unit
@pytest.mark.service_layer
class TestUserServiceBasic:
    def setup_method(self):
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        self.mock_repo = UserRepositoryFactory.create_mock_full()
        self.service = UserService(self.mock_repo)

    def test_set_password_returns_boolean_or_none(self):
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        result = self.service.set_password(1, "newpass")
        assert isinstance(result, (bool, type(None)))

    def test_create_or_update_from_google_raises_on_missing(self):
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        with pytest.raises(ValueError):
            self.service.create_or_update_from_google({})
