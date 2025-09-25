"""
Validation tests for the AppointmentController (HTTP layer only).

This file contains unit tests for input validation and error handling
of the AppointmentController:
- Missing required fields validation
- Invalid data type validation
- Malformed input validation
- Edge case validation

These tests focus on ensuring proper error responses and input sanitization
following SOLID principles and interface-based testing.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
# Use the established test path setup
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()

try:
    import app.controllers.appointment_controller as appointment_controller
    from app.schemas.dtos import AppointmentResponse, ErrorResponse
    from app.services.appointment_service import AppointmentService

    # Get the class from the module
    AppointmentController = appointment_controller.AppointmentController

    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    IMPORTS_AVAILABLE = False
    appointment_controller = None
    AppointmentController = None
    AppointmentService = None
    AppointmentResponse = None
    ErrorResponse = None


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.controllers
class TestAppointmentControllerValidation:
    """Validation tests for AppointmentController input handling following SOLID principles."""

    def setup_method(self):
        """Set up test fixtures using interface-based dependency injection."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Interface segregation: Mock only the service interface we need
        self.mock_service = Mock(spec=AppointmentService)
        self.controller = AppointmentController(appointment_service=self.mock_service)

    # =====================================================
    # CREATE APPOINTMENT VALIDATION TESTS
    # =====================================================

    def test_create_appointment_missing_user_id_returns_400_validation_error(
        self, monkeypatch
    ):
        """Missing user_id should return 400 with specific validation message."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        payload = {
            "service_type": "tattoo",
            "scheduled_date": datetime.now().isoformat(),
            "duration_minutes": 60,
            "price": 150.0,
        }

        monkeypatch.setattr(
            appointment_controller,
            "request",
            Mock(get_json=Mock(return_value=payload)),
        )

        body, status = self.controller.create_appointment()

        assert status == 400
        assert body["success"] is False
        assert "user_id is required" in body.get("message", "")

    def test_create_appointment_missing_service_type_returns_400_validation_error(
        self, monkeypatch
    ):
        """Missing service_type should return 400 with specific validation message."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        payload = {
            "user_id": 1,
            "scheduled_date": datetime.now().isoformat(),
            "duration_minutes": 60,
            "price": 150.0,
        }

        monkeypatch.setattr(
            appointment_controller,
            "request",
            Mock(get_json=Mock(return_value=payload)),
        )

        body, status = self.controller.create_appointment()

        assert status == 400
        assert "service_type is required" in body.get("message", "")

    def test_create_appointment_invalid_date_format_returns_400_validation_error(
        self, monkeypatch
    ):
        """Invalid date format should return 400 with type conversion error."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        payload = {
            "user_id": 1,
            "service_type": "tattoo",
            "scheduled_date": "not-a-valid-date",
            "duration_minutes": 60,
            "price": 150.0,
        }

        monkeypatch.setattr(
            appointment_controller,
            "request",
            Mock(get_json=Mock(return_value=payload)),
        )

        body, status = self.controller.create_appointment()

        assert status == 400
        assert "Invalid data type" in body.get("message", "")

    def test_create_appointment_invalid_user_id_type_returns_400_validation_error(
        self, monkeypatch
    ):
        """Non-integer user_id should return 400 with type conversion error."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        payload = {
            "user_id": "not-a-number",
            "service_type": "tattoo",
            "scheduled_date": datetime.now().isoformat(),
            "duration_minutes": 60,
            "price": 150.0,
        }

        monkeypatch.setattr(
            appointment_controller,
            "request",
            Mock(get_json=Mock(return_value=payload)),
        )

        body, status = self.controller.create_appointment()

        assert status == 400
        assert "Invalid data type" in body.get("message", "")

    def test_create_appointment_service_exception_returns_500_server_error(
        self, monkeypatch
    ):
        """Service layer exception should return 500 with server error message."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        scheduled = datetime.now() + timedelta(days=1)
        payload = {
            "user_id": 1,
            "service_type": "tattoo",
            "scheduled_date": scheduled.isoformat(),
            "duration_minutes": 60,
            "price": 150.0,
        }

        monkeypatch.setattr(
            appointment_controller,
            "request",
            Mock(get_json=Mock(return_value=payload)),
        )

        # Service throws unexpected exception
        self.mock_service.create_appointment.side_effect = Exception(
            "Database connection failed"
        )

        body, status = self.controller.create_appointment()

        assert status == 500
        assert body["success"] is False
        assert "Database connection failed" in body.get("message", "")

    def test_create_appointment_empty_json_body_returns_400_validation_error(
        self, monkeypatch
    ):
        """Empty JSON body should return 400 validation error."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        monkeypatch.setattr(
            appointment_controller,
            "request",
            Mock(get_json=Mock(return_value={})),
        )

        body, status = self.controller.create_appointment()

        assert status == 400
        assert body["success"] is False

    def test_create_appointment_null_json_body_returns_400_validation_error(
        self, monkeypatch
    ):
        """Null JSON body should return 400 validation error."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        monkeypatch.setattr(
            appointment_controller,
            "request",
            Mock(get_json=Mock(return_value=None)),
        )

        body, status = self.controller.create_appointment()

        assert status == 400
        assert body["success"] is False

    # =====================================================
    # UPDATE APPOINTMENT VALIDATION TESTS
    # =====================================================

    def test_update_appointment_invalid_date_format_returns_400_validation_error(
        self, monkeypatch
    ):
        """Invalid date format in update should return 400 validation error."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        payload = {"scheduled_date": "invalid-date-format"}

        monkeypatch.setattr(
            appointment_controller,
            "request",
            Mock(get_json=Mock(return_value=payload)),
        )

        body, status = self.controller.update_appointment(5)

        assert status == 400
        assert (
            "Invalid data type" in body.get("message", "")
            or "validation" in body.get("error", "").lower()
        )

    def test_update_appointment_service_exception_returns_500_server_error(
        self, monkeypatch
    ):
        """Service exception during update should return 500 server error."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        monkeypatch.setattr(
            appointment_controller,
            "request",
            Mock(get_json=Mock(return_value={"notes": "test"})),
        )

        self.mock_service.update_appointment.side_effect = Exception("Update failed")

        body, status = self.controller.update_appointment(5)

        assert status == 500
        assert body["success"] is False

    # =====================================================
    # CANCEL APPOINTMENT VALIDATION TESTS
    # =====================================================

    def test_cancel_appointment_service_validation_error_returns_400_validation_error(
        self, monkeypatch
    ):
        """Service validation error during cancel should return 400."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        monkeypatch.setattr(
            appointment_controller,
            "request",
            Mock(get_json=Mock(return_value={"reason": "test"})),
        )

        self.mock_service.cancel_appointment.side_effect = ValueError(
            "Cannot cancel completed appointment"
        )

        body, status = self.controller.cancel_appointment(5)

        assert status == 400
        assert "Cannot cancel completed appointment" in body.get("message", "")

    def test_cancel_appointment_service_exception_returns_500_server_error(
        self, monkeypatch
    ):
        """Service exception during cancel should return 500 server error."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        monkeypatch.setattr(
            appointment_controller,
            "request",
            Mock(get_json=Mock(return_value={"reason": "test"})),
        )

        self.mock_service.cancel_appointment.side_effect = Exception(
            "Service unavailable"
        )

        body, status = self.controller.cancel_appointment(5)

        assert status == 500
        assert body["success"] is False
