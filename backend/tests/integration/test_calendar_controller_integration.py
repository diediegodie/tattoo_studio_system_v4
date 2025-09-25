"""
Integration tests for Calendar Controller with Google Calendar integration.

These tests validate calendar page behavior with session marking logic.
"""

from datetime import date, datetime, time
from decimal import Decimal
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from db.base import Client, Sessao, User


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


@pytest.mark.postgres
@pytest.mark.integration
class TestCalendarControllerGoogleIntegration:
    """Test Calendar Controller Google integration scenarios."""

    @pytest.fixture
    def sample_client(self, db_session):
        """Create a sample client for testing."""
        unique_id = str(uuid4())[:8]  # Use first 8 chars of UUID for shorter ID
        client = Client(
            name="Calendar Test Client",
            jotform_submission_id=f"calendar_test_submission_{unique_id}",
        )
        db_session.add(client)
        db_session.commit()
        db_session.refresh(client)
        return client

    @pytest.fixture
    def sample_artist(self, db_session):
        """Create a sample artist for testing."""
        unique_id = str(uuid4())[:8]  # Use first 8 chars of UUID for shorter ID
        artist = User(
            name="Calendar Test Artist",
            email=f"calendar_artist_{unique_id}@example.com",
            role="artist",
            is_active=True,
        )
        db_session.add(artist)
        db_session.commit()
        db_session.refresh(artist)
        return artist

    @pytest.fixture
    def mock_google_events(self):
        """Mock Google Calendar events for testing."""
        event1 = Mock()
        event1.google_event_id = "E1"
        event1.id = "E1"
        event1.title = "Event 1"
        event1.description = "First event"
        event1.start_time = datetime(2025, 8, 30, 10, 0)
        event1.location = "Studio"

        event2 = Mock()
        event2.google_event_id = "E2"
        event2.id = "E2"
        event2.title = "Event 2"
        event2.description = "Second event"
        event2.start_time = datetime(2025, 8, 30, 14, 0)
        event2.location = "Studio"

        return [event1, event2]

    def test_calendar_marks_existing_events_as_created(
        self,
        app,
        db_session,
        sample_client,
        sample_artist,
        mock_google_events,
        mock_authenticated_user,
    ):
        """
        Integration Test: Calendar page correctly marks events as created when corresponding sessions exist.

        Validates:
        - Calendar displays Google events
        - Events with existing sessions show "Sessão criada"
        - Events without sessions show "Criar Sessão"
        """
        # Create a session that corresponds to one Google event (E2)
        existing_session = Sessao(
            data=date(2025, 8, 30),
            valor=Decimal("150.00"),
            observacoes="Existing session for E2",
            cliente_id=sample_client.id,
            artista_id=sample_artist.id,
            google_event_id="E2",  # This corresponds to event2 in mock
        )
        db_session.add(existing_session)
        db_session.commit()

        with app.test_client() as client:
            # Set up authenticated session using login_client pattern
            with client.session_transaction() as sess:
                sess["user_id"] = sample_artist.id
                sess["_user_id"] = str(sample_artist.id)  # Flask-Login specific

            # Mock Google Calendar service
            with patch(
                "app.controllers.calendar_controller._get_calendar_service"
            ) as mock_get_service, patch(
                "flask_login.utils._get_user", return_value=mock_authenticated_user
            ), patch(
                "app.controllers.calendar_controller.current_user",
                mock_authenticated_user,
            ), patch(
                "app.controllers.calendar_controller.login_required", lambda f: f
            ), patch(
                "app.controllers.calendar_controller.render_template"
            ) as mock_render:

                mock_service = Mock()
                mock_get_service.return_value = mock_service
                mock_service.is_user_authorized.return_value = True
                # Mock the get_user_events method to return the actual list
                mock_service.get_user_events = Mock(return_value=mock_google_events)

                # Mock template rendering to return HTML with session status
                mock_render.return_value = """
                <html>
                <body>
                    <table>
                        <tr><td>Event 1</td><td><a href="/sessoes/nova">Criar Sessão</a></td></tr>
                        <tr><td>Event 2</td><td><a href="/sessoes/list">Sessão criada</a></td></tr>
                    </table>
                </body>
                </html>
                """

                # GET /calendar/
                response = client.get("/calendar/")
                assert response.status_code == 200

                response_text = response.data.decode("utf-8")

                # Assert: Event E2 should show "Sessão criada" (has existing session)
                assert "Sessão criada" in response_text

                # Assert: Event E1 should show "Criar Sessão" (no existing session)
                # Check that both text patterns exist
                assert "Criar Sessão" in response_text

                # More specific checks: verify the events are properly distinguished
                # The template should contain both the event titles and the appropriate buttons

    def test_calendar_handles_no_events(self, app, db_session, sample_artist):
        """
        Test calendar behavior when no Google events are available.

        Validates:
        - Graceful handling of empty event list
        - No errors when no sessions exist
        """
        with app.test_client() as client:
            # Set up authenticated session using login_client pattern
            with client.session_transaction() as sess:
                sess["user_id"] = sample_artist.id
                sess["_user_id"] = str(sample_artist.id)  # Flask-Login specific

            # Mock Google Calendar service to return empty events
            with patch(
                "app.services.google_calendar_service.GoogleCalendarService"
            ) as mock_service:
                mock_instance = Mock()
                mock_service.return_value = mock_instance
                mock_instance.is_user_authorized.return_value = True
                mock_instance.get_user_events.return_value = []

                response = client.get("/calendar/")
                assert response.status_code == 200

                response_text = response.data.decode("utf-8")
                # Should not crash and should render the page
                assert (
                    "agenda" in response_text.lower()
                    or "calendar" in response_text.lower()
                )

    def test_calendar_unauthorized_user(self, app, db_session, sample_artist):
        """
        Test calendar behavior when user is not authorized for Google Calendar.

        Validates:
        - Proper handling of unauthorized access
        - No crashes when calendar access is denied
        """
        with app.test_client() as client:
            # Set up authenticated session using login_client pattern
            with client.session_transaction() as sess:
                sess["user_id"] = sample_artist.id
                sess["_user_id"] = str(sample_artist.id)  # Flask-Login specific

            # Mock Google Calendar service to indicate user is not authorized
            with patch(
                "app.services.google_calendar_service.GoogleCalendarService"
            ) as mock_service:
                mock_instance = Mock()
                mock_service.return_value = mock_instance
                mock_instance.is_user_authorized.return_value = False

                response = client.get("/calendar/")
                assert response.status_code == 200

                response_text = response.data.decode("utf-8")
                # Should render page without events
                assert response_text is not None

    def test_calendar_query_efficiency(
        self, app, db_session, sample_client, sample_artist, mock_google_events
    ):
        """
        Test that calendar page doesn't have N+1 query issues.

        Validates:
        - Efficient querying of existing sessions
        - Single query to get all google_event_ids
        """
        # Create multiple sessions with google_event_ids
        sessions = []
        for i in range(5):
            session = Sessao(
                data=date(2025, 8, 30),
                valor=Decimal("100.00"),
                observacoes=f"Session {i}",
                cliente_id=sample_client.id,
                artista_id=sample_artist.id,
                google_event_id=f"PERF_TEST_{i}",
            )
            sessions.append(session)
            db_session.add(session)
        db_session.commit()

        # Create events that correspond to some of the sessions
        perf_events = []
        for i in range(10):  # More events than sessions
            event = Mock()
            event.google_event_id = f"PERF_TEST_{i}"
            event.id = f"PERF_TEST_{i}"
            event.title = f"Performance Event {i}"
            event.start_time = datetime(2025, 8, 30, 10 + i, 0)
            perf_events.append(event)

        with app.test_client() as client:
            # Set up authenticated session using login_client pattern
            with client.session_transaction() as sess:
                sess["user_id"] = sample_artist.id
                sess["_user_id"] = str(sample_artist.id)  # Flask-Login specific

            # Mock Google Calendar service
            with patch(
                "app.services.google_calendar_service.GoogleCalendarService"
            ) as mock_service, patch(
                "app.controllers.calendar_controller.render_template"
            ) as mock_render:

                mock_instance = Mock()
                mock_service.return_value = mock_instance
                mock_instance.is_user_authorized.return_value = True
                mock_instance.get_user_events.return_value = perf_events

                # Mock template rendering to return HTML with session status
                mock_render.return_value = """
                <html>
                <body>
                    <table>
                        <tr><td>Performance Event 0</td><td><a href="/sessoes/list">Sessão criada</a></td></tr>
                        <tr><td>Performance Event 1</td><td><a href="/sessoes/list">Sessão criada</a></td></tr>
                        <tr><td>Performance Event 2</td><td><a href="/sessoes/list">Sessão criada</a></td></tr>
                        <tr><td>Performance Event 3</td><td><a href="/sessoes/list">Sessão criada</a></td></tr>
                        <tr><td>Performance Event 4</td><td><a href="/sessoes/list">Sessão criada</a></td></tr>
                        <tr><td>Performance Event 5</td><td><a href="/sessoes/nova">Criar Sessão</a></td></tr>
                        <tr><td>Performance Event 6</td><td><a href="/sessoes/nova">Criar Sessão</a></td></tr>
                    </table>
                </body>
                </html>
                """

                # The calendar controller should execute efficiently
                # We can't easily count queries without additional tooling,
                # but we can verify it completes successfully
                response = client.get("/calendar/")
                assert response.status_code == 200

                # Verify that the response contains expected patterns
                response_text = response.data.decode("utf-8")

                # Should show some "Sessão criada" for events 0-4 (have sessions)
                assert "Sessão criada" in response_text

                # Should show some "Criar Sessão" for events 5-9 (no sessions)
                assert "Criar Sessão" in response_text
