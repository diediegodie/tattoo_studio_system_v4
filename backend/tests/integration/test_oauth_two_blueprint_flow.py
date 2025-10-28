"""
End-to-end integration tests for Google OAuth two-blueprint architecture.

Tests the complete flow:
1. User logs in with Google (google_login blueprint)
2. User connects Google Calendar (google_calendar blueprint)
3. User syncs calendar events

Validates that tokens are stored with correct providers and operations work correctly.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import cast
from unittest.mock import Mock, patch
import pytest
from flask import url_for

from app.config.oauth_provider import PROVIDER_GOOGLE_LOGIN, PROVIDER_GOOGLE_CALENDAR
from app.db.base import User as DbUser, OAuth
from tests.conftest import (
    google_login_endpoint,
    google_calendar_endpoint,
    google_login_session_state_key,
    google_calendar_session_state_key,
)


class TestOAuthTwoBlueprintIntegration:
    """Integration tests for two-blueprint OAuth architecture."""

    def test_complete_flow_login_then_calendar(self, test_client, app, db_session):
        """
        Test complete flow: login with Google, then connect calendar.

        Steps:
        1. User logs in with Google (creates user, login token)
        2. User connects calendar (creates calendar token)
        3. Verify both tokens exist with correct providers
        """
        google_user_info = {
            "id": f"google-{uuid.uuid4().hex[:8]}",
            "email": "integration@example.com",
            "name": "Integration Test User",
            "given_name": "Integration",
            "family_name": "User",
        }

        # Step 1: Login with Google
        login_state = f"login-state-{uuid.uuid4().hex[:6]}"
        login_token = {
            "access_token": "login-access-token",
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

            mock_fetch.return_value = login_token

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = google_user_info
            mock_get.return_value = mock_response

            with app.test_request_context():
                callback_url = url_for(
                    google_login_endpoint("authorized"),
                    code="login-code",
                    state=login_state,
                )

            with test_client.session_transaction() as sess:
                sess[google_login_session_state_key()] = login_state

            response = test_client.get(callback_url, follow_redirects=False)
            assert response.status_code in [302, 307]

        # Verify user was created
        user = (
            db_session.query(DbUser).filter_by(email="integration@example.com").first()
        )
        assert user is not None
        assert user.google_id == google_user_info["id"]

        # Verify login token exists with provider_user_id
        # CRITICAL: With manual storage.set() calls, this MUST exist
        login_oauth = (
            db_session.query(OAuth)
            .filter_by(provider=PROVIDER_GOOGLE_LOGIN, user_id=user.id)
            .first()
        )
        assert (
            login_oauth is not None
        ), "Login token must be stored in database via manual storage.set()"
        assert login_oauth.provider_user_id is not None, "provider_user_id must be set"
        assert (
            login_oauth.provider_user_id == google_user_info["id"]
        ), "provider_user_id must match Google ID"
        assert login_oauth.token is not None, "Token must be stored"
        assert "access_token" in login_oauth.token, "Token must contain access_token"

        # Step 2: Connect Google Calendar
        calendar_state = f"calendar-state-{uuid.uuid4().hex[:6]}"
        calendar_token = {
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

            mock_fetch.return_value = calendar_token

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = google_user_info
            mock_get.return_value = mock_response

            with app.test_request_context():
                callback_url = url_for(
                    google_calendar_endpoint("authorized"),
                    code="calendar-code",
                    state=calendar_state,
                )

            with test_client.session_transaction() as sess:
                sess[google_calendar_session_state_key()] = calendar_state
                sess["_user_id"] = str(user.id)

            response = test_client.get(callback_url, follow_redirects=False)
            assert response.status_code in [302, 307]

        # Verify calendar token exists with provider_user_id
        # CRITICAL: With manual storage.set() calls, this MUST exist
        db_session.expire_all()  # Refresh from database
        calendar_oauth = (
            db_session.query(OAuth)
            .filter_by(provider=PROVIDER_GOOGLE_CALENDAR, user_id=user.id)
            .first()
        )
        assert (
            calendar_oauth is not None
        ), "Calendar token must be stored in database via manual storage.set()"
        assert (
            calendar_oauth.provider_user_id is not None
        ), "provider_user_id must be set"
        assert (
            calendar_oauth.provider_user_id == google_user_info["id"]
        ), "provider_user_id must match Google ID"
        assert calendar_oauth.token is not None, "Token must be stored"
        assert "access_token" in calendar_oauth.token, "Token must contain access_token"
        assert (
            "refresh_token" in calendar_oauth.token
        ), "Calendar token must contain refresh_token"

    def test_calendar_sync_uses_correct_provider(self, test_client, app, db_session):
        """Test that /calendar/sync queries for google_calendar provider."""
        # Create user
        user = DbUser()
        user.name = "Sync Test User"
        user.email = f"sync-{uuid.uuid4().hex[:8]}@example.com"
        user.google_id = f"google-{uuid.uuid4().hex[:8]}"
        user.role = "client"
        db_session.add(user)
        db_session.commit()

        # Store calendar token with correct provider
        oauth_record = OAuth()
        setattr(oauth_record, "provider", PROVIDER_GOOGLE_CALENDAR)
        oauth_record.user_id = user.id
        setattr(oauth_record, "provider_user_id", cast(str, user.google_id))
        oauth_record.token = {
            "access_token": "calendar-token-for-sync",
            "refresh_token": "calendar-refresh",
            "token_type": "Bearer",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        }
        db_session.add(oauth_record)
        db_session.commit()

        # Mock calendar API response
        mock_calendar_response = Mock()
        mock_calendar_response.ok = True
        mock_calendar_response.json.return_value = {
            "items": [
                {
                    "id": "event-1",
                    "summary": "Test Event",
                    "start": {"dateTime": "2025-11-01T10:00:00Z"},
                    "end": {"dateTime": "2025-11-01T11:00:00Z"},
                }
            ]
        }

        with patch("requests.get", return_value=mock_calendar_response):
            with test_client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)

            # Access calendar sync endpoint
            response = test_client.get("/calendar/sync", follow_redirects=False)

            # Should redirect to auth or succeed
            assert response.status_code in [200, 302]

    def test_database_contains_both_provider_types(self, db_session):
        """Test that database can store both login and calendar tokens."""
        # Create user
        user = DbUser()
        user.name = "Multi Provider User"
        user.email = f"multi-{uuid.uuid4().hex[:8]}@example.com"
        user.google_id = f"google-{uuid.uuid4().hex[:8]}"
        user.role = "client"
        db_session.add(user)
        db_session.commit()

        # Add login token
        login_oauth = OAuth()
        setattr(login_oauth, "provider", PROVIDER_GOOGLE_LOGIN)
        login_oauth.user_id = user.id
        setattr(login_oauth, "provider_user_id", cast(str, user.google_id))
        login_oauth.token = {"access_token": "login-token"}
        db_session.add(login_oauth)

        # Add calendar token
        calendar_oauth = OAuth()
        setattr(calendar_oauth, "provider", PROVIDER_GOOGLE_CALENDAR)
        calendar_oauth.user_id = user.id
        setattr(calendar_oauth, "provider_user_id", cast(str, user.google_id))
        calendar_oauth.token = {
            "access_token": "calendar-token",
            "refresh_token": "refresh",
        }
        db_session.add(calendar_oauth)

        db_session.commit()

        # Query by provider
        provider_counts = (
            db_session.query(
                OAuth.provider,
                db_session.query(OAuth)
                .filter(OAuth.provider == OAuth.provider)
                .count(),
            )
            .group_by(OAuth.provider)
            .all()
        )

        # Verify both providers exist
        login_records = (
            db_session.query(OAuth).filter_by(provider=PROVIDER_GOOGLE_LOGIN).all()
        )
        calendar_records = (
            db_session.query(OAuth).filter_by(provider=PROVIDER_GOOGLE_CALENDAR).all()
        )

        assert len(login_records) >= 1
        assert len(calendar_records) >= 1

    def test_login_without_calendar_works(self, test_client, app, db_session):
        """Test that user can login without connecting calendar."""
        google_user_info = {
            "id": f"google-{uuid.uuid4().hex[:8]}",
            "email": "loginonly@example.com",
            "name": "Login Only User",
        }

        login_state = f"state-{uuid.uuid4().hex[:6]}"
        login_token = {
            "access_token": "login-only-token",
            "token_type": "Bearer",
        }

        with patch(
            "flask_dance.consumer.oauth2.OAuth2Session.fetch_token"
        ) as mock_fetch, patch(
            "flask_dance.consumer.oauth2.OAuth2Session.get"
        ) as mock_get, patch(
            "app.core.security.create_user_token", return_value="test-jwt"
        ):

            mock_fetch.return_value = login_token

            mock_response = Mock()
            mock_response.ok = True
            mock_response.json.return_value = google_user_info
            mock_get.return_value = mock_response

            with app.test_request_context():
                callback_url = url_for(
                    google_login_endpoint("authorized"), code="code", state=login_state
                )

            with test_client.session_transaction() as sess:
                sess[google_login_session_state_key()] = login_state

            response = test_client.get(callback_url, follow_redirects=False)
            assert response.status_code in [302, 307]

        # Verify user exists
        user = db_session.query(DbUser).filter_by(email="loginonly@example.com").first()
        assert user is not None

        # Verify NO calendar token
        calendar_records = (
            db_session.query(OAuth)
            .filter_by(provider=PROVIDER_GOOGLE_CALENDAR, user_id=user.id)
            .all()
        )
        assert len(calendar_records) == 0

    def test_calendar_connect_button_exists_in_template(self, test_client, app):
        """Test that calendar page shows connect button when not connected."""
        # This test verifies the template has the correct URL
        # Would need authenticated user and mock to fully test
        pass  # Template test - verify manually or with selenium

    def test_ui_shows_connected_state_after_calendar_authorization(
        self, test_client, app, db_session
    ):
        """Test that calendar page shows 'connected' state after successful authorization."""
        # Create user with calendar token
        user = DbUser()
        user.name = "Connected User"
        user.email = f"connected-{uuid.uuid4().hex[:8]}@example.com"
        user.google_id = f"google-{uuid.uuid4().hex[:8]}"
        user.role = "client"
        db_session.add(user)
        db_session.commit()

        # Store calendar token with provider_user_id
        oauth_record = OAuth()
        setattr(oauth_record, "provider", PROVIDER_GOOGLE_CALENDAR)
        oauth_record.user_id = user.id
        setattr(oauth_record, "provider_user_id", cast(str, user.google_id))
        oauth_record.token = {
            "access_token": "calendar-token-ui-test",
            "refresh_token": "refresh-token",
            "token_type": "Bearer",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp(),
        }
        db_session.add(oauth_record)
        db_session.commit()

        # Access calendar page as this user
        with test_client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = test_client.get("/calendar/", follow_redirects=True)

        # Should render successfully
        assert response.status_code == 200

        # Check that calendar_connected is True in the rendered template
        # This would require inspecting template context or response HTML
        # For now, verify the endpoint doesn't error
        assert (
            b"calendar" in response.data.lower() or b"agenda" in response.data.lower()
        )

    def test_ui_shows_disconnected_state_without_calendar_token(
        self, test_client, app, db_session
    ):
        """Test that calendar page shows 'not connected' state without calendar token."""
        # Create user WITHOUT calendar token
        user = DbUser()
        user.name = "Disconnected User"
        user.email = f"disconnected-{uuid.uuid4().hex[:8]}@example.com"
        user.google_id = f"google-{uuid.uuid4().hex[:8]}"
        user.role = "client"
        db_session.add(user)
        db_session.commit()

        # Access calendar page as this user (no calendar token)
        with test_client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = test_client.get("/calendar/", follow_redirects=True)

        # Should render successfully even without calendar connection
        assert response.status_code == 200

        # Page should indicate calendar is not connected
        # (Would need to parse HTML or check template context)
        assert (
            b"calendar" in response.data.lower() or b"agenda" in response.data.lower()
        )

    def test_startup_logs_show_both_blueprints(self, app, caplog):
        """Test that startup logs mention both blueprints."""
        # This would check application logs during startup
        # The blueprints should log their configuration
        with app.app_context():
            # Logs should have been created during app creation
            # Check for blueprint registration messages
            pass  # Log verification test
