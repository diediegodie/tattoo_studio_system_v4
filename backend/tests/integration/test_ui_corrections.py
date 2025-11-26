"""
UI Corrections Integration Tests
Tests for Agenda page UI improvements and flow corrections.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import patch, MagicMock
from app.db.base import Pagamento, Sessao, MigrationAudit, Client, User


@pytest.fixture
def sample_artist(db_session):
    """Create and persist a test artist user for authenticated sessions."""
    unique_id = str(uuid4())[:8]
    artist = User(
        name="UI Test Artist",
        email=f"ui_artist_{unique_id}@example.com",
        role="artist",
        active_flag=True,
    )
    db_session.add(artist)
    db_session.commit()
    db_session.refresh(artist)
    return artist


class TestAgendaEventPersistence:
    """Test 6-hour event persistence buffer logic."""

    def test_unpaid_event_visible_within_6h_buffer(
        self, client, db_session, sample_artist
    ):
        """Unpaid events should remain visible up to 6 hours after end_time."""
        # Set up authenticated session
        with client.session_transaction() as sess:
            sess["user_id"] = sample_artist.id
            sess["_user_id"] = str(sample_artist.id)

        now_utc = datetime.now(timezone.utc)

        # Create mock event that ended 3 hours ago (within buffer)
        end_time_3h_ago = now_utc - timedelta(hours=3)
        mock_event = MagicMock()
        mock_event.google_event_id = "test_event_3h_ago"
        mock_event.title = "Recent Event"
        mock_event.start_time = end_time_3h_ago - timedelta(hours=2)
        mock_event.end_time = end_time_3h_ago
        mock_event.description = "Test"
        mock_event.location = None
        mock_event.attendees = []

        with patch(
            "app.controllers.calendar_controller._get_calendar_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.is_user_authorized.return_value = True
            mock_service.get_user_events.return_value = [mock_event]
            mock_get_service.return_value = mock_service

            response = client.get("/calendar/")
            assert response.status_code == 200

            # Event should be visible (no payment, within 6h buffer)
            html_content = response.data.decode("utf-8")
            assert "Recent Event" in html_content
            assert "Registrar Pagamento" in html_content

    def test_unpaid_event_hidden_after_6h_buffer(
        self, client, db_session, sample_artist
    ):
        """Unpaid events should disappear after 6 hours past end_time."""
        # Set up authenticated session
        with client.session_transaction() as sess:
            sess["user_id"] = sample_artist.id
            sess["_user_id"] = str(sample_artist.id)

        now_utc = datetime.now(timezone.utc)

        # Create mock event that ended 7 hours ago (past buffer)
        end_time_7h_ago = now_utc - timedelta(hours=7)
        mock_event = MagicMock()
        mock_event.google_event_id = "test_event_7h_ago"
        mock_event.title = "Old Event"
        mock_event.start_time = end_time_7h_ago - timedelta(hours=2)
        mock_event.end_time = end_time_7h_ago
        mock_event.description = "Test"
        mock_event.location = None
        mock_event.attendees = []

        with patch(
            "app.controllers.calendar_controller._get_calendar_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.is_user_authorized.return_value = True
            mock_service.get_user_events.return_value = [mock_event]
            mock_get_service.return_value = mock_service

            response = client.get("/calendar/")
            assert response.status_code == 200

            # Event should NOT be visible (no payment, past 6h buffer)
            html_content = response.data.decode("utf-8")
            assert "Old Event" not in html_content

    def test_paid_event_always_visible(self, client, db_session, sample_artist):
        """Paid events should remain visible regardless of end_time."""
        # Set up authenticated session
        with client.session_transaction() as sess:
            sess["user_id"] = sample_artist.id
            sess["_user_id"] = str(sample_artist.id)

        now_utc = datetime.now(timezone.utc)

        # Create paid event that ended 10 hours ago (way past buffer)
        end_time_10h_ago = now_utc - timedelta(hours=10)
        google_event_id = "test_paid_event_10h_ago"

        # Create payment in database
        cliente = Client(name="Test Client")
        artista = User(
            name="Test Artist", email="test@example.com", password_hash="dummy"
        )
        db_session.add(cliente)
        db_session.add(artista)
        db_session.flush()

        pagamento = Pagamento(
            data=datetime.now().date(),
            valor=150.0,
            forma_pagamento="Dinheiro",
            cliente_id=cliente.id,
            artista_id=artista.id,
            google_event_id=google_event_id,
        )
        db_session.add(pagamento)
        db_session.commit()

        # Mock event
        mock_event = MagicMock()
        mock_event.google_event_id = google_event_id
        mock_event.title = "Paid Old Event"
        mock_event.start_time = end_time_10h_ago - timedelta(hours=2)
        mock_event.end_time = end_time_10h_ago
        mock_event.description = "Test"
        mock_event.location = None
        mock_event.attendees = []

        with patch(
            "app.controllers.calendar_controller._get_calendar_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.is_user_authorized.return_value = True
            mock_service.get_user_events.return_value = [mock_event]
            mock_get_service.return_value = mock_service

            response = client.get("/calendar/")
            assert response.status_code == 200

            # Event SHOULD be visible (has payment, even past 6h buffer)
            html_content = response.data.decode("utf-8")
            assert "Paid Old Event" in html_content
            assert "Concluído" in html_content  # Should show completed button


class TestAgendaButtonStates:
    """Test button label and state rendering."""

    def test_unpaid_event_shows_registrar_pagamento(
        self, client, db_session, sample_artist
    ):
        """Unpaid events should show 'Registrar Pagamento' button."""
        # Set up authenticated session
        with client.session_transaction() as sess:
            sess["user_id"] = sample_artist.id
            sess["_user_id"] = str(sample_artist.id)

        now_utc = datetime.now(timezone.utc)
        future_time = now_utc + timedelta(hours=2)

        mock_event = MagicMock()
        mock_event.google_event_id = "test_unpaid_event"
        mock_event.title = "Unpaid Event"
        mock_event.start_time = future_time
        mock_event.end_time = future_time + timedelta(hours=2)
        mock_event.description = "Test"
        mock_event.location = None
        mock_event.attendees = []

        with patch(
            "app.controllers.calendar_controller._get_calendar_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.is_user_authorized.return_value = True
            mock_service.get_user_events.return_value = [mock_event]
            mock_get_service.return_value = mock_service

            response = client.get("/calendar/")
            html_content = response.data.decode("utf-8")

            assert "Registrar Pagamento" in html_content
            assert "Concluído" not in html_content
            assert "create-session-btn" in html_content

    def test_paid_event_shows_concluido_button(self, client, db_session, sample_artist):
        """Paid events should show green 'Concluído' button."""
        # Set up authenticated session
        with client.session_transaction() as sess:
            sess["user_id"] = sample_artist.id
            sess["_user_id"] = str(sample_artist.id)

        google_event_id = "test_paid_event"

        # Create payment
        cliente = Client(name="Test Client")
        artista = User(
            name="Test Artist", email="test@example.com", password_hash="dummy"
        )
        db_session.add(cliente)
        db_session.add(artista)
        db_session.flush()

        pagamento = Pagamento(
            data=datetime.now().date(),
            valor=200.0,
            forma_pagamento="Dinheiro",
            cliente_id=cliente.id,
            artista_id=artista.id,
            google_event_id=google_event_id,
        )
        db_session.add(pagamento)
        db_session.commit()

        # Mock event
        now_utc = datetime.now(timezone.utc)
        future_time = now_utc + timedelta(hours=2)
        mock_event = MagicMock()
        mock_event.google_event_id = google_event_id
        mock_event.title = "Paid Event"
        mock_event.start_time = future_time
        mock_event.end_time = future_time + timedelta(hours=2)
        mock_event.description = "Test"
        mock_event.location = None
        mock_event.attendees = []

        with patch(
            "app.controllers.calendar_controller._get_calendar_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.is_user_authorized.return_value = True
            mock_service.get_user_events.return_value = [mock_event]
            mock_get_service.return_value = mock_service

            response = client.get("/calendar/")
            html_content = response.data.decode("utf-8")

            assert "Concluído" in html_content
            assert "Registrar Pagamento" not in html_content
            assert "button-success" in html_content  # Green styling

    def test_button_aria_labels_present(self, client, db_session, sample_artist):
        """Buttons should have proper aria-labels for accessibility."""
        # Set up authenticated session
        with client.session_transaction() as sess:
            sess["user_id"] = sample_artist.id
            sess["_user_id"] = str(sample_artist.id)

        google_event_id = "test_aria_event"

        # Create payment
        cliente = Client(name="Test Client")
        artista = User(
            name="Test Artist", email="test@example.com", password_hash="dummy"
        )
        db_session.add(cliente)
        db_session.add(artista)
        db_session.flush()

        pagamento = Pagamento(
            data=datetime.now().date(),
            valor=200.0,
            forma_pagamento="Dinheiro",
            cliente_id=cliente.id,
            artista_id=artista.id,
            google_event_id=google_event_id,
        )
        db_session.add(pagamento)
        db_session.commit()

        # Mock event
        now_utc = datetime.now(timezone.utc)
        future_time = now_utc + timedelta(hours=2)
        mock_event = MagicMock()
        mock_event.google_event_id = google_event_id
        mock_event.title = "Aria Test Event"
        mock_event.start_time = future_time
        mock_event.end_time = future_time + timedelta(hours=2)
        mock_event.description = "Test"
        mock_event.location = None
        mock_event.attendees = []

        with patch(
            "app.controllers.calendar_controller._get_calendar_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.is_user_authorized.return_value = True
            mock_service.get_user_events.return_value = [mock_event]
            mock_get_service.return_value = mock_service

            response = client.get("/calendar/")
            html_content = response.data.decode("utf-8")

            # Check for aria-labels
            assert (
                'aria-label="Evento concluído - ver detalhes no histórico"'
                in html_content
            )


class TestGoogleEventIdHiddenInUI:
    """Test that google_event_id is hidden from user-facing UI."""

    def test_google_event_id_not_visible_in_details(
        self, client, db_session, sample_artist
    ):
        """google_event_id should not appear in the details table."""
        # Set up authenticated session
        with client.session_transaction() as sess:
            sess["user_id"] = sample_artist.id
            sess["_user_id"] = str(sample_artist.id)

        google_event_id = "test_hidden_id"

        now_utc = datetime.now(timezone.utc)
        future_time = now_utc + timedelta(hours=2)

        mock_event = MagicMock()
        mock_event.google_event_id = google_event_id
        mock_event.title = "Test Event"
        mock_event.start_time = future_time
        mock_event.end_time = future_time + timedelta(hours=2)
        mock_event.description = "Test Description"
        mock_event.location = "Test Location"
        mock_event.attendees = ["test@example.com"]

        with patch(
            "app.controllers.calendar_controller._get_calendar_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.is_user_authorized.return_value = True
            mock_service.get_user_events.return_value = [mock_event]
            mock_get_service.return_value = mock_service

            response = client.get("/calendar/")
            html_content = response.data.decode("utf-8")

            # Check that details are present
            assert "Test Description" in html_content
            assert "Test Location" in html_content
            assert "test@example.com" in html_content

            # But google_event_id is NOT visible in table
            assert "ID do Google" not in html_content
        # Note: google_event_id might still be in hidden form fields or URLs (which is OK)


class TestDuplicatePaymentHandling:
    """Test that duplicate payment attempts are handled gracefully."""

    def test_duplicate_payment_shows_friendly_message(
        self, client, db_session, sample_artist
    ):
        """Attempting to pay for already-paid event should show friendly message."""
        # Set up authenticated session
        with client.session_transaction() as sess:
            sess["user_id"] = sample_artist.id
            sess["_user_id"] = str(sample_artist.id)

        google_event_id = "test_duplicate_event"

        # Create existing payment
        cliente = Client(name="Test Client")
        artista = User(
            name="Test Artist", email="test@example.com", password_hash="dummy"
        )
        db_session.add(cliente)
        db_session.add(artista)
        db_session.flush()

        existing_payment = Pagamento(
            data=datetime.now().date(),
            valor=150.0,
            forma_pagamento="Dinheiro",
            cliente_id=cliente.id,
            artista_id=artista.id,
            google_event_id=google_event_id,
        )
        db_session.add(existing_payment)
        db_session.commit()
        existing_payment_id = existing_payment.id

        # Attempt to create duplicate payment
        from app.core import config as app_config

        with patch.object(app_config, "is_email_authorized", return_value=True):
            response = client.post(
                "/financeiro/registrar-pagamento",
                data={
                    "data": datetime.now().strftime("%Y-%m-%d"),
                    "valor": "200.00",
                    "forma_pagamento": "Dinheiro",
                    "cliente_id": cliente.id,
                    "artista_id": artista.id,
                    "google_event_id": google_event_id,
                    "observacoes": "Duplicate attempt",
                },
                follow_redirects=False,
            )

        # Should redirect to historico
        assert response.status_code == 302
        assert "/historico" in response.location

        # Check audit log
        audit_entry = (
            db_session.query(MigrationAudit)
            .filter_by(
                entity_type="pagamento_duplicate_attempt", entity_id=existing_payment_id
            )
            .first()
        )

        assert audit_entry is not None
        assert audit_entry.action == "duplicate_blocked"
        assert audit_entry.status == "blocked"
        assert audit_entry.details["google_event_id"] == google_event_id


class TestTimezoneCorrectness:
    """Test that timezone handling is correct for 6-hour buffer."""

    def test_naive_datetime_treated_as_utc(self, client, db_session, sample_artist):
        """Naive datetimes should be treated as UTC for comparison."""
        # Set up authenticated session
        with client.session_transaction() as sess:
            sess["user_id"] = sample_artist.id
            sess["_user_id"] = str(sample_artist.id)

        now_utc = datetime.now(timezone.utc)

        # Create naive datetime 4 hours ago (within buffer)
        naive_end_time = datetime.utcnow() - timedelta(hours=4)  # Naive treated as UTC

        mock_event = MagicMock()
        mock_event.google_event_id = "test_naive_event"
        mock_event.title = "Naive Time Event"
        mock_event.start_time = naive_end_time - timedelta(hours=2)
        mock_event.end_time = naive_end_time  # Naive datetime
        mock_event.description = "Test"
        mock_event.location = None
        mock_event.attendees = []

        with patch(
            "app.controllers.calendar_controller._get_calendar_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.is_user_authorized.return_value = True
            mock_service.get_user_events.return_value = [mock_event]
            mock_get_service.return_value = mock_service

            response = client.get("/calendar/")
            html_content = response.data.decode("utf-8")

            # Should be visible (treated as UTC, within 6h buffer)
            assert "Naive Time Event" in html_content

    def test_timezone_aware_datetime_compared_correctly(
        self, client, db_session, sample_artist
    ):
        """Timezone-aware datetimes should be compared correctly."""
        # Set up authenticated session
        with client.session_transaction() as sess:
            sess["user_id"] = sample_artist.id
            sess["_user_id"] = str(sample_artist.id)

        now_utc = datetime.now(timezone.utc)

        # Create timezone-aware datetime 5 hours ago (within buffer)
        aware_end_time = now_utc - timedelta(hours=5)

        mock_event = MagicMock()
        mock_event.google_event_id = "test_aware_event"
        mock_event.title = "Aware Time Event"
        mock_event.start_time = aware_end_time - timedelta(hours=2)
        mock_event.end_time = aware_end_time  # Timezone-aware
        mock_event.description = "Test"
        mock_event.location = None
        mock_event.attendees = []

        with patch(
            "app.controllers.calendar_controller._get_calendar_service"
        ) as mock_get_service:
            mock_service = MagicMock()
            mock_service.is_user_authorized.return_value = True
            mock_service.get_user_events.return_value = [mock_event]
            mock_get_service.return_value = mock_service

            response = client.get("/calendar/")
            html_content = response.data.decode("utf-8")

            # Should be visible (within 6h buffer)
            assert "Aware Time Event" in html_content
