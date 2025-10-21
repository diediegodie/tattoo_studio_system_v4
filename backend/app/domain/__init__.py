"""
Domain package - Pure business logic layer.

This package contains:
- entities.py: Domain entities with business logic
- interfaces.py: Repository and service contracts

Following SOLID principles:
- Single Responsibility: Each module has one purpose
- Open/Closed: Extensible without modification
- Dependency Inversion: Interfaces define contracts
"""

from .entities import Appointment, InventoryItem, User
from .interfaces import (
    IAppointmentReader,
    IAppointmentRepository,
    IAppointmentWriter,
    IInventoryReader,
    IInventoryRepository,
    IInventoryWriter,
    IUserReader,
    IUserRepository,
    IUserWriter,
)

__all__ = [
    # Domain entities
    "User",
    "Appointment",
    "InventoryItem",
    # Repository interfaces
    "IUserRepository",
    "IAppointmentRepository",
    "IInventoryRepository",
    # Segregated interfaces
    "IUserReader",
    "IUserWriter",
    "IAppointmentReader",
    "IAppointmentWriter",
    "IInventoryReader",
    "IInventoryWriter",
]
