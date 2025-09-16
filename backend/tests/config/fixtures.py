"""
Complex test fixtures for the tattoo studio system tests.

This module contains advanced fixtures that were moved from conftest.py
to maintain file size limits and improve organization. These fixtures
include complex Flask application setups, database fixtures, and
service mocks that require more extensive configuration.

All fixtures follow SOLID principles and are designed for interface-based testing.
"""

import pytest
import os
import uuid
from unittest.mock import Mock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# =====================================================
# FLASK APPLICATION FIXTURES (COMPLEX)
# =====================================================


@pytest.fixture
def authenticated_client(app, mock_user, valid_jwt_token):
    """Test client with authenticated user context and JWT methods."""
    if hasattr(app, "test_client") and hasattr(app, "app_context"):
        with app.test_client() as client:
            with app.app_context():
                # Mock current_user for authentication
                from flask_login import login_user

                try:
                    login_user(mock_user)
                except Exception:
                    # If login_user fails, just continue - some tests don't need it
                    pass

                # Add JWT authentication methods
                auth_headers = {
                    "Authorization": f"Bearer {valid_jwt_token}",
                    "Content-Type": "application/json",
                }

                def authenticated_get(url, **kwargs):
                    kwargs.setdefault("headers", {}).update(auth_headers)
                    return client.get(url, **kwargs)

                def authenticated_post(url, **kwargs):
                    kwargs.setdefault("headers", {}).update(auth_headers)
                    return client.post(url, **kwargs)

                def authenticated_put(url, **kwargs):
                    kwargs.setdefault("headers", {}).update(auth_headers)
                    return client.put(url, **kwargs)

                def authenticated_delete(url, **kwargs):
                    kwargs.setdefault("headers", {}).update(auth_headers)
                    return client.delete(url, **kwargs)

                client.authenticated_get = authenticated_get
                client.authenticated_post = authenticated_post
                client.authenticated_put = authenticated_put
                client.authenticated_delete = authenticated_delete

                yield client
    else:
        # Mock client for when app is mocked
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.get_json.return_value = {"success": True}
        mock_client.post.return_value = mock_response
        mock_client.get.return_value = mock_response
        yield mock_client


@pytest.fixture
def jwt_authenticated_client(app, mock_user):
    """Test client with JWT authentication for API endpoints."""
    if hasattr(app, "test_client") and hasattr(app, "app_context"):
        with app.test_client() as client:
            with app.app_context():
                # Create JWT token for the mock user
                try:
                    from app.core.security import create_user_token

                    token = create_user_token(mock_user.id, mock_user.email)

                    # Set Authorization header for all requests
                    client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
                except Exception as e:
                    print(f"Warning: Could not create JWT token: {e}")
                    # Continue without JWT if creation fails

                yield client
    else:
        # Mock client for when app is mocked
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.get_json.return_value = {"success": True}
        mock_client.post.return_value = mock_response
        mock_client.get.return_value = mock_response
        yield mock_client


@pytest.fixture
def sessoes_authenticated_client(jwt_authenticated_client, app, mock_user):
    """Specialized authenticated client for sessoes controller tests."""
    with app.app_context():
        # Also set up Flask-Login authentication
        from flask_login import login_user

        try:
            login_user(mock_user)
        except Exception:
            # If login_user fails, just continue
            pass

    yield jwt_authenticated_client


@pytest.fixture
def request_context_with_user(app, mock_user):
    """Request context with authenticated user for tests that need current_user."""
    with app.test_request_context():
        with app.app_context():
            # Set up user in session if needed
            from flask import session

            try:
                session["user_id"] = mock_user.id
                session["user_email"] = mock_user.email
            except Exception:
                # If session setup fails, just continue
                pass
            yield


@pytest.fixture
def flask_context(app):
    """Combined Flask context manager for tests that need both app and request context."""
    with app.app_context():
        with app.test_request_context():
            yield


@pytest.fixture
def mock_flask_context():
    """Mock Flask context objects to prevent 'Working outside of request context' errors."""
    from unittest.mock import patch

    # Mock Flask local objects
    mock_patches = [
        patch("flask.request", new_callable=lambda: Mock()),
        patch("flask.session", new_callable=lambda: Mock()),
        patch("flask.g", new_callable=lambda: Mock()),
        patch("flask.current_app", new_callable=lambda: Mock()),
    ]

    # Start all patches
    started_patches = []
    for mock_patch in mock_patches:
        started_patch = mock_patch.start()
        started_patches.append(started_patch)

    try:
        yield
    finally:
        # Stop all patches
        for started_patch in started_patches:
            started_patch.stop()


