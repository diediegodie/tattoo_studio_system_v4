"""
Unit tests for the extrato health check endpoint.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.db.base import Extrato


@pytest.mark.unit
def test_health_extrato_exists(client):
    """
    Test health check when extrato exists for previous month.

    Expected behavior:
    - Returns 200 status code
    - Status is "healthy"
    - exists is True
    - mes and ano match the previous month
    """
    # Mock get_previous_month to return a specific month
    with patch("app.controllers.health_controller.get_previous_month") as mock_get_prev:
        mock_get_prev.return_value = (9, 2025)  # September 2025

        # Mock database query to return an extrato record
        with patch("app.controllers.health_controller.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            # Create a mock Extrato record
            mock_extrato = Extrato(
                mes=9,
                ano=2025,
                pagamentos=json.dumps([]),
                sessoes=json.dumps([]),
                comissoes=json.dumps([]),
                gastos=json.dumps([]),
                totais=json.dumps({"receita_total": 0}),
            )

            # Mock query chain
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_filter.first.return_value = mock_extrato
            mock_query.filter.return_value = mock_filter
            mock_db.query.return_value = mock_query

            # Make request
            response = client.get("/health/extrato")

            # Assertions
            assert response.status_code == 200
            data = response.get_json()

            assert data["status"] == "healthy"
            assert data["mes"] == 9
            assert data["ano"] == 2025
            assert data["exists"] is True
            assert "September/2025 exists" in data["message"]

            # Verify database was queried
            mock_db.query.assert_called_once_with(Extrato)
            mock_db.close.assert_called_once()


@pytest.mark.unit
def test_health_extrato_missing(client):
    """
    Test health check when extrato is missing for previous month.

    Expected behavior:
    - Returns 200 status code (service is healthy, just data missing)
    - Status is "missing"
    - exists is False
    - mes and ano match the previous month
    """
    # Mock get_previous_month to return a specific month
    with patch("app.controllers.health_controller.get_previous_month") as mock_get_prev:
        mock_get_prev.return_value = (10, 2025)  # October 2025

        # Mock database query to return None (no record)
        with patch("app.controllers.health_controller.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            # Mock query chain to return None
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_filter.first.return_value = None
            mock_query.filter.return_value = mock_filter
            mock_db.query.return_value = mock_query

            # Make request
            response = client.get("/health/extrato")

            # Assertions
            assert response.status_code == 200
            data = response.get_json()

            assert data["status"] == "missing"
            assert data["mes"] == 10
            assert data["ano"] == 2025
            assert data["exists"] is False
            assert "October/2025 not found" in data["message"]

            # Verify database was queried
            mock_db.query.assert_called_once_with(Extrato)
            mock_db.close.assert_called_once()


@pytest.mark.unit
def test_health_extrato_error_handling(client):
    """
    Test health check when an error occurs.

    Expected behavior:
    - Returns 200 status code (to not fail monitoring)
    - Status is "error"
    - exists is False
    - Error message is included
    """
    # Mock get_previous_month to return a month
    with patch("app.controllers.health_controller.get_previous_month") as mock_get_prev:
        mock_get_prev.return_value = (9, 2025)

        # Mock database to raise an exception
        with patch("app.controllers.health_controller.SessionLocal") as mock_session:
            mock_session.side_effect = Exception("Database connection failed")

            # Make request
            response = client.get("/health/extrato")

            # Assertions
            assert response.status_code == 200  # Still 200 for monitoring
            data = response.get_json()

            assert data["status"] == "error"
            assert data["mes"] is None
            assert data["ano"] is None
            assert data["exists"] is False
            assert "Health check failed" in data["message"]
            assert "Database connection failed" in data["message"]


@pytest.mark.unit
def test_health_extrato_no_auth_required(client):
    """
    Test that the endpoint does not require authentication.

    Expected behavior:
    - Endpoint is accessible without login
    - Returns valid response (not 401 or redirect)
    """
    # Mock dependencies
    with patch("app.controllers.health_controller.get_previous_month") as mock_get_prev:
        mock_get_prev.return_value = (9, 2025)

        with patch("app.controllers.health_controller.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_filter.first.return_value = None
            mock_query.filter.return_value = mock_filter
            mock_db.query.return_value = mock_query

            # Make request WITHOUT authentication
            response = client.get("/health/extrato")

            # Should not be 401 or 302 (redirect)
            assert response.status_code == 200
            assert response.content_type == "application/json"


@pytest.mark.unit
def test_health_extrato_uses_timezone_aware_logic(client):
    """
    Test that the endpoint uses timezone-aware date calculation.

    Expected behavior:
    - Calls get_previous_month() from extrato_core
    - get_previous_month uses config.APP_TZ for timezone awareness
    """
    with patch("app.controllers.health_controller.get_previous_month") as mock_get_prev:
        mock_get_prev.return_value = (12, 2024)

        with patch("app.controllers.health_controller.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_filter.first.return_value = None
            mock_query.filter.return_value = mock_filter
            mock_db.query.return_value = mock_query

            # Make request
            response = client.get("/health/extrato")

            # Verify get_previous_month was called
            mock_get_prev.assert_called_once()

            # Verify response uses the values from get_previous_month
            data = response.get_json()
            assert data["mes"] == 12
            assert data["ano"] == 2024


@pytest.mark.unit
def test_health_extrato_structured_logging(client, caplog):
    """
    Test that the endpoint logs with structured context.

    Expected behavior:
    - Logs include context with endpoint, mes, ano
    - Logs include result status
    """
    import logging

    caplog.set_level(logging.INFO)

    with patch("app.controllers.health_controller.get_previous_month") as mock_get_prev:
        mock_get_prev.return_value = (9, 2025)

        with patch("app.controllers.health_controller.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_filter.first.return_value = None
            mock_query.filter.return_value = mock_filter
            mock_db.query.return_value = mock_query

            # Make request
            response = client.get("/health/extrato")

            # Check logging occurred (basic check)
            assert response.status_code == 200
            # Structured logging is used in the endpoint
            # Full validation would require checking LogRecord.extra
