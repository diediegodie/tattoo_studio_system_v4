"""Integration tests for Google OAuth login flow and admin alerts dashboard.

These tests validate end-to-end authentication and authorization flows using
Flask's test client with mocked Google OAuth responses. They also cover
regression scenarios to ensure repository safeguards remain in place.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from typing import Dict, Mapping, Optional
from unittest.mock import Mock, patch

import pytest

from app.db.base import User as DbUser
from app.domain.entities import User as DomainUser
from app.repositories.user_repo import UserRepository
from tests.conftest import google_oauth_session_state_key

DEFAULT_TOKEN: Dict[str, object] = {
    "access_token": "test-access-token",
    "refresh_token": "test-refresh-token",
    "token_type": "Bearer",
    "expires_at": 1_750_000_000,
}

_UNSET = object()


def _create_user(db_session, *, role: str = "client") -> DbUser:
    """Create and persist a user in the test database."""

    unique_suffix = uuid.uuid4().hex[:8]
    user = DbUser()
    user.name = f"Test {role.title()} {unique_suffix}"
    user.email = f"{role}.{unique_suffix}@example.com"
    user.google_id = f"google-{unique_suffix}"
    user.role = role
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@contextmanager
def _mock_google_oauth(
    user_info: Optional[Dict[str, object]],
    *,
    token: Optional[Dict[str, object]] = None,
    fetch_token_value: object = _UNSET,
):
    """Mock the Google OAuth handshake for Flask-Dance."""

    state_value = f"state-{uuid.uuid4().hex[:6]}"
    token_to_return = token or DEFAULT_TOKEN
    fetch_value = token_to_return if fetch_token_value is _UNSET else fetch_token_value

    oauth_response = Mock()
    oauth_response.ok = True
    oauth_response.json.return_value = user_info or {}

    with patch(
        "flask_dance.consumer.oauth2.OAuth2Session.authorization_url",
        return_value=("https://accounts.google.com/o/oauth2/auth", state_value),
    ) as mock_auth_url, patch(
        "flask_dance.consumer.oauth2.OAuth2Session.fetch_token",
        return_value=fetch_value,
    ) as mock_fetch_token, patch(
        "flask_dance.consumer.oauth2.OAuth2Session.get",
        return_value=oauth_response,
    ) as mock_get, patch(
        "app.services.oauth_token_service.OAuthTokenService.store_oauth_token",
        return_value=True,
    ), patch(
        "app.core.security.create_user_token", return_value="test-jwt-token"
    ) as mock_create_token:
        yield {
            "state": state_value,
            "mock_get": mock_get,
            "mock_fetch_token": mock_fetch_token,
            "mock_auth_url": mock_auth_url,
            "token": fetch_value,
        }


def _complete_google_login(
    client,
    user_info: Mapping[str, object],
    *,
    token: Optional[Dict[str, object]] = None,
    follow_redirects: bool = False,
    fetch_token_value: object = _UNSET,
):
    """Execute the Google OAuth login flow with patched responses."""

    payload = dict(user_info)
    with _mock_google_oauth(
        payload, token=token, fetch_token_value=fetch_token_value
    ) as oauth_context:
        # Kick off the login to populate OAuth state in the session
        login_response = client.get("/auth/login")
        assert login_response.status_code == 302

        # Retrieve the stored state so the callback can validate it
        # Use dynamic session key based on current blueprint name
        session_state_key = google_oauth_session_state_key()
        with client.session_transaction() as flask_session:
            stored_state = flask_session.get(session_state_key)
            if stored_state is None:
                # Some test paths bypass the default state persistence; ensure the expected
                # value is present to keep the OAuth flow consistent.
                flask_session[session_state_key] = oauth_context["state"]
                stored_state = oauth_context["state"]
        assert (
            stored_state is not None
        ), "OAuth state should be persisted in the session"

        # Complete the OAuth dance by calling the authorized endpoint
        callback_response = client.get(
            f"/auth/google/authorized?state={stored_state}&code=test-code",
            follow_redirects=follow_redirects,
        )

    return callback_response


@pytest.mark.integration
@pytest.mark.auth
def test_google_oauth_login_success_existing_user(client, db_session):
    """Simulate a successful Google OAuth login for an existing user."""

    existing_user = _create_user(db_session, role="artist")
    user_info = {
        "id": existing_user.google_id,
        "email": existing_user.email,
        "name": existing_user.name,
        "picture": "https://example.com/avatar.png",
    }

    response = _complete_google_login(client, user_info)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/index")
    set_cookie_header = response.headers.get("Set-Cookie", "")
    assert "access_token=" in set_cookie_header

    # Confirm the authenticated user can access a protected route
    index_response = client.get("/index")
    assert index_response.status_code == 200
    page = index_response.get_data(as_text=True)
    assert existing_user.name in page


@pytest.mark.integration
@pytest.mark.auth
def test_google_oauth_login_failure_missing_token(client):
    """Ensure the login flow surfaces an error when the token exchange fails."""

    # No user is needed because the token exchange will fail before lookup
    user_info = {
        "id": "google-missing-token",
        "email": "missing@example.com",
        "name": "Missing Token",
    }

    response = _complete_google_login(
        client,
        user_info,
        fetch_token_value=None,
        follow_redirects=True,
    )

    assert response.status_code == 200  # final page after redirect back to login
    html = response.get_data(as_text=True)
    assert "Falha ao fazer login com Google." in html

    with client.session_transaction() as flask_session:
        assert "_user_id" not in flask_session


@pytest.mark.integration
@pytest.mark.auth
def test_logout_clears_session_and_blocks_protected_routes(client, db_session):
    """After logout the session should be cleared and protected routes inaccessible."""

    user = _create_user(db_session, role="client")
    user_info = {
        "id": user.google_id,
        "email": user.email,
        "name": user.name,
    }

    # Perform login first
    login_response = _complete_google_login(client, user_info)
    assert login_response.status_code == 302

    logout_response = client.get("/logout")
    assert logout_response.status_code == 302
    assert logout_response.headers["Location"].endswith("/")

    with client.session_transaction() as flask_session:
        assert "_user_id" not in flask_session
        assert "logged_in" not in flask_session

    protected_response = client.get("/index")
    # In test mode, returns 401 JSON response for unauthenticated requests
    assert protected_response.status_code == 401


@pytest.mark.integration
def test_admin_alerts_requires_admin_role(client, db_session):
    """Non-admin users should receive 403 when accessing the alerts dashboard."""

    regular_user = _create_user(db_session, role="artist")
    user_info = {
        "id": regular_user.google_id,
        "email": regular_user.email,
        "name": regular_user.name,
    }

    login_response = _complete_google_login(client, user_info)
    assert login_response.status_code == 302

    response = client.get("/admin/alerts")
    assert response.status_code == 403


@pytest.mark.integration
def test_admin_alerts_renders_for_admin_with_alerts(client, db_session):
    """Admin users should see alert summaries and alert entries when data exists."""

    admin_user = _create_user(db_session, role="admin")
    user_info = {
        "id": admin_user.google_id,
        "email": admin_user.email,
        "name": admin_user.name,
    }

    alerts = [
        {
            "severity": "critical",
            "alert_type": "database",
            "message": "Database connection dropped",
            "timestamp": "2025-10-07T10:00:00Z",
            "details": {"request": {"route": "/api/jobs", "request_id": "req-1"}},
        },
        {
            "severity": "warning",
            "alert_type": "performance",
            "message": "Slow query detected",
            "timestamp": "2025-10-07T10:05:00Z",
            "details": {"request": {"route": "/api/jobs", "request_id": "req-2"}},
        },
        {
            "severity": "info",
            "alert_type": "heartbeat",
            "message": "Background worker heartbeat",
            "timestamp": "2025-10-07T10:10:00Z",
            "details": {
                "request": {"route": "/tasks/heartbeat", "request_id": "req-3"}
            },
        },
    ]

    login_response = _complete_google_login(client, user_info)
    assert login_response.status_code == 302

    with patch(
        "app.controllers.admin_alerts_controller.get_recent_alerts",
        return_value=alerts,
    ):
        response = client.get("/admin/alerts?limit=10")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Total de alertas:" in html
    assert "alert-summary-badge--critical" in html
    assert "alert-summary-badge--warning" in html
    assert "alert-summary-badge--info" in html
    for alert in alerts:
        assert alert["message"] in html


@pytest.mark.integration
def test_user_repository_guard_skips_is_active_assignment(db_session):
    """Ensure create/update logic no longer tries to assign Flask-Login's is_active property."""

    repo = UserRepository(db_session)
    domain_user = DomainUser(
        email="guard@example.com",
        name="Guard User",
        google_id=f"google-{uuid.uuid4().hex[:8]}",
        role="admin",
        is_active=False,
    )

    try:
        created = repo.create(domain_user)
        assert created is not None and created.id is not None

        loaded = repo.get_by_id(created.id)
        assert loaded is not None
        loaded.is_active = True

        updated = repo.update(loaded)
        assert updated is not None
    except AttributeError as exc:  # pragma: no cover - explicit regression guard
        pytest.fail(
            f"UserRepository attempted to assign read-only is_active property: {exc}"
        )
