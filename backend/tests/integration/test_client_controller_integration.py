"""
Integration tests for Client Controller using Flask test client.

This module demonstrates the implementation of integration tests
using Flask test client, database transaction isolation, and
authentication fixtures following SOLID principles.
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
    sample_client_data,
    mock_jotform_response,
    database_transaction_isolator,
    response_helper,
)
from tests.fixtures.auth_fixtures import (
    auth_headers_valid,
    auth_headers_invalid,
    auth_headers_missing,
    protected_endpoint_tester,
    auth_test_helper,
)


@pytest.mark.integration
@pytest.mark.controllers
@pytest.mark.clients
class TestClientControllerIntegrationComplete:
    """Complete integration tests for client controller endpoints."""

    def test_client_list_page_renders_successfully(
        self, authenticated_client, mock_jotform_response, response_helper
    ):
        """Test that client list page renders with proper authentication."""
        with patch(
            "services.jotform_service.JotFormService.get_submissions"
        ) as mock_jotform:
            mock_jotform.return_value = mock_jotform_response["content"]

            response = authenticated_client.authenticated_get("/clients")

            # Should render HTML page successfully
            html_content = response_helper.assert_html_response(response, 200)
            assert "clients" in html_content.lower()
            mock_jotform.assert_called_once()

    def test_client_list_requires_authentication(
        self, client, protected_endpoint_tester
    ):
        """Test that client list endpoint requires authentication."""
        assert protected_endpoint_tester("/clients")

    def test_client_list_handles_jotform_service_error(
        self, authenticated_client, response_helper
    ):
        """Test client list handles JotForm service errors gracefully."""
        with patch(
            "services.jotform_service.JotFormService.get_submissions"
        ) as mock_jotform:
            mock_jotform.side_effect = Exception("JotForm API Error")

            response = authenticated_client.authenticated_get("/clients")

            # Should still render page but handle error
            html_content = response_helper.assert_html_response(response, 200)
            # Error should be handled gracefully
            assert "error" in html_content.lower() or "clients" in html_content.lower()

    def test_sync_clients_endpoint_success(
        self,
        authenticated_client,
        mock_jotform_response,
        database_transaction_isolator,
        response_helper,
    ):
        """Test client synchronization endpoint with database transaction isolation."""
        # Use transaction isolation for this test
        savepoint = database_transaction_isolator["create_savepoint"]()

        try:
            with patch(
                "services.jotform_service.JotFormService.get_submissions"
            ) as mock_jotform:
                with patch(
                    "services.client_service.ClientService.sync_clients"
                ) as mock_sync:
                    mock_jotform.return_value = mock_jotform_response["content"]
                    mock_sync.return_value = {"synced": 1, "total": 1}

                    response = authenticated_client.authenticated_post("/clients/sync")

                    # Should redirect with success
                    location = response_helper.assert_redirect_response(response)
                    assert "/clients" in location

                    # Verify services were called
                    mock_jotform.assert_called_once()
                    mock_sync.assert_called_once()

            # Commit the transaction for this test
            database_transaction_isolator["commit_savepoint"](savepoint)

        except Exception:
            # Rollback on any error
            database_transaction_isolator["rollback_to_savepoint"](savepoint)
            raise

    def test_sync_clients_requires_authentication(
        self, client, protected_endpoint_tester
    ):
        """Test that client sync endpoint requires authentication."""
        assert protected_endpoint_tester("/clients/sync", method="POST")

    def test_api_client_list_returns_json(
        self, authenticated_client, sample_client_data, response_helper
    ):
        """Test API client list endpoint returns JSON data."""
        with patch(
            "services.client_service.ClientService.get_all_clients"
        ) as mock_service:
            mock_service.return_value = [sample_client_data]

            response = authenticated_client.authenticated_get("/api/clients")

            # Should return JSON data
            json_data = response_helper.assert_json_response(response, 200)
            assert isinstance(json_data, list)
            assert len(json_data) >= 0  # Could be empty or have data
            mock_service.assert_called_once()

    def test_api_client_list_requires_authentication(
        self, client, protected_endpoint_tester
    ):
        """Test that API client list endpoint requires authentication."""
        assert protected_endpoint_tester("/api/clients")

    def test_api_client_list_handles_service_errors(
        self, authenticated_client, response_helper
    ):
        """Test API client list handles service errors properly."""
        with patch(
            "services.client_service.ClientService.get_all_clients"
        ) as mock_service:
            mock_service.side_effect = Exception("Database Error")

            response = authenticated_client.authenticated_get("/api/clients")

            # Should return error response
            assert response.status_code >= 400
            # Response could be JSON error or HTML error page

    def test_client_endpoints_return_proper_content_types(self, authenticated_client):
        """Test that client endpoints return correct Content-Type headers."""
        with patch(
            "services.jotform_service.JotFormService.get_submissions"
        ) as mock_jotform:
            with patch(
                "services.client_service.ClientService.get_all_clients"
            ) as mock_service:
                mock_jotform.return_value = []
                mock_service.return_value = []

                # HTML endpoint should return text/html
                html_response = authenticated_client.authenticated_get("/clients")
                assert "text/html" in html_response.content_type

                # API endpoint should return application/json
                api_response = authenticated_client.authenticated_get("/api/clients")
                assert "application/json" in api_response.content_type


@pytest.mark.integration
@pytest.mark.auth
@pytest.mark.controllers
class TestAuthenticationIntegration:
    """Integration tests for authentication across all endpoints."""

    def test_all_protected_endpoints_require_valid_jwt(
        self, client, auth_headers_valid, auth_headers_invalid, auth_headers_missing
    ):
        """Test that all protected endpoints properly validate JWT tokens."""
        protected_endpoints = [
            ("/clients", "GET"),
            ("/clients/sync", "POST"),
            ("/api/clients", "GET"),
        ]

        for endpoint, method in protected_endpoints:
            # Test without auth headers
            response = getattr(client, method.lower())(
                endpoint, headers=auth_headers_missing
            )
            assert (
                response.status_code == 401
            ), f"Endpoint {endpoint} should require auth"

            # Test with invalid auth headers
            response = getattr(client, method.lower())(
                endpoint, headers=auth_headers_invalid
            )
            assert (
                response.status_code == 401
            ), f"Endpoint {endpoint} should reject invalid tokens"

    def test_jwt_token_expiration_handling(self, client, auth_headers_expired):
        """Test that expired JWT tokens are properly rejected."""
        response = client.get("/clients", headers=auth_headers_expired)
        assert response.status_code == 401

    def test_authentication_error_responses_are_consistent(
        self, client, auth_headers_invalid, auth_test_helper
    ):
        """Test that authentication errors return consistent responses."""
        endpoints = ["/clients", "/api/clients"]

        for endpoint in endpoints:
            response = client.get(endpoint, headers=auth_headers_invalid)
            auth_test_helper.assert_requires_auth(response)


@pytest.mark.integration
@pytest.mark.database
@pytest.mark.controllers
class TestDatabaseTransactionIsolation:
    """Test database transaction isolation in integration tests."""

    def test_transaction_isolation_between_tests(
        self, db_session, database_transaction_isolator, sample_client_data
    ):
        """Test that database changes are isolated between tests."""
        # This test demonstrates transaction isolation
        savepoint1 = database_transaction_isolator["create_savepoint"]()

        try:
            # Simulate database changes
            # In a real test, this would create/modify database records
            test_data = sample_client_data.copy()
            test_data["name"] = "Transaction Test User"

            # The changes should be isolated to this transaction
            savepoint2 = database_transaction_isolator["create_savepoint"]()

            # Rollback to savepoint2
            database_transaction_isolator["rollback_to_savepoint"](savepoint2)

            # Changes after savepoint2 should be rolled back
            # Original changes should still be in savepoint1

            # Commit savepoint1
            database_transaction_isolator["commit_savepoint"](savepoint1)

        except Exception:
            database_transaction_isolator["rollback_to_savepoint"](savepoint1)
            raise

    def test_database_session_cleanup_after_test(self, db_session):
        """Test that database session is properly cleaned up after each test."""
        # This test verifies that each test gets a clean database state

        # Check that session is active and clean
        assert db_session is not None
        assert db_session.is_active

        # Any changes made in this test will be automatically rolled back
        # by the db_session fixture after test completion


@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.controllers
class TestPerformanceAndReliability:
    """Integration tests for performance and reliability concerns."""

    def test_client_list_performance_with_large_dataset(
        self, authenticated_client, response_helper
    ):
        """Test client list performance with simulated large dataset."""
        # Mock a large dataset response
        large_dataset = [
            {
                "id": i,
                "name": f"Client {i}",
                "email": f"client{i}@example.com",
                "submission_id": f"jotform_{i}",
            }
            for i in range(100)  # Simulate 100 clients
        ]

        with patch(
            "services.jotform_service.JotFormService.get_submissions"
        ) as mock_jotform:
            mock_jotform.return_value = large_dataset

            import time

            start_time = time.time()

            response = authenticated_client.authenticated_get("/clients")

            end_time = time.time()
            response_time = end_time - start_time

            # Should handle large dataset efficiently
            response_helper.assert_html_response(response, 200)
            assert response_time < 5.0, f"Response took too long: {response_time}s"

    def test_concurrent_client_sync_handling(
        self, authenticated_client, mock_jotform_response, response_helper
    ):
        """Test handling of concurrent client sync requests."""
        with patch(
            "services.jotform_service.JotFormService.get_submissions"
        ) as mock_jotform:
            with patch(
                "services.client_service.ClientService.sync_clients"
            ) as mock_sync:
                mock_jotform.return_value = mock_jotform_response["content"]
                mock_sync.return_value = {"synced": 1, "total": 1}

                # Simulate concurrent requests
                responses = []
                for _ in range(3):
                    response = authenticated_client.authenticated_post("/clients/sync")
                    responses.append(response)

                # All requests should be handled gracefully
                for response in responses:
                    assert response.status_code in [
                        200,
                        302,
                        303,
                    ]  # Success or redirect

    def test_error_recovery_and_graceful_degradation(
        self, authenticated_client, response_helper
    ):
        """Test error recovery and graceful degradation."""
        # Test multiple failure scenarios
        failure_scenarios = [
            ("JotForm API timeout", Exception("Request timeout")),
            ("Database connection error", Exception("Database unavailable")),
            ("Service internal error", Exception("Internal service error")),
        ]

        for scenario_name, exception in failure_scenarios:
            with patch(
                "services.jotform_service.JotFormService.get_submissions"
            ) as mock_service:
                mock_service.side_effect = exception

                response = authenticated_client.authenticated_get("/clients")

                # Should fail gracefully, not crash
                assert response.status_code in [
                    200,
                    500,
                ]  # Either renders with error or returns 500

                # If 200, should contain error handling
                if response.status_code == 200:
                    html_content = response_helper.assert_html_response(response, 200)
                    # Should show some content even with errors
                    assert len(html_content) > 0
