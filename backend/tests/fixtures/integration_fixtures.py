"""
Integration test fixtures and utilities for Flask testing.

This module provides Flask application configuration, test client setup,
database transaction isolation, and authentication fixtures for integration tests.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Set up test environment paths
from tests.config.test_paths import setup_test_environment

setup_test_environment()

try:
    # Quick availability check for Flask and SQLAlchemy. Do NOT import
    # application modules that may create engines at module import time.
    import flask  # type: ignore
    from sqlalchemy import text  # type: ignore
    import jwt
    from datetime import datetime, timedelta, timezone

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
def app(test_database):
    """Create a Flask application configured for testing."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    # Configure environment for testing so create_app() and db.session pick up the
    # test database and secrets. Some versions of create_app accepted a config
    # dict; newer versions take no args, so we set env vars and call create_app().
    os.environ["DATABASE_URL"] = test_database
    os.environ["FLASK_SECRET_KEY"] = "test-secret-key"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"
    # After setting DATABASE_URL, reload db.session so its engine/SessionLocal
    # are created against the test database URL (important because db.session
    # may have been imported earlier during test collection).
    import importlib

    # Ensure DATABASE_URL is set before importing application modules so
    # any lazy engine creation or imports in app.main/db.session pick up the
    # test database. Reload db.session after setting env var below.
    try:
        # Import create_app lazily after env is set
        from importlib import import_module

        import_module("app.app")
        import_module("app.app")
    except Exception:
        # ignore for environments where app package isn't importable
        pass

    # Reload session module so it reads the test DATABASE_URL when later used
    try:
        import app.db.session as db_session_mod

        importlib.reload(db_session_mod)
    except Exception:
        pass

    # Now import the app factory
    from app.app import create_app

    app = create_app()

    # Fix template/static paths for test environment: create_app() uses
    # absolute Docker paths (/app/frontend/...), which are not present during
    # local pytest runs. Point Flask to the repo's frontend folders so
    # Jinja can find templates and static assets.
    from pathlib import Path

    repo_root = Path(__file__).parent.parent.parent.parent.resolve()
    templates_path = repo_root / "frontend" / "templates"
    static_path = repo_root / "frontend" / "assets"

    if templates_path.exists():
        app.template_folder = str(templates_path)
        # Ensure the jinja loader search path includes the repo templates
        try:
            loader = getattr(app, "jinja_loader", None)
            # Guard against None loader and ensure searchpath exists and is handled safely
            if loader is not None and hasattr(loader, "searchpath"):
                sp = loader.searchpath
                if sp is None:
                    # If searchpath is None, set a new list with our templates path
                    try:
                        loader.searchpath = [str(templates_path)]
                    except Exception:
                        # Non-fatal for custom loaders that don't allow assignment
                        pass
                else:
                    try:
                        # Prefer to insert into a mutable sequence
                        sp.insert(0, str(templates_path))
                    except Exception:
                        # Fallback: replace with a new list combining paths
                        try:
                            loader.searchpath = [str(templates_path)] + list(sp)
                        except Exception:
                            # Non-fatal for environments with custom loaders
                            pass
        except Exception:
            # Non-fatal for environments with custom loaders
            pass

    if static_path.exists():
        app.static_folder = str(static_path)

    # During tests surface internal exceptions to make debugging easier
    app.config["PROPAGATE_EXCEPTIONS"] = True

    # Explicit test config applied to the Flask app object
    app.config.update(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
        }
    )

    # Create application context and ensure the db tables exist on the
    # SessionLocal/engine that the application code uses.
    with app.app_context():
        from app.db.base import Base

        # Import the session module lazily (should now honor DATABASE_URL)
        from app.db import session as db_session_mod

        # Use the engine from db.session (reloaded above) so tests and
        # application share the same database connection. Prefer calling
        # get_engine() when available so we get a real SQLAlchemy Engine
        # (the session module may expose a proxy for compatibility).
        if hasattr(db_session_mod, "get_engine"):
            test_engine = db_session_mod.get_engine()
        else:
            test_engine = getattr(db_session_mod, "engine", None)

        if test_engine is None:
            # Fallback: create a direct engine to the test DB
            from sqlalchemy import create_engine

            test_engine = create_engine(test_database)

        # Defensive: also create a direct engine from the same URL and
        # create tables there too. This helps when there are subtle
        # differences between proxied engines and direct ones.
        try:
            from sqlalchemy import create_engine

            direct_engine = create_engine(test_database)
        except Exception:
            direct_engine = test_engine

        # Log engine URLs for debugging
        try:
            print(
                f"[DEBUG] session engine URL: {getattr(test_engine, 'url', test_engine)}"
            )
            print(
                f"[DEBUG] direct engine URL: {getattr(direct_engine, 'url', direct_engine)}"
            )
        except Exception:
            pass

        Base.metadata.create_all(test_engine)
        if direct_engine is not test_engine:
            Base.metadata.create_all(direct_engine)

        # Defensive: If other modules already imported their own db.session
        # (likely during test collection), create tables on those engines too.
        import sys

        for mod_name, mod in list(sys.modules.items()):
            if mod_name.endswith(".db.session") or mod_name == "db.session":
                try:
                    eng = getattr(mod, "get_engine", None)
                    if callable(eng):
                        eng = eng()
                    else:
                        eng = getattr(mod, "engine", None)
                    if eng is not None:
                        try:
                            Base.metadata.create_all(eng)
                            print(
                                f"[DEBUG] Created tables on engine from module {mod_name}"
                            )
                        except Exception:
                            pass
                except Exception:
                    pass

        yield app

        # Cleanup tables
        Base.metadata.drop_all(test_engine)


