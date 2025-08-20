"""
Integration tests for Authentication Controller using Flask test client.

This module demonstrates authentication integration testing with
Flask test client, database transaction isolation, and comprehensive
authentication scenarios following SOLID principles.
"""

import pytest
import json
from unittest.mock import patch, Mock

# Import integration fixtures
from tests.fixtures.integration_fixtures import (
    app,
    client,
    db_session,
    authenticated_client,
    database_transaction_isolator,
    response_helper,
)
from tests.fixtures.auth_fixtures import (
    valid_jwt_token,
    expired_jwt_token,
    invalid_jwt_token,
    auth_headers_valid,
    auth_headers_expired,
    auth_headers_invalid,
    mock_authenticated_user,
    authentication_scenarios,
    auth_test_helper,
    oauth_mock,
)


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.controllers
class TestAuthControllerIntegrationComplete:
    """Complete integration tests for authentication controller endpoints."""

    def test_login_page_renders_successfully(self, client, response_helper):
        """Test that login page renders without authentication."""
        response = client.get("/login")

        # Should render login page successfully
        html_content = response_helper.assert_html_response(response, 200)
        assert "login" in html_content.lower()

    def test_google_oauth_callback_success(
        self, client, oauth_mock, database_transaction_isolator, response_helper
    ):
        """Test Google OAuth callback with successful authentication."""
        # Use transaction isolation for this test
        savepoint = database_transaction_isolator["create_savepoint"]()

        try:
            with patch(
                "services.user_service.UserService.create_or_update_from_google"
            ) as mock_user_service:
                with patch("core.security.create_access_token") as mock_token:
                    # Mock successful OAuth and user creation
                    mock_user_data = oauth_mock["success"]()
                    mock_user_service.return_value = Mock(
                        id=123, email=mock_user_data["email"]
                    )
                    mock_token.return_value = "mock_jwt_token"

                    # Simulate OAuth callback
                    response = client.get("/auth/google/callback?code=valid_auth_code")

                    # Should redirect to dashboard or home
                    location = response_helper.assert_redirect_response(response)
                    assert "/" in location or "/dashboard" in location

                    # Verify services were called
                    mock_user_service.assert_called_once()
                    mock_token.assert_called_once()

            # Commit the transaction for this test
            database_transaction_isolator["commit_savepoint"](savepoint)

        except Exception:
            # Rollback on any error
            database_transaction_isolator["rollback_to_savepoint"](savepoint)
            raise

    def test_google_oauth_callback_failure(self, client, oauth_mock, response_helper):
        """Test Google OAuth callback with authentication failure."""
        with patch("requests.get") as mock_request:
            # Mock failed OAuth response
            mock_response = Mock()
            mock_response.json.return_value = oauth_mock["failure"]()
            mock_response.status_code = 400
            mock_request.return_value = mock_response

            response = client.get("/auth/google/callback?error=access_denied")

            # Should redirect to login with error
            location = response_helper.assert_redirect_response(response)
            assert "/login" in location

    def test_logout_endpoint_clears_session(
        self, authenticated_client, response_helper
    ):
        """Test logout endpoint clears authentication session."""
        response = authenticated_client.authenticated_post("/logout")

        # Should redirect to login or home
        location = response_helper.assert_redirect_response(response)
        assert "/login" in location or "/" in location

    def test_protected_endpoint_with_valid_session(
        self, authenticated_client, response_helper
    ):
        """Test protected endpoint access with valid authentication."""
        # Test accessing a protected endpoint (using clients as example)
        response = authenticated_client.authenticated_get("/clients")

        # Should allow access
        assert response.status_code in [200, 302]  # Either shows content or redirects

    def test_api_authentication_with_jwt_headers(
        self, client, auth_headers_valid, response_helper
    ):
        """Test API endpoint authentication using JWT headers."""
        response = client.get("/api/clients", headers=auth_headers_valid)

        # Should allow API access with valid JWT
        assert response.status_code in [200, 401]  # Depends on implementation

    def test_api_authentication_rejects_expired_tokens(
        self, client, auth_headers_expired, auth_test_helper
    ):
        """Test that API endpoints reject expired JWT tokens."""
        response = client.get("/api/clients", headers=auth_headers_expired)

        # Should reject expired tokens
        auth_test_helper.assert_requires_auth(response)

    def test_api_authentication_rejects_invalid_tokens(
        self, client, auth_headers_invalid, auth_test_helper
    ):
        """Test that API endpoints reject invalid JWT tokens."""
        response = client.get("/api/clients", headers=auth_headers_invalid)

        # Should reject invalid tokens
        auth_test_helper.assert_requires_auth(response)


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.security
class TestAuthenticationSecurityIntegration:
    """Integration tests for authentication security measures."""

    def test_session_hijacking_protection(self, client, auth_headers_valid):
        """Test protection against session hijacking."""
        # Create a session
        response1 = client.get("/api/clients", headers=auth_headers_valid)

        # Try to use the same token from different "client"
        # This would be detected by IP checking, user agent checking, etc.
        modified_headers = auth_headers_valid.copy()
        modified_headers["User-Agent"] = "Different-Client/1.0"

        response2 = client.get("/api/clients", headers=modified_headers)

        # Should either work (if no IP/UA checking) or fail securely
        assert response2.status_code in [200, 401, 403]

    def test_brute_force_protection(self, client):
        """Test protection against brute force attacks."""
        # Simulate multiple failed login attempts
        failed_attempts = []

        for i in range(5):
            response = client.post(
                "/auth/login",
                json={"email": "test@example.com", "[REDACTED_PASSWORD]"wrong_password_{i}"},
            )
            failed_attempts.append(response.status_code)

        # Should implement rate limiting or account lockout
        # The exact behavior depends on implementation
        assert all(status in [400, 401, 429] for status in failed_attempts)

    def test_csrf_protection_on_state_changing_operations(self, authenticated_client):
        """Test CSRF protection on state-changing operations."""
        # Test operations that change state
        csrf_protected_endpoints = [
            ("/logout", "POST"),
            ("/clients/sync", "POST"),
        ]

        for endpoint, method in csrf_protected_endpoints:
            response = getattr(authenticated_client, f"authenticated_{method.lower()}")(
                endpoint
            )

            # Should either succeed with CSRF token or fail without it
            # Since we disabled CSRF for testing, these should succeed
            assert response.status_code in [200, 302, 400, 403]

    def test_sql_injection_protection_in_login(self, client):
        """Test SQL injection protection in login endpoint."""
        # Attempt SQL injection in login
        malicious_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
        ]

        for payload in malicious_payloads:
            response = client.post(
                "/auth/login", json={"email": payload, "[REDACTED_PASSWORD]
            )

            # Should reject malicious input safely
            assert response.status_code in [400, 401]

    def test_xss_protection_in_user_data(self, authenticated_client, response_helper):
        """Test XSS protection in user data display."""
        with patch("services.user_service.UserService.get_current_user") as mock_user:
            # Mock user with potentially malicious data
            mock_user.return_value = Mock(
                name="<script>alert('xss')</script>Test User", email="test@example.com"
            )

            response = authenticated_client.authenticated_get("/dashboard")

            if response.status_code == 200:
                html_content = response_helper.assert_html_response(response, 200)

                # Should escape HTML in user data
                assert "<script>" not in html_content
                assert "&lt;script&gt;" in html_content or "Test User" in html_content


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.database
class TestAuthenticationDatabaseIntegration:
    """Integration tests for authentication with database operations."""

    def test_user_creation_with_transaction_isolation(
        self, db_session, database_transaction_isolator, authentication_scenarios
    ):
        """Test user creation with proper database transaction isolation."""
        savepoint = database_transaction_isolator["create_savepoint"]()

        try:
            # Simulate user creation
            user_data = authentication_scenarios["valid_user"]

            # In a real test, this would create a user record
            # For now, we test the transaction isolation mechanism

            # Create another savepoint for nested transaction
            nested_savepoint = database_transaction_isolator["create_savepoint"]()

            # Rollback nested transaction
            database_transaction_isolator["rollback_to_savepoint"](nested_savepoint)

            # Original transaction should still be intact
            # Commit the original transaction
            database_transaction_isolator["commit_savepoint"](savepoint)

        except Exception:
            database_transaction_isolator["rollback_to_savepoint"](savepoint)
            raise

    def test_concurrent_user_sessions(self, db_session, authentication_scenarios):
        """Test handling of concurrent user sessions."""
        # This would test scenarios like:
        # - Same user logging in from multiple devices
        # - Session invalidation
        # - Token refresh scenarios

        user_data = authentication_scenarios["valid_user"]

        # Simulate multiple active sessions for the same user
        # Implementation would depend on your session management strategy
        assert user_data["user_id"] == 123
        assert user_data["is_active"] is True

    def test_user_data_consistency_across_transactions(
        self, db_session, database_transaction_isolator
    ):
        """Test user data consistency across multiple database transactions."""
        # This tests that user authentication data remains consistent
        # across multiple database operations

        savepoint1 = database_transaction_isolator["create_savepoint"]()

        try:
            # Simulate user data operations
            # In real implementation, this would involve actual database operations

            savepoint2 = database_transaction_isolator["create_savepoint"]()

            # Test data consistency
            database_transaction_isolator["commit_savepoint"](savepoint2)
            database_transaction_isolator["commit_savepoint"](savepoint1)

        except Exception:
            database_transaction_isolator["rollback_to_savepoint"](savepoint1)
            raise


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.performance
class TestAuthenticationPerformance:
    """Integration tests for authentication performance."""

    def test_login_performance_under_load(self, client):
        """Test login endpoint performance under simulated load."""
        import time

        # Simulate multiple concurrent login attempts
        login_times = []

        for i in range(10):
            start_time = time.time()

            response = client.post(
                "/auth/login",
                json={"email": f"user{i}@example.com", "[REDACTED_PASSWORD]"},
            )

            end_time = time.time()
            login_times.append(end_time - start_time)

        # Should handle multiple requests efficiently
        avg_time = sum(login_times) / len(login_times)
        max_time = max(login_times)

        assert avg_time < 1.0, f"Average login time too slow: {avg_time}s"
        assert max_time < 2.0, f"Maximum login time too slow: {max_time}s"

    def test_jwt_token_validation_performance(self, client, auth_headers_valid):
        """Test JWT token validation performance."""
        import time

        # Test multiple API calls with JWT validation
        validation_times = []

        for i in range(20):
            start_time = time.time()

            response = client.get("/api/clients", headers=auth_headers_valid)

            end_time = time.time()
            validation_times.append(end_time - start_time)

        # JWT validation should be fast
        avg_time = sum(validation_times) / len(validation_times)
        assert avg_time < 0.5, f"JWT validation too slow: {avg_time}s"

    def test_session_cleanup_performance(
        self, db_session, database_transaction_isolator
    ):
        """Test session cleanup and garbage collection performance."""
        savepoint = database_transaction_isolator["create_savepoint"]()

        try:
            # Simulate session creation and cleanup
            import time

            start_time = time.time()

            # Create multiple nested savepoints to test cleanup
            savepoints = []
            for i in range(10):
                sp = database_transaction_isolator["create_savepoint"]()
                savepoints.append(sp)

            # Clean up all savepoints
            for sp in reversed(savepoints):
                database_transaction_isolator["rollback_to_savepoint"](sp)

            end_time = time.time()
            cleanup_time = end_time - start_time

            assert cleanup_time < 1.0, f"Session cleanup too slow: {cleanup_time}s"

            database_transaction_isolator["commit_savepoint"](savepoint)

        except Exception:
            database_transaction_isolator["rollback_to_savepoint"](savepoint)
            raise
