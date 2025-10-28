"""
Tests for Google Calendar Blueprint (google_calendar)

This test suite validates the calendar authorization flow via Google OAuth
using the google_calendar blueprint, which handles calendar token authorization
separately from user login.
"""

import uuid
from typing import cast
from unittest.mock import Mock, patch
import pytest
from flask import url_for

from app.config.oauth_provider import PROVIDER_GOOGLE_CALENDAR, PROVIDER_GOOGLE_LOGIN
from app.db.base import User as DbUser, OAuth
from tests.conftest import google_calendar_endpoint, google_calendar_session_state_key


class TestGoogleCalendarBlueprint:
    """Test suite for Google Calendar blueprint functionality."""

    def test_google_calendar_blueprint_registered(self, app):
        """Verify google_calendar blueprint is registered with correct URL prefix."""
        with app.test_request_context():
            # Should be able to generate URL for google_calendar.login
            login_url = url_for(google_calendar_endpoint("login"))
            assert login_url is not None
            assert "/auth/calendar/" in login_url or "google_calendar" in login_url

    def test_google_calendar_requires_authenticated_user(self, test_client, app):
        """Test that calendar authorization requires a logged-in user."""
        # Try to access calendar authorization without being logged in
        with app.test_request_context():
            login_url = url_for(google_calendar_endpoint("login"))

        response = test_client.get(login_url, follow_redirects=False)

        # Should redirect to login or return unauthorized
        # Flask-Dance with user_required=True should handle this
        assert response.status_code in [302, 307, 401]

    def test_google_calendar_callback_stores_token_with_correct_provider(
        self, test_client, app, db_session, authenticated_user
    ):
        """Test that calendar callback stores token with provider='google_calendar'."""
        # Create logged-in user
        user = authenticated_user

        google_user_info = {
            "id": user.google_id,
            "email": user.email,
        }

        state_value = f"state-{uuid.uuid4().hex[:6]}"
        token_data = {
            "access_token": "calendar-access-token",
            "refresh_token": "calendar-refresh-token",
            "token_type": "Bearer",
            "expires_at": 1750000000,
        }

        with patch(
            "flask_dance.consumer.oauth2.OAuth2Session.fetch_token"
        ) as mock_fetch, patch(
            "flask_dance.consumer.oauth2.OAuth2Session.get"
        ) as mock_get:

            mock_fetch.return_value = token_data

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = google_user_info
            mock_get.return_value = mock_response

            with app.test_request_context():
                callback_url = url_for(
                    google_calendar_endpoint("authorized"),
                    code="test-code",
                    state=state_value,
                )

            with test_client.session_transaction() as sess:
                sess[google_calendar_session_state_key()] = state_value
                # Simulate logged-in user
                sess["_user_id"] = str(user.id)

            response = test_client.get(callback_url, follow_redirects=False)

            # Should redirect to calendar page
            assert response.status_code in [302, 307]

            # Verify token was stored with correct provider and provider_user_id
            # CRITICAL: Manual storage.set() must persist to database
            db_session.expire_all()  # Refresh from database
            oauth_record = (
                db_session.query(OAuth)
                .filter_by(provider=PROVIDER_GOOGLE_CALENDAR, user_id=user.id)
                .first()
            )

            assert (
                oauth_record is not None
            ), "Calendar token must be stored in database via manual storage.set()"
            assert (
                oauth_record.provider_user_id is not None
            ), "provider_user_id must be set"
            assert (
                oauth_record.provider_user_id == user.google_id
            ), "provider_user_id must match user's Google ID"
            assert oauth_record.token is not None, "Token must be stored"
            assert (
                oauth_record.token["access_token"] == token_data["access_token"]
            ), "Access token must match"
            assert (
                "refresh_token" in oauth_record.token
            ), "Calendar token must include refresh_token"

    def test_google_calendar_callback_without_token_shows_error(
        self, test_client, app, authenticated_user
    ):
        """Test that calendar callback handles missing token gracefully."""
        state_value = f"state-{uuid.uuid4().hex[:6]}"

        with patch(
            "flask_dance.consumer.oauth2.OAuth2Session.fetch_token"
        ) as mock_fetch:
            mock_fetch.return_value = None  # Simulate OAuth error

            with app.test_request_context():
                callback_url = url_for(
                    google_calendar_endpoint("authorized"),
                    code="test-code",
                    state=state_value,
                )

            with test_client.session_transaction() as sess:
                sess[google_calendar_session_state_key()] = state_value
                sess["_user_id"] = str(authenticated_user.id)

            response = test_client.get(callback_url, follow_redirects=True)

            # Should handle error and redirect
            assert response.status_code == 200

    def test_google_calendar_separate_from_login_tokens(
        self, db_session, authenticated_user
    ):
        """Test that calendar tokens are stored separately from login tokens."""
        user = authenticated_user

        # Create a login token
        login_token = OAuth()
        setattr(login_token, "provider", PROVIDER_GOOGLE_LOGIN)
        login_token.user_id = user.id
        setattr(login_token, "provider_user_id", cast(str, user.google_id))
        login_token.token = {
            "access_token": "login-token",
            "token_type": "Bearer",
        }
        db_session.add(login_token)

        # Create a calendar token
        calendar_token = OAuth()
        setattr(calendar_token, "provider", PROVIDER_GOOGLE_CALENDAR)
        calendar_token.user_id = user.id
        setattr(calendar_token, "provider_user_id", cast(str, user.google_id))
        calendar_token.token = {
            "access_token": "calendar-token",
            "refresh_token": "calendar-refresh",
            "token_type": "Bearer",
        }
        db_session.add(calendar_token)
        db_session.commit()

        # Query both types
        login_tokens = (
            db_session.query(OAuth)
            .filter_by(provider=PROVIDER_GOOGLE_LOGIN, user_id=user.id)
            .all()
        )

        calendar_tokens = (
            db_session.query(OAuth)
            .filter_by(provider=PROVIDER_GOOGLE_CALENDAR, user_id=user.id)
            .all()
        )

        # Should have one of each
        assert len(login_tokens) == 1
        assert len(calendar_tokens) == 1

        # Tokens should be different
        assert (
            login_tokens[0].token["access_token"]
            != calendar_tokens[0].token["access_token"]
        )

    def test_google_calendar_redirects_to_calendar_page_after_auth(
        self, test_client, app, db_session, authenticated_user
    ):
        """Test that successful calendar auth redirects back to calendar page."""
        user = authenticated_user

        google_user_info = {
            "id": user.google_id,
            "email": user.email,
        }

        state_value = f"state-{uuid.uuid4().hex[:6]}"
        token_data = {
            "access_token": "calendar-access-token",
            "refresh_token": "calendar-refresh-token",
            "token_type": "Bearer",
            "expires_at": 1750000000,
        }

        with patch(
            "flask_dance.consumer.oauth2.OAuth2Session.fetch_token"
        ) as mock_fetch, patch(
            "flask_dance.consumer.oauth2.OAuth2Session.get"
        ) as mock_get:

            mock_fetch.return_value = token_data

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = google_user_info
            mock_get.return_value = mock_response

            with app.test_request_context():
                callback_url = url_for(
                    google_calendar_endpoint("authorized"),
                    code="test-code",
                    state=state_value,
                )

            with test_client.session_transaction() as sess:
                sess[google_calendar_session_state_key()] = state_value
                sess["_user_id"] = str(user.id)

            response = test_client.get(callback_url, follow_redirects=False)

            # Should redirect
            assert response.status_code in [302, 307]

            # Check redirect location contains calendar
            if response.location:
                assert (
                    "calendar" in response.location.lower() or response.location == "/"
                )


@pytest.fixture
def authenticated_user(db_session):
    """Create and return an authenticated user for tests."""
    user = DbUser()
    user.name = "Test User"
    user.email = f"testuser-{uuid.uuid4().hex[:8]}@example.com"
    user.google_id = f"google-{uuid.uuid4().hex[:8]}"
    user.role = "client"
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