@pytest.fixture(scope="function")
def client(app):
    """Create a test client for the Flask application."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    return app.test_client()


@pytest.fixture(scope="function")
def runner(app):
    """Create a test runner for the Flask application."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    return app.test_cli_runner()


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
def auth_headers():
    """Create authentication headers for protected endpoints."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    # Create a mock JWT token
    payload = {
        "user_id": 123,
        "email": "test@example.com",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }

    # Import jwt locally to avoid relying on a module-level name that may be
    # unbound during static analysis or in environments where top-level imports
    # were skipped.
    try:
        import jwt as _jwt  # local import
    except Exception:
        pytest.skip("PyJWT is not available in the test environment")

    token = _jwt.encode(payload, "test-jwt-secret", algorithm="HS256")
    # PyJWT may return bytes in some versions; ensure we return a str token.
    if isinstance(token, bytes):
        token = token.decode("utf-8")

    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@pytest.fixture
def mock_authenticated_user():
    """Create a mock authenticated user for testing."""
    user = Mock()
    user.id = 123
    user.email = "test@example.com"
    user.name = "Test User"
    user.google_id = "google123"
    user.avatar_url = "https://example.com/avatar.jpg"
    user.is_active = True
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def authenticated_client(client, db_session, mock_authenticated_user):
    """Create an authenticated test client with Flask-Login session."""
    if not FLASK_IMPORTS_AVAILABLE:
        pytest.skip("Flask integration dependencies not available")

    # Create a test user in the database
    from app.db.base import User

    test_user = User(
        name="Test User",
        email="test@example.com",
        google_id="test123",
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    # Create a custom client class that includes authentication methods
    class AuthenticatedClient:
        def __init__(self, client, user, mock_user):
            self.client = client
            self.user = user
            self.mock_user = mock_user

        def get(self, *args, **kwargs):
            with patch("flask_login.current_user", self.mock_user):
                self.mock_user.is_authenticated = True
                self.mock_user.id = self.user.id
                with self.client.application.test_request_context():
                    with self.client.session_transaction() as sess:
                        sess["user_id"] = self.user.id
                        sess["_user_id"] = str(self.user.id)
                        sess["logged_in"] = True
                return self.client.get(*args, **kwargs)

        def post(self, *args, **kwargs):
            with patch("flask_login.current_user", self.mock_user):
                self.mock_user.is_authenticated = True
                self.mock_user.id = self.user.id
                with self.client.application.test_request_context():
                    with self.client.session_transaction() as sess:
                        sess["user_id"] = self.user.id
                        sess["_user_id"] = str(self.user.id)
                        sess["logged_in"] = True
                return self.client.post(*args, **kwargs)

        def put(self, *args, **kwargs):
            with patch("flask_login.current_user", self.mock_user):
                self.mock_user.is_authenticated = True
                self.mock_user.id = self.user.id
                with self.client.application.test_request_context():
                    with self.client.session_transaction() as sess:
                        sess["user_id"] = self.user.id
                        sess["_user_id"] = str(self.user.id)
                        sess["logged_in"] = True
                return self.client.put(*args, **kwargs)

        def patch(self, *args, **kwargs):
            with patch("flask_login.current_user", self.mock_user):
                self.mock_user.is_authenticated = True
                self.mock_user.id = self.user.id
                with self.client.application.test_request_context():
                    with self.client.session_transaction() as sess:
                        sess["user_id"] = self.user.id
                        sess["_user_id"] = str(self.user.id)
                        sess["logged_in"] = True
                return self.client.patch(*args, **kwargs)

        def delete(self, *args, **kwargs):
            with patch("flask_login.current_user", self.mock_user):
                self.mock_user.is_authenticated = True
                self.mock_user.id = self.user.id
                with self.client.application.test_request_context():
                    with self.client.session_transaction() as sess:
                        sess["user_id"] = self.user.id
                        sess["_user_id"] = str(self.user.id)
                        sess["logged_in"] = True
                return self.client.delete(*args, **kwargs)

        # Add convenience methods for authenticated requests
        def authenticated_get(self, *args, **kwargs):
            return self.get(*args, **kwargs)

        def authenticated_post(self, *args, **kwargs):
            return self.post(*args, **kwargs)

        def authenticated_put(self, *args, **kwargs):
            return self.put(*args, **kwargs)

        def authenticated_patch(self, *args, **kwargs):
            return self.patch(*args, **kwargs)

        def authenticated_delete(self, *args, **kwargs):
            return self.delete(*args, **kwargs)

    return AuthenticatedClient(client, test_user, mock_authenticated_user)


@pytest.fixture
def sample_client_data():
    """Create sample client data for testing."""
    return {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "+1234567890",
        "submission_id": "jotform_123456",
        "birth_date": "1990-01-15",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def sample_appointment_data():
    """Create sample appointment data for testing."""
    return {
        "client_id": 1,
        "date": "2024-12-25",
        "time": "14:00",
        "service": "Tatuagem Pequena",
        "status": "agendado",
        "notes": "First tattoo session",
    }


@pytest.fixture
def mock_jotform_response():
    """Create mock JotForm API response data."""
    return {
        "responseCode": 200,
        "message": "success",
        "content": [
            {
                "id": "123456",
                "form_id": "242871033645151",
                "ip": "192.168.1.1",
                "created_at": "2024-01-15 10:30:00",
                "status": "ACTIVE",
                "answers": {
                    "3": {"answer": "John Doe"},
                    "4": {"answer": "john.doe@example.com"},
                    "5": {"answer": "+1234567890"},
                    "6": {"answer": "1990-01-15"},
                },
            }
        ],
    }


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


class FlaskTestResponse:
    """Helper class for testing Flask responses."""

    @staticmethod
    def assert_json_response(response, expected_status=200):
        """Assert that response is JSON with expected status."""
        assert response.status_code == expected_status
        assert response.content_type == "application/json"
        return response.get_json()

    @staticmethod
    def assert_html_response(response, expected_status=200):
        """Assert that response is HTML with expected status."""
        assert response.status_code == expected_status
        assert "text/html" in response.content_type
        return response.get_data(as_text=True)

    @staticmethod
    def assert_redirect_response(response, expected_location=None):
        """Assert that response is a redirect."""
        assert response.status_code in [301, 302, 303, 307, 308]
        if expected_location:
            assert expected_location in response.location
        return response.location
