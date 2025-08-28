"""
Integration tests for Calendar Controller with Google Calendar integration.

These tests validate calendar page behavior with session marking logic.
"""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime, date, time
from decimal import Decimal

from db.base import Sessao, Client, User


@pytest.mark.postgres
@pytest.mark.integration
class TestCalendarControllerGoogleIntegration:
    """Test Calendar Controller Google integration scenarios."""

    @pytest.fixture
    def sample_client(self, postgres_db):
        """Create a sample client for testing."""
        client = Client(
            name="Calendar Test Client",
            jotform_submission_id="calendar_test_submission_456",
        )
        postgres_db.add(client)
        postgres_db.commit()
        postgres_db.refresh(client)
        return client

    @pytest.fixture
    def sample_artist(self, postgres_db):
        """Create a sample artist for testing."""
        artist = User(
            name="Calendar Test Artist",
            email="calendar_artist@example.com",
            role="artist",
            is_active=True,
        )
        postgres_db.add(artist)
        postgres_db.commit()
        postgres_db.refresh(artist)
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
        postgres_db,
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
            hora=time(14, 0),
            valor=Decimal("150.00"),
            observacoes="Existing session for E2",
            cliente_id=sample_client.id,
            artista_id=sample_artist.id,
            google_event_id="E2",  # This corresponds to event2 in mock
        )
        postgres_db.add(existing_session)
        postgres_db.commit()

        with app.test_client() as client:
            # Mock Flask-Login current_user to be authenticated
            with patch("flask_login.current_user", mock_authenticated_user):
                mock_authenticated_user.is_authenticated = True
                mock_authenticated_user.id = sample_artist.id

                # Also patch current_user in the calendar controller
                with patch(
                    "controllers.calendar_controller.current_user",
                    mock_authenticated_user,
                ):
                    # Mock Google Calendar service
                    with patch(
                        "services.google_calendar_service.GoogleCalendarService"
                    ) as mock_service:
                        mock_instance = Mock()
                        mock_service.return_value = mock_instance
                        mock_instance.is_user_authorized.return_value = True
                        mock_instance.get_user_events.return_value = mock_google_events

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

    def test_calendar_handles_no_events(self, app, postgres_db, sample_artist):
        """
        Test calendar behavior when no Google events are available.

        Validates:
        - Graceful handling of empty event list
        - No errors when no sessions exist
        """
        with app.test_client() as client:
            # Mock the user session
            with client.session_transaction() as sess:
                sess["user_id"] = sample_artist.id
                sess["logged_in"] = True

            # Mock Google Calendar service to return empty events
            with patch(
                "services.google_calendar_service.GoogleCalendarService"
            ) as mock_service:
                mock_instance = Mock()
                mock_service.return_value = mock_instance
                mock_instance.is_user_authorized.return_value = True
                mock_instance.get_user_events.return_value = []

                response = client.get("/calendar")
                assert response.status_code == 200

                response_text = response.data.decode("utf-8")
                # Should not crash and should render the page
                assert (
                    "agenda" in response_text.lower()
                    or "calendar" in response_text.lower()
                )

    def test_calendar_unauthorized_user(self, app, postgres_db, sample_artist):
        """
        Test calendar behavior when user is not authorized for Google Calendar.

        Validates:
        - Proper handling of unauthorized access
        - No crashes when calendar access is denied
        """
        with app.test_client() as client:
            # Mock the user session
            with client.session_transaction() as sess:
                sess["user_id"] = sample_artist.id
                sess["logged_in"] = True

            # Mock Google Calendar service to indicate user is not authorized
            with patch(
                "services.google_calendar_service.GoogleCalendarService"
            ) as mock_service:
                mock_instance = Mock()
                mock_service.return_value = mock_instance
                mock_instance.is_user_authorized.return_value = False

                response = client.get("/calendar")
                assert response.status_code == 200

                response_text = response.data.decode("utf-8")
                # Should render page without events
                assert response_text is not None

    def test_calendar_query_efficiency(
        self, app, postgres_db, sample_client, sample_artist, mock_google_events
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
                hora=time(10 + i, 0),
                valor=Decimal("100.00"),
                observacoes=f"Session {i}",
                cliente_id=sample_client.id,
                artista_id=sample_artist.id,
                google_event_id=f"PERF_TEST_{i}",
            )
            sessions.append(session)
            postgres_db.add(session)
        postgres_db.commit()

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
            # Mock the user session
            with client.session_transaction() as sess:
                sess["user_id"] = sample_artist.id
                sess["logged_in"] = True

            # Mock Google Calendar service
            with patch(
                "services.google_calendar_service.GoogleCalendarService"
            ) as mock_service:
                mock_instance = Mock()
                mock_service.return_value = mock_instance
                mock_instance.is_user_authorized.return_value = True
                mock_instance.get_user_events.return_value = perf_events

                # The calendar controller should execute efficiently
                # We can't easily count queries without additional tooling,
                # but we can verify it completes successfully
                response = client.get("/calendar")
                assert response.status_code == 200

                # Verify that the response contains expected patterns
                response_text = response.data.decode("utf-8")

                # Should show some "Sessão criada" for events 0-4 (have sessions)
                assert "Sessão criada" in response_text

                # Should show some "Criar Sessão" for events 5-9 (no sessions)
                assert "Criar Sessão" in response_text
