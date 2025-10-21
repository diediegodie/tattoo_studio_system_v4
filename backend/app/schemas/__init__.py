"""
Schemas package - Data Transfer Objects and validation.

This package contains DTOs that define the API contracts
and handle validation following SOLID principles.
"""

from .dtos import (
    AppointmentCreateRequest,
    AppointmentResponse,
    AppointmentUpdateRequest,
    AuthTokenResponse,
    ErrorResponse,
    InventoryItemCreateRequest,
    InventoryItemResponse,
    InventoryItemUpdateRequest,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)

__all__ = [
    # User DTOs
    "UserCreateRequest",
    "UserUpdateRequest",
    "UserResponse",
    # Appointment DTOs
    "AppointmentCreateRequest",
    "AppointmentUpdateRequest",
    "AppointmentResponse",
    # Inventory DTOs
    "InventoryItemCreateRequest",
    "InventoryItemUpdateRequest",
    "InventoryItemResponse",
    # Common DTOs
    "AuthTokenResponse",
    "ErrorResponse",
]
