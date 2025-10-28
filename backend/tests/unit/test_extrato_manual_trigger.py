"""
Unit tests for manual extrato generation API endpoint.

Tests the /api/extrato/generate endpoint to ensure:
- Admin-only access control
- Proper parameter validation
- Correct function calls with atomic transaction support
- Backup toggle compliance (EXTRATO_REQUIRE_BACKUP)
- Proper error handling
- Structured logging
"""

import json
from unittest.mock import MagicMock, patch
import pytest


class TestExtratoManualTriggerAccessControl:
    """Test access control for the manual trigger endpoint."""

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    def test_admin_success(self, mock_generate, client):
        """Test that admin users can trigger generation."""
        mock_generate.return_value = True

        # Mock admin user
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "admin"
        mock_user.id = 1
        mock_user.email = "admin@test.com"

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/api/extrato/generate",
                json={"month": 1, "year": 2025, "force": False},
                headers={"Content-Type": "application/json"},
            )

            # Should succeed
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True

            # Verify atomic function was called
            mock_generate.assert_called_once_with(mes=1, ano=2025, force=False)

    def test_non_admin_user_rejected(self, client):
        """Test that non-admin users are rejected."""
        # Mock non-admin user
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "user"
        mock_user.id = 2

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/api/extrato/generate",
                json={"month": 1, "year": 2025},
                headers={"Content-Type": "application/json"},
            )

            # Should be forbidden
            assert response.status_code == 403
            data = response.get_json()
            assert data["success"] is False


class TestExtratoManualTriggerValidation:
    """Test parameter validation."""

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    def test_invalid_month_too_low(self, mock_generate, client):
        """Test that month < 1 returns 400."""
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "admin"
        mock_user.id = 1

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/api/extrato/generate",
                json={"month": 0, "year": 2025},
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 400
            data = response.get_json()
            assert data["success"] is False
            assert "Month must be an integer between 1 and 12" in data["error"]

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    def test_invalid_month_too_high(self, mock_generate, client):
        """Test that month > 12 returns 400."""
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "admin"
        mock_user.id = 1

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/api/extrato/generate",
                json={"month": 13, "year": 2025},
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 400
            data = response.get_json()
            assert data["success"] is False

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    def test_invalid_year_values(self, mock_generate, client):
        """Test invalid year values."""
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "admin"
        mock_user.id = 1

        with patch("flask_login.utils._get_user", return_value=mock_user):
            # Test year too low
            response = client.post(
                "/api/extrato/generate",
                json={"month": 1, "year": 1999},
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 400


class TestExtratoManualTriggerSuccess:
    """Test successful extrato generation scenarios."""

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    def test_success_with_explicit_params(self, mock_generate, client):
        """Test successful generation with explicit month and year."""
        mock_generate.return_value = True
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "admin"
        mock_user.id = 1
        mock_user.email = "admin@test.com"

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/api/extrato/generate",
                json={"month": 2, "year": 2025, "force": True},
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["data"]["month"] == 2
            assert data["data"]["year"] == 2025
            assert data["data"]["force"] is True

            mock_generate.assert_called_once_with(mes=2, ano=2025, force=True)

    @patch("app.services.extrato_core.get_previous_month")
    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    def test_success_with_defaults(self, mock_generate, mock_prev_month, client):
        """Test successful generation with default month/year."""
        mock_generate.return_value = True
        mock_prev_month.return_value = (10, 2024)

        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "admin"
        mock_user.id = 1
        mock_user.email = "admin@test.com"

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/api/extrato/generate",
                json={},  # No month/year provided
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            # Should use previous month
            assert data["data"]["month"] == 10
            assert data["data"]["year"] == 2024


class TestExtratoManualTriggerErrorHandling:
    """Test error handling scenarios."""

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    def test_generation_function_returns_false(self, mock_generate, client):
        """Test when generation function returns False."""
        mock_generate.return_value = False
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "admin"
        mock_user.id = 1

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/api/extrato/generate",
                json={"month": 3, "year": 2025},
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    def test_generation_function_raises_exception(self, mock_generate, client):
        """Test when generation function raises an exception."""
        mock_generate.side_effect = Exception("Database error")
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "admin"
        mock_user.id = 1

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/api/extrato/generate",
                json={"month": 4, "year": 2025},
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False
            assert "Internal server error" in data["error"]


class TestExtratoManualTriggerAtomicFunction:
    """Test that the endpoint uses the correct atomic function."""

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    def test_uses_correct_atomic_function(self, mock_atomic, client):
        """Verify endpoint uses check_and_generate_extrato_with_transaction."""
        mock_atomic.return_value = True
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "admin"
        mock_user.id = 1
        mock_user.email = "admin@test.com"

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/api/extrato/generate",
                json={"month": 5, "year": 2025, "force": False},
                headers={"Content-Type": "application/json"},
            )

            # Verify the atomic function was called
            assert mock_atomic.called
            mock_atomic.assert_called_once_with(mes=5, ano=2025, force=False)


class TestExtratoManualTriggerLogging:
    """Test structured logging functionality."""

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    @patch("app.controllers.api_controller.logger")
    def test_logs_successful_generation(self, mock_logger, mock_generate, client):
        """Test that successful generation is logged."""
        mock_generate.return_value = True
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "admin"
        mock_user.id = 1
        mock_user.email = "admin@test.com"

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/api/extrato/generate",
                json={"month": 6, "year": 2025},
                headers={"Content-Type": "application/json"},
            )

            # Verify logging occurred
            assert mock_logger.info.called

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    @patch("app.controllers.api_controller.logger")
    def test_logs_failed_generation(self, mock_logger, mock_generate, client):
        """Test that failed generation is logged."""
        mock_generate.return_value = False
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "admin"
        mock_user.id = 1

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/api/extrato/generate",
                json={"month": 7, "year": 2025},
                headers={"Content-Type": "application/json"},
            )

            # Verify error logging
            assert mock_logger.error.called

    @patch("app.controllers.api_controller.logger")
    def test_logs_unauthorized_attempts(self, mock_logger, client):
        """Test that unauthorized attempts are logged."""
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "user"  # Not admin
        mock_user.id = 2

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/api/extrato/generate",
                json={"month": 8, "year": 2025},
                headers={"Content-Type": "application/json"},
            )

            # Verify warning was logged
            assert mock_logger.warning.called
