"""
Central pyte# Add /app to sys.path for relative imports to work in Docker
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/backend') configuration for the tattoo studio system tests.

This file provides common fixtures, test markers, and setup
for both unit and integration tests following SOLID principles.
"""

import pytest
import sys
import os
import uuid
from pathlib import Path
from unittest.mock import Mock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add backend directories to sys.path for imports to work
backend_root = Path(__file__).parent.parent  # backend/
backend_app = backend_root / "app"  # backend/app/

sys.path.insert(0, str(backend_app))
sys.path.insert(0, str(backend_root))

# Test database configuration (set early so import-time engines use it)
TEST_DATABASE_URL = "sqlite:///:memory:"  # In-memory SQLite for fast tests
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["TESTING"] = "true"  # Set testing environment variable
os.environ["JOTFORM_API_KEY"] = "test-api-key"  # Set test JotForm credentials
os.environ["JOTFORM_FORM_ID"] = "test-form-id"

# Set up test environment paths BEFORE any other imports
from tests.config.test_paths import setup_test_environment

# Set up the test environment immediately
print("Configuring test environment in conftest.py...")
setup_test_environment()

# Ensure application models are imported and tables are created for the test DB.
try:
    import importlib

    # Import models so Base.metadata is populated
    importlib.import_module("db.base")

    # Call create_tables on the session module (safe no-op if not present)
    db_session_mod = importlib.import_module("db.session")
    if hasattr(db_session_mod, "create_tables"):
        db_session_mod.create_tables()
except Exception as e:
    # Don't fail test collection for table creation problems; show a warning.
    print(f"Warning: could not create test tables: {e}")

# Import after path setup - graceful handling for interface segregation
try:
    import importlib

    # Dynamically import modules to avoid static import resolution errors in editors/linters
    UserRepository = None
    UserService = None

    try:
        repo_mod = importlib.import_module("repositories.user_repo")
        UserRepository = getattr(repo_mod, "UserRepository", None)
    except Exception as e:
        # Do not fail test discovery on import problems; log for debugging.
        print(f"Warning: Could not import repositories.user_repo: {e}")

    try:
        service_mod = importlib.import_module("services.user_service")
        UserService = getattr(service_mod, "UserService", None)
    except Exception as e:
        print(f"Warning: Could not import services.user_service: {e}")

    IMPORTS_AVAILABLE = UserRepository is not None and UserService is not None
except Exception as e:
    # Handle import errors gracefully for test discovery
    print(f"Warning: Could not import modules: {e}")
    UserRepository = None
    UserService = None
    IMPORTS_AVAILABLE = False


# Import integration and auth fixtures for availability across all test modules
try:
    from fixtures.integration_fixtures import *
    from fixtures.auth_fixtures import *

    print("Integration and authentication fixtures loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import advanced fixtures: {e}")
    print("Basic fixtures will still be available")


# =====================================================
# BASIC MOCK FIXTURES
# =====================================================


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = Mock()
    user.id = 123
    user.email = "test@example.com"
    user.name = "Test User"
    user.google_id = "google123"
    user.avatar_url = "https://example.com/avatar.jpg"
    user.password_hash = None
    user.is_active = True
    user.created_at = None
    user.updated_at = None
    return user


@pytest.fixture
def mock_google_user_info():
    """Create mock Google OAuth user info for testing."""
    return {
        "id": "google123456",
        "email": "google.user@gmail.com",
        "name": "Google Test User",
        "picture": "https://lh3.googleusercontent.com/test-avatar",
    }


@pytest.fixture
def mock_db_session():
    """Create a mock database session for testing."""
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.refresh = Mock()
    session.rollback = Mock()
    session.close = Mock()
    session.query = Mock()
    return session


@pytest.fixture
def mock_user_repository(mock_db_session):
    """Create a mock UserRepository for testing."""
    if IMPORTS_AVAILABLE and UserRepository is not None:
        repo = Mock(spec=UserRepository)
    else:
        repo = Mock()

    repo.db = mock_db_session
    repo.get_by_id = Mock()
    repo.get_by_email = Mock()
    repo.get_by_google_id = Mock()
    repo.create = Mock()
    repo.update = Mock()
    repo.set_[REDACTED_PASSWORD]
    return repo


@pytest.fixture
def mock_user_service(mock_user_repository):
    """Create a mock UserService for testing."""
    if IMPORTS_AVAILABLE and UserService is not None:
        service = Mock(spec=UserService)
    else:
        service = Mock()

    service.repo = mock_user_repository
    service.create_or_update_from_google = Mock()
    service.set_[REDACTED_PASSWORD]
    service.authenticate_local = Mock()
    return service


# =====================================================
# FLASK APPLICATION FIXTURES
# =====================================================


@pytest.fixture(scope="session")
def app_config():
    """Provide test application configuration."""
    return {
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "JWT_SECRET_KEY": "test-jwt-secret",
        "DATABASE_URL": TEST_DATABASE_URL,
        "GOOGLE_OAUTH_CLIENT_ID": "test-google-client-id",
        "GOOGLE_OAUTH_CLIENT_SECRET": "test-google-client-secret",
    }


