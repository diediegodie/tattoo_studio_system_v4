"""
Tests for Google Login Blueprint (google_login)

This test suite validates the user authentication flow via Google OAuth
using the google_login blueprint, which handles user login only
(no calendar authorization).
"""

import uuid
from unittest.mock import Mock, patch
import os
import pytest
from flask import url_for, session

from app.config.oauth_provider import PROVIDER_GOOGLE_LOGIN
from app.db.base import User as DbUser, OAuth
from tests.conftest import google_login_endpoint, google_login_session_state_key


class TestGoogleLoginBlueprint:
    """Test suite for Google Login blueprint functionality."""

    @pytest.fixture(autouse=True)
    def mock_authorized_emails(self):
        """Allow test emails for OAuth login in unit tests."""
        with patch.dict(
            "os.environ",
            {"AUTHORIZED_EMAILS": "newuser@example.com,user@example.com"},
        ):
            import app.core.config

            app.core.config.AUTHORIZED_EMAILS = (
                app.core.config.get_authorized_emails()
            )
            yield
            app.core.config.AUTHORIZED_EMAILS = set()

    def test_google_login_blueprint_registered(self, app):
        """Verify google_login blueprint is registered with correct URL prefix."""
        with app.test_request_context():
            # Should be able to generate URL for google_login.login
            login_url = url_for(google_login_endpoint("login"))
            assert login_url is not None
            assert "/auth/" in login_url or "google_login" in login_url

    def test_google_login_initiates_oauth_flow(self, test_client, app):
        """Test that clicking login redirects to Google OAuth."""
        with patch(
            "flask_dance.consumer.oauth2.OAuth2Session.authorization_url"
        ) as mock_auth:
            mock_auth.return_value = (
                "https://accounts.google.com/o/oauth2/auth",
                "test-state",
            )

            with app.test_request_context():
                login_url = url_for(google_login_endpoint("login"))

            response = test_client.get(login_url)

            # Should redirect to Google
            assert response.status_code in [302, 307]

    def test_google_login_callback_creates_user(self, test_client, app, db_session):
        """Test that successful Google login creates a new user."""
        google_user_info = {
            "id": f"google-{uuid.uuid4().hex[:8]}",
            "email": "newuser@example.com",
            "name": "New Test User",
            "given_name": "New",
            "family_name": "User",
        }

        state_value = f"state-{uuid.uuid4().hex[:6]}"
        token_data = {
            "access_token": "test-access-token",
            "token_type": "Bearer",
            "expires_at": 1750000000,
        }

        with patch(
            "flask_dance.consumer.oauth2.OAuth2Session.fetch_token"
        ) as mock_fetch, patch(
            "flask_dance.consumer.oauth2.OAuth2Session.get"
        ) as mock_get, patch(
            "app.core.security.create_user_token", return_value="test-jwt"
        ):

            mock_fetch.return_value = token_data

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = google_user_info
            mock_get.return_value = mock_response

            with app.test_request_context():
                callback_url = url_for(
                    google_login_endpoint("authorized"),
                    code="test-code",
                    state=state_value,
                )

            # Set session state for OAuth flow
            with test_client.session_transaction() as sess:
                sess[google_login_session_state_key()] = state_value

            response = test_client.get(callback_url, follow_redirects=False)

            # Should redirect to index after successful login
            assert response.status_code in [302, 307]

            # Verify user was created
            user = (
                db_session.query(DbUser).filter_by(email="newuser@example.com").first()
            )
            assert user is not None
            assert user.name == "New Test User"
            assert user.google_id == google_user_info["id"]

    def test_google_login_callback_updates_existing_user(
        self, test_client, app, db_session
    ):
        """Test that login updates existing user information."""
        google_id = f"google-{uuid.uuid4().hex[:8]}"

        # Create existing user
        existing_user = DbUser()
        existing_user.name = "Old Name"
        existing_user.email = "user@example.com"
        existing_user.google_id = google_id
        existing_user.role = "client"
        db_session.add(existing_user)
        db_session.commit()
        user_id = existing_user.id

        google_user_info = {
            "id": google_id,
            "email": "user@example.com",
            "name": "Updated Name",
            "given_name": "Updated",
            "family_name": "Name",
        }

        state_value = f"state-{uuid.uuid4().hex[:6]}"
        token_data = {
            "access_token": "test-access-token",
            "token_type": "Bearer",
            "expires_at": 1750000000,
        }

        with patch(
            "flask_dance.consumer.oauth2.OAuth2Session.fetch_token"
        ) as mock_fetch, patch(
            "flask_dance.consumer.oauth2.OAuth2Session.get"
        ) as mock_get, patch(
            "app.core.security.create_user_token", return_value="test-jwt"
        ):

            mock_fetch.return_value = token_data

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = google_user_info
            mock_get.return_value = mock_response

            with app.test_request_context():
                callback_url = url_for(
                    google_login_endpoint("authorized"),
                    code="test-code",
                    state=state_value,
                )

            with test_client.session_transaction() as sess:
                sess[google_login_session_state_key()] = state_value

            response = test_client.get(callback_url, follow_redirects=False)

            assert response.status_code in [302, 307]

            # Verify user was updated
            db_session.expire_all()
            user = db_session.query(DbUser).filter_by(id=user_id).first()
            assert user is not None
            assert user.name == "Updated Name"

    def test_google_login_does_not_create_calendar_token(
        self, test_client, app, db_session
    ):
        """Test that google_login does NOT create calendar tokens."""
        google_user_info = {
            "id": f"google-{uuid.uuid4().hex[:8]}",
            "email": "user@example.com",
            "name": "Test User",
        }

        state_value = f"state-{uuid.uuid4().hex[:6]}"
        token_data = {
            "access_token": "test-access-token",
            "token_type": "Bearer",
        }

        with patch(
            "flask_dance.consumer.oauth2.OAuth2Session.fetch_token"
        ) as mock_fetch, patch(
            "flask_dance.consumer.oauth2.OAuth2Session.get"
        ) as mock_get, patch(
            "app.core.security.create_user_token", return_value="test-jwt"
        ):

            mock_fetch.return_value = token_data

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = google_user_info
            mock_get.return_value = mock_response

            with app.test_request_context():
                callback_url = url_for(
                    google_login_endpoint("authorized"),
                    code="test-code",
                    state=state_value,
                )

            with test_client.session_transaction() as sess:
                sess[google_login_session_state_key()] = state_value

            response = test_client.get(callback_url, follow_redirects=False)

            # OAuth tokens are stored by manual storage.set() calls
            # CRITICAL: Verify the token was persisted with provider_user_id
            db_session.expire_all()  # Refresh from database
            oauth_records = (
                db_session.query(OAuth).filter_by(provider=PROVIDER_GOOGLE_LOGIN).all()
            )

            # There should be exactly one login token (stored by manual storage.set())
            assert len(oauth_records) == 1, "Exactly one login token must be stored"

            login_token = oauth_records[0]
            assert (
                login_token.provider_user_id is not None
            ), "provider_user_id must be set"
            assert login_token.token is not None, "Token must be stored"
            assert (
                "access_token" in login_token.token
            ), "Token must contain access_token"

            # There should be NO calendar tokens
            from app.config.oauth_provider import PROVIDER_GOOGLE_CALENDAR

            calendar_records = (
                db_session.query(OAuth)
                .filter_by(provider=PROVIDER_GOOGLE_CALENDAR)
                .all()
            )
            assert len(calendar_records) == 0

    def test_google_login_handles_oauth_error(self, test_client, app):
        """Test that login handles OAuth errors gracefully."""
        state_value = f"state-{uuid.uuid4().hex[:6]}"

        with patch(
            "flask_dance.consumer.oauth2.OAuth2Session.fetch_token"
        ) as mock_fetch:
            mock_fetch.return_value = None  # Simulate OAuth error

            with app.test_request_context():
                callback_url = url_for(
                    google_login_endpoint("authorized"),
                    code="test-code",
                    state=state_value,
                )

            with test_client.session_transaction() as sess:
                sess[google_login_session_state_key()] = state_value

            response = test_client.get(callback_url, follow_redirects=True)

            # Should redirect back to login with error message
            assert response.status_code == 200
            # Response should contain login page or error message

    def test_google_login_handles_userinfo_error(self, test_client, app, db_session):
        """Test that login handles Google userinfo API errors."""
        state_value = f"state-{uuid.uuid4().hex[:6]}"
        token_data = {
            "access_token": "test-access-token",
            "token_type": "Bearer",
        }

        with patch(
            "flask_dance.consumer.oauth2.OAuth2Session.fetch_token"
        ) as mock_fetch, patch(
            "flask_dance.consumer.oauth2.OAuth2Session.get"
        ) as mock_get:

            mock_fetch.return_value = token_data

            mock_response = Mock()
            mock_response.ok = False  # Simulate API error
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            with app.test_request_context():
                callback_url = url_for(
                    google_login_endpoint("authorized"),
                    code="test-code",
                    state=state_value,
                )

            with test_client.session_transaction() as sess:
                sess[google_login_session_state_key()] = state_value

            response = test_client.get(callback_url, follow_redirects=True)

            # Should handle error gracefully
            assert response.status_code == 200
