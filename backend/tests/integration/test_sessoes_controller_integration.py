"""
Integration tests for Sessoes Controller with Google Calendar integration.

These tests validate core session flows around Google Calendar integration.
They use the project's `db_session` fixture for transactional isolation.
"""

import uuid
from datetime import date, datetime, time
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from app.db.base import Client, Sessao, User


@pytest.mark.postgres
@pytest.mark.integration
class TestSessoesControllerGoogleIntegration:
    """Test Google Calendar integration with Sessoes controller."""

    @pytest.fixture
    def sample_client(self, db_session):
        submission_id = f"test_submission_{uuid.uuid4().hex[:8]}"
        client = Client(name="Test Client", jotform_submission_id=submission_id)
        db_session.add(client)
        db_session.commit()
        db_session.refresh(client)
        return client

    @pytest.fixture
    def sample_artist(self, db_session):
        artist = User(
            name="Test Artist",
            email=f"artist_{uuid.uuid4().hex[:8]}@example.com",
            role="artist",
            is_active=True,
        )
        db_session.add(artist)
        db_session.commit()
        db_session.refresh(artist)
        return artist

    @pytest.fixture
    def mock_google_event(self):
        event = Mock()
        event.google_event_id = "EVT1"
        event.id = "EVT1"
        event.title = "Test Event (google agenda)"
        event.description = "Test description"
        event.start_time = datetime(2025, 8, 30, 14, 0)
        event.end_time = datetime(2025, 8, 30, 15, 0)
        event.location = "Studio"
        event.attendees = []
        event.duration_minutes = int(
            (event.end_time - event.start_time).total_seconds() // 60
        )
        event.is_past_event = False
        event.created_by = None
        return event

    def test_create_session_from_google_creates_new_when_not_exists(
        self,
        app,
        db_session,
        sample_client,
        sample_artist,
        mock_google_event,
        mock_authenticated_user,
    ):
        with app.test_client() as client:
            with patch("flask_login.current_user", mock_authenticated_user):
                mock_authenticated_user.is_authenticated = True
                mock_authenticated_user.id = sample_artist.id

                with client.session_transaction() as sess:
                    sess["user_id"] = sample_artist.id
                    sess["_user_id"] = str(sample_artist.id)
                    sess["logged_in"] = True

                with patch(
                    "app.services.google_calendar_service.GoogleCalendarService"
                ) as mock_service:
                    mock_instance = Mock()
                    mock_service.return_value = mock_instance
                    mock_instance.is_user_authorized.return_value = True
                    mock_instance.get_user_events.return_value = [mock_google_event]

                    response = client.get("/sessoes/nova?event_id=EVT1")
                    assert response.status_code == 200
                    assert b"Test Event (google agenda)" in response.data

                    form_data = {
                        "data": "2025-08-30",
                        "cliente_id": str(sample_client.id),
                        "artista_id": str(sample_artist.id),
                        "valor": "100.00",
                        "observacoes": "Test session from Google",
                        "google_event_id": "EVT1",
                    }

                    response = client.post(
                        "/sessoes/nova", data=form_data, follow_redirects=False
                    )
                    assert response.status_code == 302
                    assert "/sessoes/list" in response.location

                    sess = (
                        db_session.query(Sessao)
                        .filter_by(google_event_id="EVT1")
                        .first()
                    )
                    assert sess is not None
                    assert sess.cliente_id == sample_client.id
                    assert sess.artista_id == sample_artist.id
                    assert sess.valor == Decimal("100.00")

    def test_create_session_from_google_redirects_when_already_exists(
        self, app, db_session, sample_client, sample_artist, mock_authenticated_user
    ):
        existing = Sessao(
            data=date(2025, 8, 30),
            valor=Decimal("100.00"),
            observacoes="Existing session",
            cliente_id=sample_client.id,
            artista_id=sample_artist.id,
            google_event_id="EVT2",
        )
        db_session.add(existing)
        db_session.commit()

        with app.test_client() as client:
            with patch("flask_login.current_user", mock_authenticated_user):
                mock_authenticated_user.is_authenticated = True
                mock_authenticated_user.id = sample_artist.id

                with client.session_transaction() as sess:
                    sess["user_id"] = sample_artist.id
                    sess["_user_id"] = str(sample_artist.id)
                    sess["logged_in"] = True

                form_data = {
                    "data": "2025-08-31",
                    "cliente_id": str(sample_client.id),
                    "artista_id": str(sample_artist.id),
                    "valor": "150.00",
                    "observacoes": "Duplicate attempt",
                    "google_event_id": "EVT2",
                }

                response = client.post(
                    "/sessoes/nova", data=form_data, follow_redirects=True
                )
                assert response.status_code == 200
                assert (
                    b"Uma sess" in response.data or b"j\xc3\xa1 existe" in response.data
                )

                sessions = (
                    db_session.query(Sessao).filter_by(google_event_id="EVT2").all()
                )
                assert len(sessions) == 1
                assert sessions[0].valor == Decimal("100.00")

    def test_manual_session_creation_has_null_google_event_id(
        self, app, db_session, sample_client, sample_artist, mock_authenticated_user
    ):
        with app.test_client() as client:
            with patch("flask_login.current_user", mock_authenticated_user):
                mock_authenticated_user.is_authenticated = True
                mock_authenticated_user.id = sample_artist.id

                with client.session_transaction() as sess:
                    sess["user_id"] = sample_artist.id
                    sess["_user_id"] = str(sample_artist.id)
                    sess["logged_in"] = True

                form_data = {
                    "data": "2025-09-01",
                    "cliente_id": str(sample_client.id),
                    "artista_id": str(sample_artist.id),
                    "valor": "200.00",
                    "observacoes": "Manual session",
                }

                response = client.post(
                    "/sessoes/nova", data=form_data, follow_redirects=False
                )
                assert response.status_code == 302
                assert "/sessoes/list" in response.location

                sess = (
                    db_session.query(Sessao)
                    .first()
                )
                assert sess is not None
                assert sess.google_event_id is None
                assert sess.valor == Decimal("200.00")

    def test_double_submit_integrityerror_is_caught(
        self, app, db_session, sample_client, sample_artist, mock_authenticated_user
    ):
        with app.test_client() as client:
            with patch("flask_login.current_user", mock_authenticated_user):
                mock_authenticated_user.is_authenticated = True
                mock_authenticated_user.id = sample_artist.id

                with client.session_transaction() as sess:
                    sess["user_id"] = sample_artist.id
                    sess["_user_id"] = str(sample_artist.id)
                    sess["logged_in"] = True

                form_data = {
                    "data": "2025-09-02",
                    "cliente_id": str(sample_client.id),
                    "artista_id": str(sample_artist.id),
                    "valor": "250.00",
                    "observacoes": "Double submit test",
                    "google_event_id": "EVT_DOUBLE",
                }

                response1 = client.post(
                    "/sessoes/nova", data=form_data, follow_redirects=False
                )
                assert response1.status_code == 302

                response2 = client.post(
                    "/sessoes/nova", data=form_data, follow_redirects=True
                )
                assert response2.status_code == 200

                sessions = (
                    db_session.query(Sessao)
                    .filter_by(google_event_id="EVT_DOUBLE")
                    .all()
                )
                assert len(sessions) == 1

    def test_api_responses_include_google_event_id(
        self, app, db_session, sample_client, sample_artist, mock_authenticated_user
    ):
        session = Sessao(
            data=date(2025, 9, 3),
            valor=Decimal("300.00"),
            observacoes="API test session",
            cliente_id=sample_client.id,
            artista_id=sample_artist.id,
            google_event_id="EVT_API",
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        with app.test_client() as client:
            with patch("flask_login.current_user", mock_authenticated_user):
                mock_authenticated_user.is_authenticated = True
                mock_authenticated_user.id = sample_artist.id

                with client.session_transaction() as sess:
                    sess["user_id"] = sample_artist.id
                    sess["_user_id"] = str(sample_artist.id)
                    sess["logged_in"] = True

                response = client.get("/sessoes/api")
                assert response.status_code == 200

                data = response.get_json()
                assert data["success"] is True
                assert "data" in data

                session_data = None
                for s in data["data"]:
                    if s.get("google_event_id") == "EVT_API":
                        session_data = s
                        break

                assert session_data is not None
                assert session_data["google_event_id"] == "EVT_API"

                response = client.get(f"/sessoes/api/{session.id}")
                assert response.status_code == 200

                data = response.get_json()
                assert data["success"] is True
                assert data["data"]["google_event_id"] == "EVT_API"
