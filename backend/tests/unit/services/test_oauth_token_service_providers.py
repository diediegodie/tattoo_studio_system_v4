"""
Unit tests for OAuthTokenService with provider parameter support.

Tests validate that the service correctly handles multiple OAuth providers
(google_login and google_calendar) and manages tokens separately.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import cast
from unittest.mock import Mock, patch

from app.config.oauth_provider import PROVIDER_GOOGLE_LOGIN, PROVIDER_GOOGLE_CALENDAR
from app.db.base import OAuth, User as DbUser
from app.services.oauth_token_service import OAuthTokenService


class TestOAuthTokenServiceWithProviders:
    """Test OAuthTokenService with explicit provider parameters."""

    def test_store_oauth_token_with_google_login_provider(self, db_session):
        """Test storing token with google_login provider."""
        # Create user
        user = DbUser()
        user.name = "Test User"
        user.email = f"user-{uuid.uuid4().hex[:8]}@example.com"
        user.google_id = f"google-{uuid.uuid4().hex[:8]}"
        user.role = "client"
        db_session.add(user)
        db_session.commit()

        # Ensure google_id is set (for type checker)
        google_id = cast(str, user.google_id)

        # Store login token
        service = OAuthTokenService()
        token = {
            "access_token": "login-access-token",
            "token_type": "Bearer",
            "expires_at": 1750000000,
        }

        result = service.store_oauth_token(
            user_id=str(user.id),
            provider=PROVIDER_GOOGLE_LOGIN,
            provider_user_id=google_id,
            token=token,
        )

        assert result is True

        # Verify token in database
        oauth_record = (
            db_session.query(OAuth)
            .filter_by(provider=PROVIDER_GOOGLE_LOGIN, user_id=user.id)
            .first()
        )

        assert oauth_record is not None
        assert oauth_record.token["access_token"] == "login-access-token"

    def test_store_oauth_token_with_google_calendar_provider(self, db_session):
        """Test storing token with google_calendar provider."""
        # Create user
        user = DbUser()
        user.name = "Test User"
        user.email = f"user-{uuid.uuid4().hex[:8]}@example.com"
        user.google_id = f"google-{uuid.uuid4().hex[:8]}"
        user.role = "client"
        db_session.add(user)
        db_session.commit()

        # Store calendar token
        service = OAuthTokenService()
        token = {
            "access_token": "calendar-access-token",
            "refresh_token": "calendar-refresh-token",
            "token_type": "Bearer",
            "expires_at": 1750000000,
        }

        result = service.store_oauth_token(
            user_id=str(user.id),
            provider=PROVIDER_GOOGLE_CALENDAR,
            provider_user_id=cast(str, user.google_id),
            token=token,
        )

        assert result is True

        # Verify token in database
        oauth_record = (
            db_session.query(OAuth)
            .filter_by(provider=PROVIDER_GOOGLE_CALENDAR, user_id=user.id)
            .first()
        )

        assert oauth_record is not None
        assert oauth_record.token["access_token"] == "calendar-access-token"
        assert oauth_record.token["refresh_token"] == "calendar-refresh-token"

    def test_get_user_access_token_with_provider_parameter(self, db_session):
        """Test retrieving token with explicit provider parameter."""
        # Create user
        user = DbUser()
        user.name = "Test User"
        user.email = f"user-{uuid.uuid4().hex[:8]}@example.com"
        user.google_id = f"google-{uuid.uuid4().hex[:8]}"
        user.role = "client"
        db_session.add(user)
        db_session.commit()

        # Store calendar token
        oauth_record = OAuth()
        setattr(oauth_record, "provider", PROVIDER_GOOGLE_CALENDAR)
        oauth_record.user_id = user.id
        setattr(oauth_record, "provider_user_id", cast(str, user.google_id))
        oauth_record.token = {
            "access_token": "test-calendar-token",
            "token_type": "Bearer",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        }
        db_session.add(oauth_record)
        db_session.commit()

        # Retrieve with provider parameter
        service = OAuthTokenService()
        token = service.get_user_access_token(
            str(user.id), provider=PROVIDER_GOOGLE_CALENDAR
        )

        assert token == "test-calendar-token"

    def test_get_user_access_token_defaults_to_calendar_provider(self, db_session):
        """Test that get_user_access_token defaults to google_calendar provider."""
        # Create user
        user = DbUser()
        user.name = "Test User"
        user.email = f"user-{uuid.uuid4().hex[:8]}@example.com"
        user.google_id = f"google-{uuid.uuid4().hex[:8]}"
        user.role = "client"
        db_session.add(user)
        db_session.commit()

        # Store calendar token
        oauth_record = OAuth()
        setattr(oauth_record, "provider", PROVIDER_GOOGLE_CALENDAR)
        oauth_record.user_id = user.id
        setattr(oauth_record, "provider_user_id", cast(str, user.google_id))
        oauth_record.token = {
            "access_token": "default-calendar-token",
            "token_type": "Bearer",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        }
        db_session.add(oauth_record)
        db_session.commit()

        # Call without provider parameter (should default to calendar)
        service = OAuthTokenService()
        token = service.get_user_access_token(str(user.id))

        assert token == "default-calendar-token"

    def test_separate_tokens_for_different_providers(self, db_session):
        """Test that login and calendar tokens are stored separately."""
        # Create user
        user = DbUser()
        user.name = "Test User"
        user.email = f"user-{uuid.uuid4().hex[:8]}@example.com"
        user.google_id = f"google-{uuid.uuid4().hex[:8]}"
        user.role = "client"
        db_session.add(user)
        db_session.commit()

        service = OAuthTokenService()

        # Store login token
        login_token = {
            "access_token": "login-token",
            "token_type": "Bearer",
        }
        service.store_oauth_token(
            user_id=str(user.id),
            provider=PROVIDER_GOOGLE_LOGIN,
            provider_user_id=cast(str, user.google_id),
            token=login_token,
        )

        # Store calendar token
        calendar_token = {
            "access_token": "calendar-token",
            "refresh_token": "calendar-refresh",
            "token_type": "Bearer",
        }
        service.store_oauth_token(
            user_id=str(user.id),
            provider=PROVIDER_GOOGLE_CALENDAR,
            provider_user_id=cast(str, user.google_id),
            token=calendar_token,
        )

        # Verify both exist separately
        login_record = (
            db_session.query(OAuth)
            .filter_by(provider=PROVIDER_GOOGLE_LOGIN, user_id=user.id)
            .first()
        )

        calendar_record = (
            db_session.query(OAuth)
            .filter_by(provider=PROVIDER_GOOGLE_CALENDAR, user_id=user.id)
            .first()
        )

        assert login_record is not None
        assert calendar_record is not None
        assert (
            login_record.token["access_token"] != calendar_record.token["access_token"]
        )

    def test_refresh_access_token_with_provider(self, db_session, app):
        """Test token refresh with explicit provider parameter."""
        # Create user
        user = DbUser()
        user.name = "Test User"
        user.email = f"user-{uuid.uuid4().hex[:8]}@example.com"
        user.google_id = f"google-{uuid.uuid4().hex[:8]}"
        user.role = "client"
        db_session.add(user)
        db_session.commit()

        # Store expired calendar token
        oauth_record = OAuth()
        setattr(oauth_record, "provider", PROVIDER_GOOGLE_CALENDAR)
        oauth_record.user_id = user.id
        setattr(oauth_record, "provider_user_id", cast(str, user.google_id))
        oauth_record.token = {
            "access_token": "old-token",
            "refresh_token": "refresh-token",
            "token_type": "Bearer",
            "expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp(),
        }
        db_session.add(oauth_record)
        db_session.commit()

        # Mock refresh response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-token",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

        with patch("requests.post", return_value=mock_response):
            with app.app_context():
                service = OAuthTokenService()
                new_token = service.refresh_access_token(
                    str(user.id), provider=PROVIDER_GOOGLE_CALENDAR
                )

        assert new_token == "new-token"

    def test_is_token_valid_with_provider(self, db_session):
        """Test token validation with provider parameter."""
        # Create user
        user = DbUser()
        user.name = "Test User"
        user.email = f"user-{uuid.uuid4().hex[:8]}@example.com"
        user.google_id = f"google-{uuid.uuid4().hex[:8]}"
        user.role = "client"
        db_session.add(user)
        db_session.commit()

        # Store valid calendar token
        oauth_record = OAuth()
        setattr(oauth_record, "provider", PROVIDER_GOOGLE_CALENDAR)
        oauth_record.user_id = user.id
        setattr(oauth_record, "provider_user_id", cast(str, user.google_id))
        oauth_record.token = {
            "access_token": "valid-token",
            "token_type": "Bearer",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        }
        db_session.add(oauth_record)
        db_session.commit()

        # Mock API validation
        mock_response = Mock()
        mock_response.status_code = 200

        with patch("requests.get", return_value=mock_response):
            service = OAuthTokenService()
            is_valid = service.is_token_valid(
                str(user.id), provider=PROVIDER_GOOGLE_CALENDAR
            )

        assert is_valid is True

    def test_revoke_user_token_with_provider(self, db_session):
        """Test token revocation with provider parameter."""
        # Create user
        user = DbUser()
        user.name = "Test User"
        user.email = f"user-{uuid.uuid4().hex[:8]}@example.com"
        user.google_id = f"google-{uuid.uuid4().hex[:8]}"
        user.role = "client"
        db_session.add(user)
        db_session.commit()

        # Store calendar token
        oauth_record = OAuth()
        setattr(oauth_record, "provider", PROVIDER_GOOGLE_CALENDAR)
        oauth_record.user_id = user.id
        setattr(oauth_record, "provider_user_id", cast(str, user.google_id))
        oauth_record.token = {
            "access_token": "token-to-revoke",
            "token_type": "Bearer",
        }
        db_session.add(oauth_record)
        db_session.commit()

        # Mock revocation response
        mock_response = Mock()
        mock_response.status_code = 200

        with patch("requests.post", return_value=mock_response):
            service = OAuthTokenService()
            result = service.revoke_user_token(
                str(user.id), provider=PROVIDER_GOOGLE_CALENDAR
            )

        assert result is True

        # Verify token was deleted
        oauth_record = (
            db_session.query(OAuth)
            .filter_by(provider=PROVIDER_GOOGLE_CALENDAR, user_id=user.id)
            .first()
        )

        assert oauth_record is None
