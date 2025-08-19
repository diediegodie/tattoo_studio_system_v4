"""
Appointment controller following SOLID principles.

This controller demonstrates:
- Single Responsibility: Handles only HTTP concerns for appointments
- Dependency Inversion: Depends on service interfaces
- Open/Closed: New endpoints can be added without modifying existing code
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from typing import Dict, Any

from services.appointment_service import AppointmentService
from schemas.dtos import (
    AppointmentCreateRequest,
    AppointmentUpdateRequest,
    AppointmentResponse,
    ErrorResponse,
)
from core.auth_decorators import jwt_required, get_current_user


appointment_bp = Blueprint("appointments", __name__, url_prefix="/api/appointments")


class AppointmentController:
    """Controller for appointment-related HTTP endpoints.

    Follows SOLID principles by:
    - Focusing only on HTTP request/response handling (Single Responsibility)
    - Using dependency injection for services (Dependency Inversion)
    - Being easily testable with mocked services (Liskov Substitution)
    """

    def __init__(self, appointment_service: AppointmentService):
        self.appointment_service = appointment_service

    def create_appointment(self) -> Dict[str, Any]:
        """Create a new appointment."""
        try:
            data = request.get_json() or {}

            # Create request DTO
            create_request = AppointmentCreateRequest(
                user_id=data.get("user_id"),
                service_type=data.get("service_type"),
                scheduled_date=datetime.fromisoformat(data.get("scheduled_date")),
                duration_minutes=data.get("duration_minutes"),
                price=data.get("price"),
                notes=data.get("notes"),
            )

            # Delegate to service
            response = self.appointment_service.create_appointment(create_request)

            return {
                "success": True,
                "data": {
                    "id": response.id,
                    "user_id": response.user_id,
                    "service_type": response.service_type,
                    "scheduled_date": response.scheduled_date.isoformat(),
                    "duration_minutes": response.duration_minutes,
                    "price": response.price,
                    "status": response.status,
                    "notes": response.notes,
                    "created_at": response.created_at.isoformat(),
                },
            }

        except ValueError as e:
            error = ErrorResponse.validation_error(str(e))
            return {
                "success": False,
                "error": error.error,
                "message": error.message,
            }, 400
        except Exception as e:
            error = ErrorResponse.server_error(str(e))
            return {
                "success": False,
                "error": error.error,
                "message": error.message,
            }, 500

    def get_appointment(self, appointment_id: int) -> Dict[str, Any]:
        """Get a specific appointment."""
        try:
            # This would call appointment_service.get_appointment_by_id()
            # For now, return placeholder
            return {
                "success": True,
                "data": {
                    "id": appointment_id,
                    "message": "Appointment retrieval not yet implemented",
                },
            }
        except Exception as e:
            error = ErrorResponse.server_error(str(e))
            return {
                "success": False,
                "error": error.error,
                "message": error.message,
            }, 500

    def update_appointment(self, appointment_id: int) -> Dict[str, Any]:
        """Update an existing appointment."""
        try:
            data = request.get_json() or {}

            # Create update request DTO
            update_request = AppointmentUpdateRequest(
                scheduled_date=(
                    datetime.fromisoformat(data["scheduled_date"])
                    if data.get("scheduled_date")
                    else None
                ),
                duration_minutes=data.get("duration_minutes"),
                price=data.get("price"),
                status=data.get("status"),
                notes=data.get("notes"),
            )

            # Delegate to service
            response = self.appointment_service.update_appointment(
                appointment_id, update_request
            )

            if response:
                return {
                    "success": True,
                    "data": {
                        "id": response.id,
                        "user_id": response.user_id,
                        "service_type": response.service_type,
                        "scheduled_date": response.scheduled_date.isoformat(),
                        "duration_minutes": response.duration_minutes,
                        "price": response.price,
                        "status": response.status,
                        "notes": response.notes,
                    },
                }
            else:
                error = ErrorResponse.not_found("Appointment")
                return {
                    "success": False,
                    "error": error.error,
                    "message": error.message,
                }, 404

        except ValueError as e:
            error = ErrorResponse.validation_error(str(e))
            return {
                "success": False,
                "error": error.error,
                "message": error.message,
            }, 400
        except Exception as e:
            error = ErrorResponse.server_error(str(e))
            return {
                "success": False,
                "error": error.error,
                "message": error.message,
            }, 500

    def get_user_appointments(self, user_id: int) -> Dict[str, Any]:
        """Get all appointments for a specific user."""
        try:
            appointments = self.appointment_service.get_appointments_for_user(user_id)

            return {
                "success": True,
                "data": [
                    {
                        "id": apt.id,
                        "service_type": apt.service_type,
                        "scheduled_date": apt.scheduled_date.isoformat(),
                        "duration_minutes": apt.duration_minutes,
                        "price": apt.price,
                        "status": apt.status,
                        "notes": apt.notes,
                    }
                    for apt in appointments
                ],
            }
        except Exception as e:
            error = ErrorResponse.server_error(str(e))
            return {
                "success": False,
                "error": error.error,
                "message": error.message,
            }, 500

    def cancel_appointment(self, appointment_id: int) -> Dict[str, Any]:
        """Cancel an appointment."""
        try:
            data = request.get_json() or {}
            reason = data.get("reason")

            success = self.appointment_service.cancel_appointment(
                appointment_id, reason
            )

            if success:
                return {
                    "success": True,
                    "message": "Appointment cancelled successfully",
                }
            else:
                error = ErrorResponse.not_found("Appointment")
                return {
                    "success": False,
                    "error": error.error,
                    "message": error.message,
                }, 404

        except ValueError as e:
            error = ErrorResponse.validation_error(str(e))
            return {
                "success": False,
                "error": error.error,
                "message": error.message,
            }, 400
        except Exception as e:
            error = ErrorResponse.server_error(str(e))
            return {
                "success": False,
                "error": error.error,
                "message": error.message,
            }, 500


# Note: These would typically be registered in a dependency injection container
# For now, we'll show the structure without the actual DI setup


@appointment_bp.route("", methods=["POST"])
@jwt_required
def create_appointment():
    """Create appointment endpoint."""
    # In a real implementation, the controller would be injected with dependencies
    # controller = get_appointment_controller()  # From DI container
    # return jsonify(controller.create_appointment())
    return jsonify({"message": "Appointment creation endpoint - DI setup needed"})


@appointment_bp.route("/<int:appointment_id>", methods=["GET"])
@jwt_required
def get_appointment(appointment_id: int):
    """Get appointment endpoint."""
    return jsonify({"message": f"Get appointment {appointment_id} - DI setup needed"})


@appointment_bp.route("/<int:appointment_id>", methods=["PUT"])
@jwt_required
def update_appointment(appointment_id: int):
    """Update appointment endpoint."""
    return jsonify(
        {"message": f"Update appointment {appointment_id} - DI setup needed"}
    )


@appointment_bp.route("/user/<int:user_id>", methods=["GET"])
@jwt_required
def get_user_appointments(user_id: int):
    """Get user appointments endpoint."""
    return jsonify(
        {"message": f"Get appointments for user {user_id} - DI setup needed"}
    )


@appointment_bp.route("/<int:appointment_id>/cancel", methods=["POST"])
@jwt_required
def cancel_appointment(appointment_id: int):
    """Cancel appointment endpoint."""
    return jsonify(
        {"message": f"Cancel appointment {appointment_id} - DI setup needed"}
    )