@pytest.fixture
def test_context_with_client(app, mock_user):
    """Test context with Flask app context, request context, and test client."""
    from unittest.mock import patch

    with app.app_context():
        with app.test_request_context():
            # Mock Flask local objects to prevent context errors
            with patch("flask.request") as mock_request, patch(
                "flask.session"
            ) as mock_session, patch("flask.g") as mock_g, patch(
                "flask.current_app", app
            ):
                # Configure mocks
                mock_request.method = "GET"
                mock_session.__setitem__ = Mock()
                mock_session.__getitem__ = Mock(return_value=None)
                mock_g.user = mock_user

                # Create test client
                client = app.test_client()

                yield {
                    "app": app,
                    "client": client,
                    "request": mock_request,
                    "session": mock_session,
                    "g": mock_g,
                    "user": mock_user,
                }


# =====================================================
# SHARED MOCK FIXTURES FOR COMMON PATTERNS
# =====================================================


@pytest.fixture
def mock_query_chain():
    """Create a mock database query chain for common SQLAlchemy patterns."""
    mock_query = Mock()
    mock_query.filter = Mock(return_value=mock_query)
    mock_query.order_by = Mock(return_value=mock_query)
    mock_query.options = Mock(return_value=mock_query)
    mock_query.all = Mock(return_value=[])
    mock_query.first = Mock(return_value=None)
    mock_query.count = Mock(return_value=0)
    mock_query.delete = Mock()
    return mock_query


@pytest.fixture
def mock_db_with_query(mock_query_chain):
    """Create a mock database session with query chain."""
    mock_db = Mock()
    mock_db.query = Mock(return_value=mock_query_chain)
    mock_db.add = Mock()
    mock_db.commit = Mock()
    mock_db.rollback = Mock()
    mock_db.refresh = Mock()
    mock_db.close = Mock()
    return mock_db


@pytest.fixture
def mock_service():
    """Create a generic mock service for testing."""
    service = Mock()
    # Common service methods
    service.create = Mock()
    service.update = Mock()
    service.delete = Mock()
    service.get_by_id = Mock()
    service.list_all = Mock()
    return service


@pytest.fixture
def mock_template_renderer():
    """Create a mock template renderer for Flask controller testing."""
    mock_render = Mock()
    mock_render.return_value = "<html>Mock template</html>"
    return mock_render


@pytest.fixture
def mock_session_local(mock_db_with_query):
    """Create a mock SessionLocal for database session mocking."""
    mock_session_local = Mock()
    mock_session_local.return_value = mock_db_with_query
    return mock_session_local


# =====================================================
# DATABASE FIXTURES
# =====================================================


@pytest.fixture
def sqlite_db():
    """Create an in-memory SQLite database for fast unit tests."""
    engine = create_engine("sqlite:///:memory:")

    # Import models and create tables
    try:
        import importlib

        db_base_mod = importlib.import_module("db.base")
        Base = getattr(db_base_mod, "Base", None)
        if Base:
            Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Warning: Could not create SQLite tables: {e}")

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def postgres_db():
    """Create a temporary PostgreSQL database for integration tests."""
    # Get PostgreSQL connection details from environment
    pg_host = os.environ.get("POSTGRES_HOST", "localhost")
    pg_port = os.environ.get("POSTGRES_PORT", "5432")
    pg_user = os.environ.get("POSTGRES_USER", "admin")
    pg_[REDACTED_PASSWORD]"POSTGRES_PASSWORD", "secret123")
    pg_database = os.environ.get("POSTGRES_DB", "tattoo_studio")

    # Create a temporary database name
    test_db_name = f"tattoo_studio_test_{str(uuid.uuid4()).replace('-', '')[:8]}"

    # Connection URL for the main database (to create the test database)
    main_db_url = (
        f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
    )

    # Create engine for the main database
    main_engine = create_engine(main_db_url, isolation_level="AUTOCOMMIT")

    try:
        # Create the temporary test database
        with main_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE {test_db_name}"))

        # Connection URL for the test database
        test_db_url = (
            f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{test_db_name}"
        )

        # Create engine for the test database
        test_engine = create_engine(test_db_url)

        # Create all tables
        try:
            import importlib

            db_base_mod = importlib.import_module("db.base")
            Base = getattr(db_base_mod, "Base", None)
            if Base:
                Base.metadata.create_all(bind=test_engine)
        except Exception as e:
            print(f"Warning: Could not create tables in test database: {e}")

        # Create a session factory for the test database
        TestSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=test_engine
        )

        # Create and yield a session
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()
            test_engine.dispose()

    finally:
        # Clean up: drop the temporary database
        try:
            with main_engine.connect() as conn:
                # Terminate any active connections to the test database
                conn.execute(
                    text(
                        f"""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = '{test_db_name}' AND pid <> pg_backend_pid()
                """
                    )
                )
                # Drop the database
                conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
        except Exception as e:
            print(f"Warning: Could not drop test database {test_db_name}: {e}")
        finally:
            main_engine.dispose()


