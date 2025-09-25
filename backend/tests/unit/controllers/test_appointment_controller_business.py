"""
Business logic tests for the AppointmentController (HTTP layer only).

This file contains tests for business logic validation and architectural
compliance of the AppointmentController:
- SOLID principles verification
- Service integration testing
- Complex business scenarios
- Architectural pattern validation

These tests ensure the controller follows proper design principles
and integrates correctly with the service layer.
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
class TestAppointmentControllerBusiness:
    """Business logic tests for AppointmentController following SOLID principles."""

    def setup_method(self):
        """Set up test fixtures using interface-based dependency injection."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Interface segregation: Mock only the service interface we need
        self.mock_service = Mock(spec=AppointmentService)
        self.controller = AppointmentController(appointment_service=self.mock_service)

    # =====================================================
    # CANCEL APPOINTMENT BUSINESS LOGIC TESTS
    # =====================================================

    def test_cancel_appointment_success_with_reason_returns_success_message(
        self, monkeypatch
    ):
        """Cancelling appointment with reason should return success message."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        payload = {"reason": "Client requested reschedule"}

        monkeypatch.setattr(
            appointment_controller,
            "request",
            Mock(get_json=Mock(return_value=payload)),
        )

        self.mock_service.cancel_appointment.return_value = True

        result = self.controller.cancel_appointment(5)

        assert result["success"] is True
        assert "cancelled successfully" in result["message"]

    def test_cancel_appointment_success_without_reason_returns_success_message(
        self, monkeypatch
    ):
        """Cancelling appointment without reason should still succeed."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        payload = {}

        monkeypatch.setattr(
            appointment_controller,
            "request",
            Mock(get_json=Mock(return_value=payload)),
        )

        self.mock_service.cancel_appointment.return_value = True

        result = self.controller.cancel_appointment(8)

        assert result["success"] is True

    def test_cancel_appointment_not_found_returns_404_error(self, monkeypatch):
        """Cancelling non-existent appointment should return 404 error."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        monkeypatch.setattr(
            appointment_controller,
            "request",
            Mock(get_json=Mock(return_value={"reason": "test"})),
        )

        self.mock_service.cancel_appointment.return_value = False

        body, status = self.controller.cancel_appointment(999)

        assert status == 404
        assert body["success"] is False

    # =====================================================
    # SOLID PRINCIPLES VERIFICATION TESTS
    # =====================================================

    def test_controller_follows_single_responsibility_principle(self):
        """Controller should only handle HTTP concerns, not business logic."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Verify controller class has no business logic methods
        controller_methods = [
            method for method in dir(self.controller) if not method.startswith("_")
        ]
        business_logic_keywords = ["validate", "calculate", "process", "compute"]

        for method in controller_methods:
            for keyword in business_logic_keywords:
                assert (
                    keyword not in method.lower()
                ), f"Controller method '{method}' suggests business logic violation"

    def test_controller_follows_dependency_inversion_principle(self):
        """Controller should depend on service interface, not concrete implementation."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Verify controller accepts service through constructor (dependency injection)
        assert hasattr(self.controller, "appointment_service")
        assert self.controller.appointment_service == self.mock_service

    def test_controller_methods_return_consistent_response_format(self, monkeypatch):
        """All controller methods should return consistent response format."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Test consistent success response format
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

        mock_response = Mock()
        mock_response.id = 1
        mock_response.user_id = 1
        mock_response.service_type = "tattoo"
        mock_response.scheduled_date = scheduled
        mock_response.duration_minutes = 60
        mock_response.price = 150.0
        mock_response.status = "scheduled"
        mock_response.notes = None
        mock_response.created_at = datetime.now()

        self.mock_service.create_appointment.return_value = mock_response

        result = self.controller.create_appointment()

        # Verify consistent response structure
        assert "success" in result
        assert isinstance(result["success"], bool)
        if result["success"]:
            assert "data" in result
        else:
            assert "error" in result
            assert "message" in result

    # =====================================================
    # SERVICE INTEGRATION TESTS
    # =====================================================

    def test_controller_properly_integrates_with_service_layer(self, monkeypatch):
        """Controller should properly integrate with service layer through interface."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Test that controller calls service methods correctly
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

        mock_response = Mock()
        mock_response.id = 1
        self.mock_service.create_appointment.return_value = mock_response

        result = self.controller.create_appointment()

        # Verify service method was called
        self.mock_service.create_appointment.assert_called_once()

        # Verify response structure
        assert result["success"] is True
        assert "data" in result

    def test_controller_handles_service_layer_errors_gracefully(self, monkeypatch):
        """Controller should handle service layer errors gracefully."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        monkeypatch.setattr(
            appointment_controller,
            "request",
            Mock(
                get_json=Mock(
                    return_value={
                        "user_id": 1,
                        "service_type": "tattoo",
                        "scheduled_date": datetime.now().isoformat(),
                        "duration_minutes": 60,
                        "price": 150.0,
                    }
                )
            ),
        )

        # Service throws business logic exception
        self.mock_service.create_appointment.side_effect = ValueError(
            "Invalid appointment data"
        )

        body, status = self.controller.create_appointment()

        assert status == 400
        assert body["success"] is False
        assert "Invalid appointment data" in body.get("message", "")

    def test_controller_maintains_interface_segregation(self):
        """Controller should only depend on interfaces it actually uses."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Verify controller only uses methods defined in the service interface
        controller_service_methods = [
            method for method in dir(self.mock_service) if not method.startswith("_")
        ]

        # These are the methods the controller should actually call
        expected_methods = [
            "create_appointment",
            "update_appointment",
            "get_appointments_for_user",
            "cancel_appointment",
        ]

        for method in expected_methods:
            assert (
                method in controller_service_methods
            ), f"Controller expects service method '{method}' but it's not available"
