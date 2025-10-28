"""
Unit tests for CustomOAuthStorage

Tests validate:
- provider_user_id fetching from Google API
- Fallback path when API fails
- Manual storage.set() calls
- Database persistence with all required fields
"""

import uuid
from unittest.mock import Mock, patch, MagicMock
import pytest

from app.core.custom_oauth_storage import CustomOAuthStorage
from app.config.oauth_provider import PROVIDER_GOOGLE_LOGIN, PROVIDER_GOOGLE_CALENDAR
from app.db.base import OAuth, User as DbUser


class TestCustomOAuthStorage:
    """Test suite for CustomOAuthStorage class."""

    @pytest.fixture
    def mock_blueprint(self):
        """Create a mock Flask-Dance blueprint."""
        blueprint = Mock()
        blueprint.name = PROVIDER_GOOGLE_CALENDAR
        blueprint.session = Mock()
        blueprint.config = {}
        return blueprint

    @pytest.fixture
    def mock_user(self, db_session):
        """Create a test user in database."""
        user = DbUser()
        user.name = "Test User"
        user.email = f"test-{uuid.uuid4().hex[:8]}@example.com"
        user.google_id = f"google-{uuid.uuid4().hex[:8]}"
        user.role = "client"
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    @pytest.fixture
    def storage(self, db_session):
        """Create CustomOAuthStorage instance."""
        return CustomOAuthStorage(
            model=OAuth,
            session=db_session,
            user_required=False,
        )

    def test_successful_provider_user_id_fetch(
        self, storage, mock_blueprint, mock_user
    ):
        """Test successful fetch of provider_user_id from Google API."""
        # Mock Google API response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": mock_user.google_id,
            "email": mock_user.email,
        }
        mock_blueprint.session.get.return_value = mock_response

        # Fetch provider_user_id
        provider_user_id = storage._fetch_provider_user_id(mock_blueprint)

        # Verify
        assert provider_user_id == mock_user.google_id
        mock_blueprint.session.get.assert_called_once_with("/oauth2/v2/userinfo")

    def test_fallback_when_google_api_fails(self, storage, mock_blueprint):
        """Test fallback path when Google API returns error."""
        # Mock Google API error response
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_blueprint.session.get.return_value = mock_response

        # Fetch provider_user_id with fallback
        provider_user_id = storage._fetch_provider_user_id(
            mock_blueprint, fallback_user_id="fallback-123"
        )

        # Should return None (caller handles fallback)
        assert provider_user_id is None

    def test_fallback_when_google_api_returns_malformed_json(
        self, storage, mock_blueprint
    ):
        """Test fallback when Google API returns JSON without 'id' field."""
        # Mock Google API response without 'id'
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"email": "test@example.com"}  # Missing 'id'
        mock_blueprint.session.get.return_value = mock_response

        # Fetch provider_user_id
        provider_user_id = storage._fetch_provider_user_id(mock_blueprint)

        # Should return None
        assert provider_user_id is None

    def test_fallback_when_google_api_raises_exception(self, storage, mock_blueprint):
        """Test fallback when Google API call raises exception."""
        # Mock Google API exception
        mock_blueprint.session.get.side_effect = Exception("Network error")

        # Fetch provider_user_id
        provider_user_id = storage._fetch_provider_user_id(mock_blueprint)

        # Should return None and not raise
        assert provider_user_id is None

    def test_storage_set_creates_database_record(
        self, storage, mock_blueprint, mock_user, db_session
    ):
        """Test that storage.set() creates OAuth record in database."""
        # Mock Google API response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"id": mock_user.google_id}
        mock_blueprint.session.get.return_value = mock_response

        # Token to store
        token = {
            "access_token": "test-token-123",
            "refresh_token": "refresh-token-123",
            "token_type": "Bearer",
            "expires_at": 1750000000,
        }

        # Call storage.set()
        storage.set(
            blueprint=mock_blueprint,
            token=token,
            user=mock_user,
            user_id=mock_user.id,
        )

        # Verify database record was created
        oauth_record = (
            db_session.query(OAuth)
            .filter_by(provider=PROVIDER_GOOGLE_CALENDAR, user_id=mock_user.id)
            .first()
        )

        assert oauth_record is not None, "OAuth record must be created in database"
        assert (
            oauth_record.provider_user_id == mock_user.google_id
        ), "Must have provider_user_id"
        assert oauth_record.token["access_token"] == "test-token-123"
        assert oauth_record.token["refresh_token"] == "refresh-token-123"

    def test_storage_set_with_fallback_provider_user_id(
        self, storage, mock_blueprint, mock_user, db_session
    ):
        """Test that storage.set() uses fallback when API fails."""
        # Mock Google API failure
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_blueprint.session.get.return_value = mock_response

        # Token to store
        token = {
            "access_token": "test-token-456",
            "token_type": "Bearer",
        }

        # Call storage.set() - should use fallback
        storage.set(
            blueprint=mock_blueprint,
            token=token,
            user=mock_user,
            user_id=mock_user.id,
        )

        # Verify database record was created with fallback provider_user_id
        oauth_record = (
            db_session.query(OAuth)
            .filter_by(provider=PROVIDER_GOOGLE_CALENDAR, user_id=mock_user.id)
            .first()
        )

        assert (
            oauth_record is not None
        ), "OAuth record must be created even with API failure"
        assert oauth_record.provider_user_id.startswith(
            "unknown_"
        ), "Should use fallback"
        assert oauth_record.token["access_token"] == "test-token-456"

    def test_storage_set_updates_existing_record(
        self, storage, mock_blueprint, mock_user, db_session
    ):
        """Test that storage.set() updates existing OAuth record."""
        # Mock Google API
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"id": mock_user.google_id}
        mock_blueprint.session.get.return_value = mock_response

        # Create initial record
        initial_token = {"access_token": "old-token"}
        storage.set(
            blueprint=mock_blueprint,
            token=initial_token,
            user=mock_user,
            user_id=mock_user.id,
        )

        # Update with new token
        new_token = {"access_token": "new-token", "refresh_token": "new-refresh"}
        storage.set(
            blueprint=mock_blueprint,
            token=new_token,
            user=mock_user,
            user_id=mock_user.id,
        )

        # Verify only one record exists with updated token
        oauth_records = (
            db_session.query(OAuth)
            .filter_by(provider=PROVIDER_GOOGLE_CALENDAR, user_id=mock_user.id)
            .all()
        )

        assert (
            len(oauth_records) == 1
        ), "Should have exactly one record (updated, not duplicated)"
        assert oauth_records[0].token["access_token"] == "new-token"
        assert oauth_records[0].token["refresh_token"] == "new-refresh"

    def test_get_user_id_from_various_sources(self, storage, mock_blueprint, mock_user):
        """Test _get_user_id() extracts user ID from various sources."""
        # Test 1: Explicit user_id parameter
        user_id = storage._get_user_id(user=None, user_id=123, blueprint=mock_blueprint)
        assert user_id == 123

        # Test 2: User object with .id attribute
        user_id = storage._get_user_id(
            user=mock_user, user_id=None, blueprint=mock_blueprint
        )
        assert user_id == mock_user.id

        # Test 3: User object with .get_id() method
        mock_flask_user = Mock()
        mock_flask_user.get_id.return_value = "456"
        user_id = storage._get_user_id(
            user=mock_flask_user, user_id=None, blueprint=mock_blueprint
        )
        assert user_id == 456

    def test_storage_respects_user_required_setting(self, db_session, mock_blueprint):
        """Test that user_required=True prevents storage without user."""
        # Create storage with user_required=True
        storage = CustomOAuthStorage(
            model=OAuth,
            session=db_session,
            user_required=True,
        )

        # Mock Google API
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"id": "google-123"}
        mock_blueprint.session.get.return_value = mock_response

        token = {"access_token": "test-token"}

        # Should raise ValueError when no user provided
        with pytest.raises(
            ValueError, match="Cannot set OAuth token without an associated user"
        ):
            storage.set(blueprint=mock_blueprint, token=token, user=None, user_id=None)

    def test_storage_works_for_both_login_and_calendar_providers(
        self, storage, mock_user, db_session
    ):
        """Test that CustomOAuthStorage works for both google_login and google_calendar."""
        # Mock Google API
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"id": mock_user.google_id}

        # Test google_login provider
        login_blueprint = Mock()
        login_blueprint.name = PROVIDER_GOOGLE_LOGIN
        login_blueprint.session = Mock()
        login_blueprint.session.get.return_value = mock_response
        login_blueprint.config = {}

        login_token = {"access_token": "login-token"}
        storage.set(
            blueprint=login_blueprint,
            token=login_token,
            user=mock_user,
            user_id=mock_user.id,
        )

        # Test google_calendar provider
        calendar_blueprint = Mock()
        calendar_blueprint.name = PROVIDER_GOOGLE_CALENDAR
        calendar_blueprint.session = Mock()
        calendar_blueprint.session.get.return_value = mock_response
        calendar_blueprint.config = {}

        calendar_token = {"access_token": "calendar-token", "refresh_token": "refresh"}
        storage.set(
            blueprint=calendar_blueprint,
            token=calendar_token,
            user=mock_user,
            user_id=mock_user.id,
        )

        # Verify both records exist
        login_record = (
            db_session.query(OAuth)
            .filter_by(provider=PROVIDER_GOOGLE_LOGIN, user_id=mock_user.id)
            .first()
        )
        calendar_record = (
            db_session.query(OAuth)
            .filter_by(provider=PROVIDER_GOOGLE_CALENDAR, user_id=mock_user.id)
            .first()
        )

        assert login_record is not None
        assert calendar_record is not None
        assert login_record.provider_user_id == mock_user.google_id
        assert calendar_record.provider_user_id == mock_user.google_id
        assert login_record.token["access_token"] == "login-token"
        assert calendar_record.token["access_token"] == "calendar-token"
