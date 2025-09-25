"""
Domain entity fixtures following Single Responsibility Principle.

This module provides fixtures for creating domain entities used in tests,
ensuring consistent entity creation across the test suite.
"""

import os
# Import after ensuring paths are set up
import sys
from datetime import datetime, timedelta
from typing import Optional

import pytest

# Add the backend app directory to Python path
backend_path = os.path.join(os.path.dirname(__file__), "..", "..", "app")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

try:
    from tests.config import setup_test_imports

    setup_test_imports()
except ImportError:
    pass

try:
    from domain.entities import Appointment, InventoryItem, User

    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import domain modules: {e}")

    # Create mock classes for type hints when imports fail
    class User:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class Appointment:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class InventoryItem:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    IMPORTS_AVAILABLE = False


@pytest.fixture
def valid_user_data() -> dict:
    """Provide valid user data for domain entity creation."""
    return {
        "email": "test@example.com",
        "name": "Test User",
        "google_id": "google_123",
        "avatar_url": "https://example.com/avatar.jpg",
        "is_active": True,
    }


@pytest.fixture
def domain_user(valid_user_data) -> User:
    """Create a valid domain User entity."""
    return User(**valid_user_data)


@pytest.fixture
def domain_user_with_id(valid_user_data) -> User:
    """Create a domain User entity with ID (as if persisted)."""
    return User(
        id=123, created_at=datetime.now(), updated_at=datetime.now(), **valid_user_data
    )


@pytest.fixture
def inactive_domain_user(valid_user_data) -> User:
    """Create an inactive domain User entity."""
    valid_user_data["is_active"] = False
    return User(**valid_user_data)


@pytest.fixture
def google_user_data() -> dict:
    """Provide Google user info data for OAuth testing."""
    return {
        "id": "google_oauth_123",
        "email": "google.user@gmail.com",
        "name": "Google User",
        "picture": "https://lh3.googleusercontent.com/avatar.jpg",
    }


@pytest.fixture
def valid_appointment_data() -> dict:
    """Provide valid appointment data for domain entity creation."""
    return {
        "user_id": 1,
        "service_type": "Tattoo Session",
        "scheduled_date": datetime.now() + timedelta(days=1),
        "duration_minutes": 120,
        "price": 250.00,
        "status": "scheduled",
        "notes": "Test appointment for client",
    }


@pytest.fixture
def domain_appointment(valid_appointment_data) -> Appointment:
    """Create a valid domain Appointment entity."""
    return Appointment(**valid_appointment_data)


@pytest.fixture
def domain_appointment_with_id(valid_appointment_data) -> Appointment:
    """Create a domain Appointment entity with ID (as if persisted)."""
    return Appointment(
        id=456,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        **valid_appointment_data,
    )


@pytest.fixture
def completed_appointment(valid_appointment_data) -> Appointment:
    """Create a completed appointment entity."""
    valid_appointment_data["status"] = "completed"
    valid_appointment_data["scheduled_date"] = datetime.now() - timedelta(days=1)
    return Appointment(**valid_appointment_data)


@pytest.fixture
def cancelled_appointment(valid_appointment_data) -> Appointment:
    """Create a cancelled appointment entity."""
    valid_appointment_data["status"] = "cancelled"
    return Appointment(**valid_appointment_data)


@pytest.fixture
def valid_inventory_data() -> dict:
    """Provide valid inventory item data for domain entity creation."""
    return {
        "name": "Tattoo Ink - Black",
        "category": "Ink",
        "quantity": 50,
        "unit_price": 25.99,
        "minimum_stock": 10,
        "supplier": "Professional Tattoo Supply Co.",
    }


@pytest.fixture
def domain_inventory_item(valid_inventory_data) -> InventoryItem:
    """Create a valid domain InventoryItem entity."""
    return InventoryItem(**valid_inventory_data)


@pytest.fixture
def domain_inventory_item_with_id(valid_inventory_data) -> InventoryItem:
    """Create a domain InventoryItem entity with ID (as if persisted)."""
    return InventoryItem(
        id=789,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        **valid_inventory_data,
    )


@pytest.fixture
def low_stock_inventory_item(valid_inventory_data) -> InventoryItem:
    """Create an inventory item with low stock."""
    valid_inventory_data["quantity"] = 5  # Below minimum stock of 10
    return InventoryItem(**valid_inventory_data)


@pytest.fixture
def out_of_stock_inventory_item(valid_inventory_data) -> InventoryItem:
    """Create an out-of-stock inventory item."""
    valid_inventory_data["quantity"] = 0
    return InventoryItem(**valid_inventory_data)


# Collection fixtures for testing multiple entities
@pytest.fixture
def multiple_domain_users() -> list[User]:
    """Create multiple domain User entities for testing collections."""
    users_data = [
        {"id": 1, "email": "user1@example.com", "name": "User One", "is_active": True},
        {"id": 2, "email": "user2@example.com", "name": "User Two", "is_active": True},
        {
            "id": 3,
            "email": "user3@example.com",
            "name": "User Three",
            "is_active": False,
        },
    ]
    return [User(**data) for data in users_data]


@pytest.fixture
def multiple_domain_appointments(domain_user_with_id) -> list[Appointment]:
    """Create multiple domain Appointment entities for testing collections."""
    base_date = datetime.now()
    appointments_data = [
        {
            "id": 1,
            "user_id": domain_user_with_id.id,
            "service_type": "Small Tattoo",
            "scheduled_date": base_date + timedelta(days=1),
            "duration_minutes": 60,
            "price": 150.00,
            "status": "scheduled",
        },
        {
            "id": 2,
            "user_id": domain_user_with_id.id,
            "service_type": "Large Tattoo",
            "scheduled_date": base_date + timedelta(days=7),
            "duration_minutes": 240,
            "price": 500.00,
            "status": "confirmed",
        },
        {
            "id": 3,
            "user_id": domain_user_with_id.id,
            "service_type": "Touch-up",
            "scheduled_date": base_date - timedelta(days=30),
            "duration_minutes": 30,
            "price": 75.00,
            "status": "completed",
        },
    ]
    return [Appointment(**data) for data in appointments_data]


# Validation test fixtures
@pytest.fixture
def invalid_user_data_no_email() -> dict:
    """Provide invalid user data (missing email) for validation testing."""
    return {"name": "User Without Email", "is_active": True}


@pytest.fixture
def invalid_user_data_bad_email() -> dict:
    """Provide invalid user data (bad email format) for validation testing."""
    return {"email": "not-an-email", "name": "User With Bad Email", "is_active": True}


@pytest.fixture
def invalid_appointment_data_past_date() -> dict:
    """Provide invalid appointment data (past date) for validation testing."""
    return {
        "user_id": 1,
        "service_type": "Past Appointment",
        "scheduled_date": datetime.now() - timedelta(days=1),
        "duration_minutes": 60,
        "price": 100.00,
    }
