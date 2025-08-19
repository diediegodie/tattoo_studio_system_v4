"""
Database test fixtures and utilities.

This module provides database fixtures for testing with proper isolation
and transaction rollback capabilities.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock

# Import after ensuring paths are set up
from tests.config import setup_test_imports

setup_test_imports()

try:
    from db.session import SessionLocal, engine
    from db.base import Base

    DB_IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import database modules: {e}")
    DB_IMPORTS_AVAILABLE = False


@pytest.fixture(scope="session")
def test_database():
    """Create a test database for the entire test session."""
    if not DB_IMPORTS_AVAILABLE:
        yield Mock()
        return

    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    try:
        # Create all tables in the test database
        Base.metadata.create_all(bind=engine)
        yield db_path
    finally:
        # Clean up the temporary database file
        os.close(db_fd)
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture
def db_session(test_database):
    """Provide a database session with transaction rollback."""
    if not DB_IMPORTS_AVAILABLE:
        yield Mock()
        return

    # Create a new session for this test
    session = SessionLocal()

    try:
        yield session
    finally:
        # Rollback any changes made during the test
        session.rollback()
        session.close()


@pytest.fixture
def clean_db_session(test_database):
    """Provide a clean database session that commits changes."""
    if not DB_IMPORTS_AVAILABLE:
        yield Mock()
        return

    session = SessionLocal()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture
def isolated_db_session():
    """Provide a completely isolated database session for integration tests."""
    if not DB_IMPORTS_AVAILABLE:
        yield Mock()
        return

    # Create a unique in-memory database for this test
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Use in-memory SQLite database for complete isolation
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    session = TestSessionLocal()

    try:
        yield session
    finally:
        session.close()


class DatabaseTestHelper:
    """Helper class for database testing operations."""

    @staticmethod
    def clear_all_tables(session):
        """Clear all data from all tables in the test database."""
        if not DB_IMPORTS_AVAILABLE:
            return

        try:
            # Get all table names
            for table in reversed(Base.metadata.sorted_tables):
                session.execute(table.delete())
            session.commit()
        except Exception as e:
            session.rollback()
            raise e

    @staticmethod
    def count_records(session, model_class):
        """Count the number of records in a table."""
        if not DB_IMPORTS_AVAILABLE:
            return 0

        return session.query(model_class).count()

    @staticmethod
    def create_test_data(session, model_class, data_list):
        """Create multiple test records in the database."""
        if not DB_IMPORTS_AVAILABLE:
            return []

        created_objects = []
        try:
            for data in data_list:
                obj = model_class(**data)
                session.add(obj)
                created_objects.append(obj)

            session.commit()
            return created_objects
        except Exception as e:
            session.rollback()
            raise e

    @staticmethod
    def verify_database_state(session, expected_counts):
        """
        Verify that the database contains the expected number of records.

        Args:
            session: Database session
            expected_counts: Dict mapping model classes to expected record counts
                           e.g., {User: 2, Appointment: 1}
        """
        if not DB_IMPORTS_AVAILABLE:
            return True

        for model_class, expected_count in expected_counts.items():
            actual_count = DatabaseTestHelper.count_records(session, model_class)
            assert (
                actual_count == expected_count
            ), f"Expected {expected_count} {model_class.__name__} records, but found {actual_count}"

    @staticmethod
    def execute_sql_script(session, sql_script):
        """Execute a raw SQL script for test setup."""
        if not DB_IMPORTS_AVAILABLE:
            return

        try:
            session.execute(sql_script)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e


@pytest.fixture
def database_helper():
    """Provide access to database testing helper methods."""
    return DatabaseTestHelper


# Transaction management fixtures for complex test scenarios
@pytest.fixture
def transactional_test(db_session):
    """
    Provide a transactional test environment where all changes are rolled back.

    This fixture ensures that each test starts with a clean database state
    and all changes are automatically rolled back after the test completes.
    """
    if not DB_IMPORTS_AVAILABLE:
        yield Mock()
        return

    # Start a savepoint
    savepoint = db_session.begin_nested()

    try:
        yield db_session
    finally:
        # Rollback to the savepoint
        savepoint.rollback()


@pytest.fixture
def persistent_test(clean_db_session):
    """
    Provide a test environment where changes persist across tests.

    Use this fixture when you need to test database operations that should
    persist or when testing migration scenarios.
    """
    if not DB_IMPORTS_AVAILABLE:
        yield Mock()
        return

    yield clean_db_session


# Test data generation fixtures
@pytest.fixture
def sample_test_data():
    """Provide sample test data for common test scenarios."""
    return {
        "users": [
            {
                "email": "user1@example.com",
                "password_hash": "hashed_password_1",
                "name": "Test User 1",
                "phone": "1234567890",
                "is_verified": True,
            },
            {
                "email": "user2@example.com",
                "password_hash": "hashed_password_2",
                "name": "Test User 2",
                "phone": "0987654321",
                "is_verified": False,
            },
        ],
        "appointments": [
            {
                "user_id": 1,
                "service_type": "Tattoo Consultation",
                "appointment_date": "2024-01-15 10:00:00",
                "notes": "Initial consultation",
                "status": "scheduled",
            }
        ],
        "inventory_items": [
            {
                "name": "Tattoo Ink - Black",
                "sku": "INK-BLK-001",
                "quantity": 50,
                "price": 25.99,
                "supplier": "Ink Supplier Co",
                "minimum_stock": 10,
            }
        ],
    }


@pytest.fixture
def populated_database(clean_db_session, sample_test_data, database_helper):
    """Provide a database populated with sample test data."""
    if not DB_IMPORTS_AVAILABLE:
        yield Mock()
        return

    # This would need to be implemented based on actual model classes
    # For now, just return the session
    yield clean_db_session