# =====================================================
# GOOGLE CALENDAR MOCK FIXTURES
# =====================================================


@pytest.fixture
def mock_google_calendar_service():
    """Mock Google Calendar service for testing."""
    service = Mock()

    # Mock events list
    mock_events = {
        "items": [
            {
                "id": "test_event_1",
                "summary": "Test Event 1",
                "start": {"dateTime": "2023-12-01T10:00:00Z"},
                "end": {"dateTime": "2023-12-01T11:00:00Z"},
            },
            {
                "id": "test_event_2",
                "summary": "Test Event 2",
                "start": {"dateTime": "2023-12-01T14:00:00Z"},
                "end": {"dateTime": "2023-12-01T15:00:00Z"},
            },
        ]
    }

    service.events.return_value.list.return_value.execute.return_value = mock_events
    service.events.return_value.insert.return_value.execute.return_value = {
        "id": "new_event_123",
        "summary": "Created Event",
    }

    return service


# =====================================================
# COMPLEX CLIENT FIXTURES
# =====================================================


@pytest.fixture
def login_client(app):
    """Create a test client with Flask-Login session authentication."""
    if hasattr(app, "test_client") and hasattr(app, "app_context"):
        # Create database tables in the app's database engine
        try:
            import importlib

            # Import models to populate Base.metadata
            importlib.import_module("db.base")

            db_session_mod = importlib.import_module("db.session")
            Base = getattr(db_session_mod, "Base", None)
            if Base:
                try:
                    from app.db.session import get_engine

                    Base.metadata.create_all(bind=get_engine())
                except ImportError:
                    # Fallback if db.session import fails
                    from sqlalchemy import create_engine

                    engine = create_engine(
                        os.environ.get("DATABASE_URL", "sqlite:///:memory:")
                    )
                    Base.metadata.create_all(bind=engine)

            # Create a test user in the database
            try:
                db_session_mod = importlib.import_module("db.session")
                db_base_mod = importlib.import_module("db.base")

                SessionLocal = getattr(db_session_mod, "SessionLocal", None)
                User = getattr(db_base_mod, "User", None)

                if SessionLocal and User:
                    db = SessionLocal()
                    try:
                        # Check if test user already exists
                        existing_user = db.query(User).filter_by(id=1).first()
                        if not existing_user:
                            test_user = User(
                                id=1,
                                email="test@example.com",
                                name="Test User",
                                google_id="test_google_id",
                                is_active=True,
                            )
                            db.add(test_user)
                            db.commit()
                    except Exception as e:
                        print(f"Warning: Could not create test user: {e}")
                        db.rollback()
                    finally:
                        db.close()
            except Exception as e:
                print(f"Warning: Could not import database modules: {e}")

        except Exception as e:
            print(f"Warning: Could not create tables in login_client: {e}")

        with app.test_client() as client:
            with app.app_context():
                # Set up a mock user session for Flask-Login
                with client.session_transaction() as sess:
                    sess["user_id"] = 1
                    sess["_user_id"] = "1"  # Flask-Login specific
                    sess["user_email"] = "test@example.com"
                yield client
    else:
        # Mock client for when app is mocked
        mock_client = Mock()
        yield mock_client


@pytest.fixture
def jwt_client(app, valid_jwt_token):
    """Create a test client with JWT authentication."""
    if hasattr(app, "test_client") and hasattr(app, "app_context"):
        with app.test_client() as client:
            with app.app_context():
                # Create a custom client class that includes JWT authentication
                class JWTAuthenticatedClient:
                    def __init__(self, client, token):
                        self.client = client
                        self.auth_headers = {
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                        }

                    def get(self, *args, **kwargs):
                        kwargs.setdefault("headers", {}).update(self.auth_headers)
                        return self.client.get(*args, **kwargs)

                    def post(self, *args, **kwargs):
                        kwargs.setdefault("headers", {}).update(self.auth_headers)
                        return self.client.post(*args, **kwargs)

                    def put(self, *args, **kwargs):
                        kwargs.setdefault("headers", {}).update(self.auth_headers)
                        return self.client.put(url, **kwargs)

                    def patch(self, *args, **kwargs):
                        kwargs.setdefault("headers", {}).update(self.auth_headers)
                        return self.client.patch(*args, **kwargs)

                    def delete(self, *args, **kwargs):
                        kwargs.setdefault("headers", {}).update(self.auth_headers)
                        return self.client.delete(*args, **kwargs)

                yield JWTAuthenticatedClient(client, valid_jwt_token)
    else:
        # Mock client for when app is mocked
        mock_client = Mock()
        yield mock_client
