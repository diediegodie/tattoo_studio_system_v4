"""
Database fixtures for integration testing.

This module provides database setup, session management, and transaction isolation
fixtures for integration tests.
"""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
# Set up test environment paths
from tests.config.test_paths import setup_test_environment

setup_test_environment()

try:
    # Quick availability check for Flask and SQLAlchemy. Do NOT import
    # application modules that may create engines at module import time.
    from datetime import datetime, timedelta, timezone

    import flask  # type: ignore
    import jwt
    from sqlalchemy import text  # type: ignore

    FLASK_IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Flask integration dependencies not available: {e}")
    FLASK_IMPORTS_AVAILABLE = False


@pytest.fixture(scope="session")
def test_database():
    """Create a test database for the session."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix=".db")

    # Configure test database URL
    test_db_url = f"sqlite:///{db_path}"

    yield test_db_url

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def db_session(app):
    """Create a database session with transaction isolation."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    # Create a new database session
    # Import SessionLocal lazily to ensure it is created against the test DB
    from app.db.session import SessionLocal as _SessionLocal

    session = _SessionLocal()

    # Ensure tables exist
    from app.db.base import Base

    Base.metadata.create_all(bind=session.get_bind())

    # Begin a transaction
    transaction = session.begin()

    try:
        yield session
    finally:
        # Always rollback the transaction to isolate tests, but only if
        # it's still active. Guarding prevents errors when the transaction
        # was already closed due to an earlier exception.
        try:
            if getattr(transaction, "is_active", False):
                transaction.rollback()
        except Exception:
            # As a last resort, call session.rollback()
            try:
                session.rollback()
            except Exception:
                pass
        finally:
            session.close()


@pytest.fixture
def database_transaction_isolator(db_session):
    """Provide database transaction isolation for tests."""

    def create_savepoint():
        """Create a savepoint for nested transaction isolation."""
        return db_session.begin_nested()

    def rollback_to_savepoint(savepoint):
        """Rollback to a specific savepoint."""
        savepoint.rollback()

    def commit_savepoint(savepoint):
        """Commit a savepoint."""
        savepoint.commit()

    return {
        "session": db_session,
        "create_savepoint": create_savepoint,
        "rollback_to_savepoint": rollback_to_savepoint,
        "commit_savepoint": commit_savepoint,
    }