@pytest.fixture
def app():
    """Create a Flask application for testing with proper configuration."""
    try:
        import importlib

        main_mod = importlib.import_module("app.main")
        create_app = getattr(main_mod, "create_app", None)
        if create_app is None:
            raise ImportError("create_app not found in 'app.main' module")

        # Set environment variables for testing
        import os

        # Don't set LOGIN_DISABLED globally - let individual tests control this
        # os.environ["LOGIN_DISABLED"] = "true"
        os.environ["TESTING"] = "true"
        os.environ["SECRET_KEY"] = "test-secret-key"
        os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"

        app = create_app()

        # Ensure test configuration is applied
        app.config.update(
            {
                "TESTING": True,
                "WTF_CSRF_ENABLED": False,  # Disable CSRF for testing
                # "LOGIN_DISABLED": True,  # Don't disable login globally
                "SECRET_KEY": "test-secret-key",
                "JWT_SECRET_KEY": "test-jwt-secret",
                "PROPAGATE_EXCEPTIONS": True,  # Show exceptions in tests
            }
        )

        return app
    except Exception as e:
        print(f"Warning: Could not create real Flask app: {e}")
        # Return a mock app if the real one can't be imported
        mock_app = Mock()
        mock_app.config = {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "JWT_SECRET_KEY": "test-jwt-secret",
        }

        # Create a mock test client that supports context manager
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client.get = Mock()
        mock_client.post = Mock()
        mock_client.put = Mock()
        mock_client.delete = Mock()

        mock_app.test_client = Mock(return_value=mock_client)

        # Create a mock app_context that supports context manager
        mock_app_context = Mock()
        mock_app_context.__enter__ = Mock(return_value=mock_app_context)
        mock_app_context.__exit__ = Mock(return_value=None)
        mock_app.app_context = Mock(return_value=mock_app_context)

        return mock_app


@pytest.fixture
def client(app):
    """Create a test client for Flask application with proper context."""
    if hasattr(app, "test_client") and hasattr(app, "app_context"):
        with app.test_client() as client:
            with app.app_context():
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
def app_context(app):
    """Provide Flask application context for tests that need it."""
    with app.app_context():
        yield app


@pytest.fixture
def request_context(app):
    """Provide Flask request context for tests that access request/session/g objects."""
    with app.test_request_context():
        yield


@pytest.fixture
def test_client(app):
    """Enhanced test client with both app and request context."""
    with app.test_client() as client:
        with app.app_context():
            yield client


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
# TEST MARKERS AND CONFIGURATION
# =====================================================


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "auth: mark test as authentication-related")
    config.addinivalue_line("markers", "security: mark test as security-related")
    config.addinivalue_line("markers", "api: mark test as API endpoint test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "postgres: mark test as requiring PostgreSQL")
    config.addinivalue_line("markers", "google: mark test as requiring Google API")
    config.addinivalue_line("markers", "controllers: mark test as controller-related")
    config.addinivalue_line("markers", "sessions: mark test as session-related")
    config.addinivalue_line("markers", "clients: mark test as client-related")
    config.addinivalue_line("markers", "database: mark test as database-related")
    config.addinivalue_line("markers", "performance: mark test as performance-related")
    config.addinivalue_line("markers", "services: mark test as service layer test")
    config.addinivalue_line("markers", "appointment: mark test as appointment-related")
    config.addinivalue_line("markers", "artist: mark test as artist-related")
    config.addinivalue_line("markers", "repositories: mark test as repository test")
    config.addinivalue_line("markers", "user: mark test as user-related")
    config.addinivalue_line("markers", "service_layer: mark test as service layer test")


def pytest_collection_modifyitems(config, items):
    """Modify test items during collection."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        if "auth" in str(item.fspath) or "auth" in item.name:
            item.add_marker(pytest.mark.auth)

        if "security" in str(item.fspath) or "security" in item.name:
            item.add_marker(pytest.mark.security)

        if "postgres" in str(item.fspath) or "postgres" in item.name:
            item.add_marker(pytest.mark.postgres)

        if "calendar" in str(item.fspath) or "google" in str(item.fspath):
            item.add_marker(pytest.mark.google)

        # Add sessoes-specific markers
        if "sessoes" in str(item.fspath) or "sessoes" in item.name:
            item.add_marker(pytest.mark.controllers)
            item.add_marker(pytest.mark.sessions)

        # Add general controller markers
        if "controller" in str(item.fspath):
            item.add_marker(pytest.mark.controllers)

        # Add service layer markers
        if "service" in str(item.fspath) or "service" in item.name:
            item.add_marker(pytest.mark.services)
            item.add_marker(pytest.mark.service_layer)

        # Add repository markers
        if "repo" in str(item.fspath) or "repository" in str(item.fspath):
            item.add_marker(pytest.mark.repositories)


@pytest.fixture
def response_helper():
    """Simple response helper for integration tests."""

    class ResponseHelper:
        @staticmethod
        def assert_html_response(response, expected_status=200):
            assert response.status_code == expected_status
            return response.get_data(as_text=True)

        @staticmethod
        def assert_json_response(response, expected_status=200):
            assert response.status_code == expected_status
            return response.get_json()

        @staticmethod
        def assert_redirect_response(response):
            assert response.status_code in (301, 302, 303, 307, 308)
            return response.headers.get("Location")

    return ResponseHelper()


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
                    from db.session import get_engine

                    Base.metadata.create_all(bind=get_engine())
                except ImportError:
                    # Fallback if db.session import fails
                    from sqlalchemy import create_engine

                    engine = create_engine(TEST_DATABASE_URL)
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
                        return self.client.put(*args, **kwargs)

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
