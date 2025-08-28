"""
Integration tests for Sessoes Controller with Google Calendar integration.

These tests validate the P0 scenarios for google_event_id flow:
- Idempotent session creation from Google events
- Constraint handling and database integrity
- Controller behavior and redirects
"""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime, date, time
from decimal import Decimal

from db.base import Sessao, Client, User


@pytest.mark.postgres
@pytest.mark.integration
class TestSessoesControllerGoogleIntegration:
    """Test Google Calendar integration with Sessoes controller."""

    @pytest.fixture
    def sample_client(self, postgres_db):
        """Create a sample client for testing."""
        client = Client(name="Test Client", jotform_submission_id="test_submission_123")
        postgres_db.add(client)
        postgres_db.commit()
        postgres_db.refresh(client)
        return client

    @pytest.fixture
    def sample_artist(self, postgres_db):
        """Create a sample artist for testing."""
        artist = User(
            name="Test Artist",
            email="artist@example.com",
            role="artist",
            is_active=True,
        )
        postgres_db.add(artist)
        postgres_db.commit()
        postgres_db.refresh(artist)
        return artist

    @pytest.fixture
    def mock_google_event(self):
        """Mock Google Calendar event data."""
        event = Mock()
        event.google_event_id = "EVT1"
        event.id = "EVT1"
        event.title = "Test Event (google agenda)"
        event.description = "Test description"
        event.start_time = datetime(2025, 8, 30, 14, 0)
        event.end_time = datetime(2025, 8, 30, 15, 0)
        return event

    def test_create_session_from_google_creates_new_when_not_exists(
        self,
        app,
        postgres_db,
        sample_client,
        sample_artist,
        mock_google_event,
        mock_authenticated_user,
    ):
        """
        P0 Test: Create session from Google event when it doesn't exist.

        Validates:
        - Idempotent creation behavior
        - Database row creation with google_event_id
        - Proper redirect response
        """
        with app.test_client() as client:
            # Mock Flask-Login current_user to be authenticated
            with patch("flask_login.current_user", mock_authenticated_user):
                mock_authenticated_user.is_authenticated = True
                mock_authenticated_user.id = sample_artist.id

                # Mock Google Calendar service to return the event
                with patch(
                    "services.google_calendar_service.GoogleCalendarService"
                ) as mock_service:
                    mock_instance = Mock()
                    mock_service.return_value = mock_instance
                    mock_instance.is_user_authorized.return_value = True
                    mock_instance.get_user_events.return_value = [mock_google_event]

                    # Step 1: GET /sessoes/nova?event_id=EVT1 (should populate form)
                    response = client.get("/sessoes/nova?event_id=EVT1")
                    assert response.status_code == 200
                    assert b"Test Event (google agenda)" in response.data

                    # Step 2: POST form data with google_event_id
                    form_data = {
                        "data": "2025-08-30",
                        "hora": "14:00",
                        "cliente_id": str(sample_client.id),
                        "artista_id": str(sample_artist.id),
                        "valor": "100.00",
                        "observacoes": "Test session from Google",
                        "google_event_id": "EVT1",
                    }

                    response = client.post(
                        "/sessoes/nova", data=form_data, follow_redirects=False
                    )

                    # Assert: Should redirect to session list
                    assert response.status_code == 302
                    assert "/sessoes/list" in response.location

                    # Assert: Database row should be created with google_event_id
                    session = (
                        postgres_db.query(Sessao)
                        .filter_by(google_event_id="EVT1")
                        .first()
                    )
                    assert session is not None
                    assert session.google_event_id == "EVT1"
                    assert session.cliente_id == sample_client.id
                    assert session.artista_id == sample_artist.id
                    assert session.valor == Decimal("100.00")

    def test_create_session_from_google_redirects_when_already_exists(
        self, app, postgres_db, sample_client, sample_artist
    ):
        """
        P0 Test: Redirect when session already exists for google_event_id.

        Validates:
        - Idempotent behavior prevents duplicates
        - Proper redirect and flash message
        - No duplicate database rows
        """
        # Pre-insert a session with google_event_id='EVT2'
        existing_session = Sessao(
            data=date(2025, 8, 30),
            hora=time(14, 0),
            valor=Decimal("100.00"),
            observacoes="Existing session",
            cliente_id=sample_client.id,
            artista_id=sample_artist.id,
            google_event_id="EVT2",
        )
        postgres_db.add(existing_session)
        postgres_db.commit()

        with app.test_client() as client:
            # Mock the user session
            with client.session_transaction() as sess:
                sess["user_id"] = sample_artist.id
                sess["logged_in"] = True

            # Attempt to create another session with the same google_event_id
            form_data = {
                "data": "2025-08-31",
                "hora": "15:00",
                "cliente_id": str(sample_client.id),
                "artista_id": str(sample_artist.id),
                "valor": "150.00",
                "observacoes": "Duplicate attempt",
                "google_event_id": "EVT2",
            }

            response = client.post(
                "/sessoes/nova", data=form_data, follow_redirects=True
            )

            # Assert: Should redirect to session list with flash message
            assert response.status_code == 200
            assert (
                b"Uma sess" in response.data or b"j\xc3\xa1 existe" in response.data
            )  # Flash message

            # Assert: Only one session should exist in database
            sessions = postgres_db.query(Sessao).filter_by(google_event_id="EVT2").all()
            assert len(sessions) == 1
            # Original session should remain unchanged
            assert sessions[0].valor == Decimal("100.00")  # Original value, not 150.00

    def test_manual_session_creation_has_null_google_event_id(
        self, app, postgres_db, sample_client, sample_artist
    ):
        """
        P0 Test: Manual session creation without google_event_id.

        Validates:
        - Sessions created manually have NULL google_event_id
        - Standard session creation flow works
        """
        with app.test_client() as client:
            # Mock the user session
            with client.session_transaction() as sess:
                sess["user_id"] = sample_artist.id
                sess["logged_in"] = True

            # Create session without google_event_id
            form_data = {
                "data": "2025-09-01",
                "hora": "16:00",
                "cliente_id": str(sample_client.id),
                "artista_id": str(sample_artist.id),
                "valor": "200.00",
                "observacoes": "Manual session",
                # No google_event_id field
            }

            response = client.post(
                "/sessoes/nova", data=form_data, follow_redirects=False
            )

            # Assert: Should redirect successfully
            assert response.status_code == 302
            assert "/sessoes/list" in response.location

            # Assert: Session created with NULL google_event_id
            session = (
                postgres_db.query(Sessao)
                .filter_by(data=date(2025, 9, 1), hora=time(16, 0))
                .first()
            )
            assert session is not None
            assert session.google_event_id is None
            assert session.valor == Decimal("200.00")

    def test_double_submit_integrityerror_is_caught(
        self, app, postgres_db, sample_client, sample_artist
    ):
        """
        P0 Test: Handle rapid double submission for same google_event_id.

        Validates:
        - IntegrityError is caught and handled gracefully
        - Only one row exists after double submit
        - Second submit redirects properly
        """
        with app.test_client() as client:
            # Mock the user session
            with client.session_transaction() as sess:
                sess["user_id"] = sample_artist.id
                sess["logged_in"] = True

            form_data = {
                "data": "2025-09-02",
                "hora": "17:00",
                "cliente_id": str(sample_client.id),
                "artista_id": str(sample_artist.id),
                "valor": "250.00",
                "observacoes": "Double submit test",
                "google_event_id": "EVT_DOUBLE",
            }

            # First submit - should succeed
            response1 = client.post(
                "/sessoes/nova", data=form_data, follow_redirects=False
            )
            assert response1.status_code == 302

            # Second submit with same google_event_id - should be handled gracefully
            response2 = client.post(
                "/sessoes/nova", data=form_data, follow_redirects=True
            )
            assert response2.status_code == 200  # Should redirect and follow

            # Assert: Only one session exists
            sessions = (
                postgres_db.query(Sessao).filter_by(google_event_id="EVT_DOUBLE").all()
            )
            assert len(sessions) == 1

    def test_api_responses_include_google_event_id(
        self, app, postgres_db, sample_client, sample_artist
    ):
        """
        P0 Test: Verify API responses include google_event_id field.

        Validates:
        - JSON API completeness
        - Proper serialization of google_event_id
        """
        # Create a session with google_event_id
        session = Sessao(
            data=date(2025, 9, 3),
            hora=time(18, 0),
            valor=Decimal("300.00"),
            observacoes="API test session",
            cliente_id=sample_client.id,
            artista_id=sample_artist.id,
            google_event_id="EVT_API",
        )
        postgres_db.add(session)
        postgres_db.commit()
        postgres_db.refresh(session)

        with app.test_client() as client:
            # Mock the user session
            with client.session_transaction() as sess:
                sess["user_id"] = sample_artist.id
                sess["logged_in"] = True

            # Test list API
            response = client.get("/sessoes/api")
            assert response.status_code == 200

            data = response.get_json()
            assert data["success"] is True
            assert "data" in data

            # Find our session in the response
            session_data = None
            for s in data["data"]:
                if s.get("google_event_id") == "EVT_API":
                    session_data = s
                    break

            assert session_data is not None
            assert session_data["google_event_id"] == "EVT_API"

            # Test detail API
            response = client.get(f"/sessoes/api/{session.id}")
            assert response.status_code == 200

            data = response.get_json()
            assert data["success"] is True
            assert data["data"]["google_event_id"] == "EVT_API"
