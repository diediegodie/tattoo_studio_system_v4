import pytest
from unittest.mock import Mock, patch

# Ensure test imports are configured
from tests.config import setup_test_imports

setup_test_imports()

from importlib import import_module, reload

try:
    # Import domain entity (may raise in restricted environments)
    from app.domain.entities import User

    DOMAIN_AVAILABLE = True
except Exception:
    DOMAIN_AVAILABLE = False


def import_calendar_controller_with_bypass():
    """Import the calendar_controller module while bypassing login_required."""
    with patch("flask_login.login_required", lambda f: f):
        mod = import_module("controllers.calendar_controller")
        # Ensure module is reloaded under the patched decorator
        reload(mod)
        return mod


try:
    calendar_controller = import_calendar_controller_with_bypass()
    IMPORTS_AVAILABLE = True
except Exception as e:
    print(f"Warning: Could not import calendar controller modules: {e}")
    IMPORTS_AVAILABLE = False


@pytest.fixture(autouse=True)
def mock_calendar_service():
    """Patch CalendarService used inside the controller to a Mock."""
    with patch("controllers.calendar_controller.GoogleCalendarService") as MockService:
        mock = Mock()
        MockService.return_value = mock
        yield mock


@pytest.fixture(autouse=True)
def bypass_login_required():
    """Patch the login_required decorator to a no-op so endpoints are callable in unit tests."""
    with patch("controllers.calendar_controller.login_required", lambda f: f):
        yield


@pytest.fixture
def local_client():
    """Create a local Flask app and register the calendar blueprint imported with bypass."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Calendar controller not importable")

    from flask import Flask
    from pathlib import Path

    app = Flask(__name__)
    app.secret_key = "test-secret-key"  # Required for sessions

    # Set up template and static folders - frontend is at project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    template_dir = project_root / "frontend" / "templates"
    static_dir = project_root / "frontend" / "assets"

    app.template_folder = str(template_dir)
    app.static_folder = str(static_dir)

    # Add a simple index route for redirects
    @app.route("/index")
    def index():
        return "Index page"

    app.register_blueprint(calendar_controller.calendar_bp)

    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_authenticated_user():
    """Create a mock authenticated user for testing."""
    user = Mock()
    user.id = 1
    user.email = "test@example.com"
    user.name = "Test User"
    user.is_active = True
    user.is_authenticated = True
    user.is_anonymous = False
    return user


@pytest.mark.unit
@pytest.mark.controllers
class TestCalendarControllerEndpoints:
    def test_calendar_page_returns_200_with_mock_user(
        self, local_client, mock_authenticated_user, mock_calendar_service
    ):
        """Test that calendar page returns 200 with proper mocking."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Calendar controller not importable")

        # Mock the current_user
        with patch(
            "controllers.calendar_controller.current_user", mock_authenticated_user
        ), patch("app.db.session.SessionLocal") as mock_session, patch(
            "controllers.calendar_controller.render_template"
        ) as mock_render:

            # Mock the database session
            mock_db = Mock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.filter.return_value.all.return_value = []

            # Mock the calendar service methods
            mock_calendar_service.is_user_authorized.return_value = True
            mock_calendar_service.get_user_events.return_value = []

            # Mock template rendering
            mock_render.return_value = "<html>Mock calendar page</html>"

            resp = local_client.get("/calendar/")
            assert resp.status_code == 200
            mock_render.assert_called_once()

    def test_api_events_endpoint_returns_json(
        self, local_client, mock_authenticated_user, mock_calendar_service
    ):
        """Test that /api/events returns JSON response."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Calendar controller not importable")

        # Mock the current_user
        with patch(
            "controllers.calendar_controller.current_user", mock_authenticated_user
        ):
            # Mock the calendar service methods
            mock_calendar_service.is_user_authorized.return_value = True
            mock_calendar_service.get_user_events.return_value = []

            resp = local_client.get("/calendar/api/events")
            assert resp.status_code == 200
            data = resp.get_json()
            assert isinstance(data, dict)
            assert "success" in data

    def test_api_events_unauthorized_user(
        self, local_client, mock_authenticated_user, mock_calendar_service
    ):
        """Test that unauthorized users get proper error response."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Calendar controller not importable")

        # Mock the current_user
        with patch(
            "controllers.calendar_controller.current_user", mock_authenticated_user
        ):
            # Mock the calendar service to return unauthorized
            mock_calendar_service.is_user_authorized.return_value = False

            resp = local_client.get("/calendar/api/events")
            assert resp.status_code == 401
            data = resp.get_json()
            assert data["success"] is False
            assert "auth_required" in data

    def test_api_events_with_date_range(
        self, local_client, mock_authenticated_user, mock_calendar_service
    ):
        """Test that date range parameters are handled correctly."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Calendar controller not importable")

        # Mock the current_user
        with patch(
            "controllers.calendar_controller.current_user", mock_authenticated_user
        ):
            # Mock the calendar service methods
            mock_calendar_service.is_user_authorized.return_value = True
            mock_calendar_service.get_user_events.return_value = []

            resp = local_client.get(
                "/calendar/api/events?start=2025-01-01T00:00:00Z&end=2025-01-07T23:59:59Z"
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert "success" in data

    def test_api_events_invalid_date_format(
        self, local_client, mock_authenticated_user, mock_calendar_service
    ):
        """Test that invalid date formats return proper error."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Calendar controller not importable")

        # Mock the current_user
        with patch(
            "controllers.calendar_controller.current_user", mock_authenticated_user
        ):
            # Mock the calendar service methods
            mock_calendar_service.is_user_authorized.return_value = True

            resp = local_client.get("/calendar/api/events?start=invalid-date")
            assert resp.status_code == 400
            data = resp.get_json()
            assert data["success"] is False
            assert "Invalid start date format" in data["error"]

    def test_api_events_end_before_start(
        self, local_client, mock_authenticated_user, mock_calendar_service
    ):
        """Test that end date before start date returns proper error."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Calendar controller not importable")

        # Mock the current_user
        with patch(
            "controllers.calendar_controller.current_user", mock_authenticated_user
        ):
            # Mock the calendar service methods
            mock_calendar_service.is_user_authorized.return_value = True

            resp = local_client.get(
                "/calendar/api/events?start=2025-01-07T00:00:00Z&end=2025-01-01T00:00:00Z"
            )
            assert resp.status_code == 400
            data = resp.get_json()
            assert data["success"] is False
            assert "End date must be after start date" in data["error"]
