"""
Test factories for creating Sessao and related objects.

These factories provide convenient ways to create test data
following SOLID principles and supporting the P0 test scenarios.
"""

from datetime import date, datetime, time
from decimal import Decimal
from unittest.mock import Mock


class SessaoFactory:
    """Factory for creating Sessao test objects."""

    @staticmethod
    def create_sessao_data(**kwargs):
        """
        Create Sessao data dictionary with sensible defaults.

        Args:
            **kwargs: Override any default values

        Returns:
            dict: Sessao data ready for model instantiation
        """
        defaults = {
            "data": date(2025, 8, 30),
            "valor": Decimal("100.00"),
            "observacoes": "Test session",
            "cliente_id": 1,
            "artista_id": 1,
            "google_event_id": None,
        }
        defaults.update(kwargs)
        return defaults

    @staticmethod
    def create_with_google_event_id(google_event_id, **kwargs):
        """
        Create Sessao data with specific google_event_id.

        Args:
            google_event_id (str): Google Calendar event ID
            **kwargs: Additional overrides

        Returns:
            dict: Sessao data with google_event_id set
        """
        return SessaoFactory.create_sessao_data(
            google_event_id=google_event_id, **kwargs
        )

    @staticmethod
    def create_manual_session(**kwargs):
        """
        Create Sessao data for manual session (no google_event_id).

        Args:
            **kwargs: Override any default values

        Returns:
            dict: Sessao data with google_event_id=None
        """
        return SessaoFactory.create_sessao_data(
            google_event_id=None, observacoes="Manual session", **kwargs
        )

    @staticmethod
    def create_mock_sessao(**kwargs):
        """
        Create a Mock Sessao object for unit tests.

        Args:
            **kwargs: Override any default values

        Returns:
            Mock: Mock Sessao object with realistic attributes
        """
        data = SessaoFactory.create_sessao_data(**kwargs)

        mock_sessao = Mock()
        for key, value in data.items():
            setattr(mock_sessao, key, value)

        # Add commonly needed mock attributes
        mock_sessao.id = kwargs.get("id", 1)
        mock_sessao.created_at = kwargs.get("created_at", datetime(2025, 8, 28, 10, 0))
        mock_sessao.updated_at = kwargs.get("updated_at", datetime(2025, 8, 28, 10, 0))

        return mock_sessao


class ClientFactory:
    """Factory for creating Client test objects."""

    @staticmethod
    def create_client_data(**kwargs):
        """
        Create Client data dictionary with sensible defaults.

        Args:
            **kwargs: Override any default values

        Returns:
            dict: Client data ready for model instantiation
        """
        defaults = {
            "name": "Test Client",
            "email": "client@example.com",
            "phone": "123456789",
        }
        defaults.update(kwargs)
        return defaults

    @staticmethod
    def create_mock_client(**kwargs):
        """
        Create a Mock Client object for unit tests.

        Args:
            **kwargs: Override any default values

        Returns:
            Mock: Mock Client object
        """
        data = ClientFactory.create_client_data(**kwargs)

        mock_client = Mock()
        for key, value in data.items():
            setattr(mock_client, key, value)

        mock_client.id = kwargs.get("id", 1)
        return mock_client


class UserFactory:
    """Factory for creating User (Artist) test objects."""

    @staticmethod
    def create_artist_data(**kwargs):
        """
        Create User data for artist with sensible defaults.

        Args:
            **kwargs: Override any default values

        Returns:
            dict: User data ready for model instantiation
        """
        defaults = {
            "name": "Test Artist",
            "email": "artist@example.com",
            "role": "artist",
            "is_active": True,
        }
        defaults.update(kwargs)
        return defaults

    @staticmethod
    def create_mock_artist(**kwargs):
        """
        Create a Mock User (artist) object for unit tests.

        Args:
            **kwargs: Override any default values

        Returns:
            Mock: Mock User object configured as artist
        """
        data = UserFactory.create_artist_data(**kwargs)

        mock_artist = Mock()
        for key, value in data.items():
            setattr(mock_artist, key, value)

        mock_artist.id = kwargs.get("id", 1)
        return mock_artist


class GoogleEventFactory:
    """Factory for creating Google Calendar event mock objects."""

    @staticmethod
    def create_google_event(**kwargs):
        """
        Create a Mock Google Calendar event.

        Args:
            **kwargs: Override any default values

        Returns:
            Mock: Mock Google Calendar event object
        """
        defaults = {
            "google_event_id": "GOOGLE_EVENT_123",
            "id": "GOOGLE_EVENT_123",
            "title": "Test Google Event",
            "description": "Test event description",
            "start_time": datetime(2025, 8, 30, 14, 0),
            "end_time": datetime(2025, 8, 30, 15, 0),
            "location": "Studio",
        }
        defaults.update(kwargs)

        mock_event = Mock()
        for key, value in defaults.items():
            setattr(mock_event, key, value)

        return mock_event

    @staticmethod
    def create_google_events_list(event_ids):
        """
        Create a list of Google Calendar events with specific IDs.

        Args:
            event_ids (list): List of Google event IDs to create

        Returns:
            list: List of Mock Google Calendar event objects
        """
        events = []
        for i, event_id in enumerate(event_ids):
            event = GoogleEventFactory.create_google_event(
                google_event_id=event_id,
                id=event_id,
                title=f"Event {i+1}",
                description=f"Description for event {i+1}",
                start_time=datetime(2025, 8, 30, 10 + i, 0),
                end_time=datetime(2025, 8, 30, 11 + i, 0),
            )
            events.append(event)
        return events


class PagamentoFactory:
    """Factory for creating Pagamento test objects."""

    @staticmethod
    def create_payment_data(**kwargs):
        """
        Create payment data dictionary with sensible defaults.

        Args:
            **kwargs: Override any default values. Use cliente_id=None for payments without clients.

        Returns:
            dict: Payment data ready for model instantiation or form submission
        """
        defaults = {
            "data": "2024-01-15",
            "valor": "100.00",
            "forma_pagamento": "Dinheiro",
            "cliente_id": "1",  # Default to having a client
            "artista_id": "1",
            "observacoes": "Test payment",
            "sessao_id": None,  # Optional session linkage
        }
        defaults.update(kwargs)
        return defaults

    @staticmethod
    def create_payment_data_without_client(**kwargs):
        """
        Create payment data for payments without a client.

        Args:
            **kwargs: Override any default values

        Returns:
            dict: Payment data without cliente_id
        """
        base_data = PagamentoFactory.create_payment_data(**kwargs)
        base_data["cliente_id"] = None  # No client
        return base_data

    @staticmethod
    def create_mock_payment(**kwargs):
        """
        Create a Mock Pagamento object for unit tests.

        Args:
            **kwargs: Override any default values

        Returns:
            Mock: Mock Pagamento object
        """
        from decimal import Decimal
        from datetime import date

        defaults = {
            "id": 1,
            "data": date(2024, 1, 15),
            "valor": Decimal("100.00"),
            "forma_pagamento": "Dinheiro",
            "observacoes": "Test payment",
            "cliente_id": 1,
            "artista_id": 1,
            "sessao_id": None,
        }
        defaults.update(kwargs)

        mock_payment = Mock()
        for key, value in defaults.items():
            setattr(mock_payment, key, value)

        # Add client relationship mock
        if defaults.get("cliente_id"):
            mock_client = Mock()
            mock_client.id = defaults["cliente_id"]
            mock_client.name = f"Test Client {defaults['cliente_id']}"
            mock_payment.cliente = mock_client
        else:
            mock_payment.cliente = None

        # Add artist relationship mock
        mock_artist = Mock()
        mock_artist.id = defaults["artista_id"]
        mock_artist.name = f"Test Artist {defaults['artista_id']}"
        mock_payment.artista = mock_artist

        return mock_payment


class FormDataFactory:
    """Factory for creating form data for testing."""

    @staticmethod
    def create_sessao_form_data(**kwargs):
        """
        Create form data for session creation/update.

        Args:
            **kwargs: Override any default values

        Returns:
            dict: Form data ready for HTTP request
        """
        defaults = {
            "data": "2025-08-30",
            "cliente_id": "1",
            "artista_id": "1",
            "valor": "100.00",
            "observacoes": "Test session",
        }
        defaults.update(kwargs)
        return defaults

    @staticmethod
    def create_google_session_form_data(google_event_id, **kwargs):
        """
        Create form data for Google Calendar session creation.

        Args:
            google_event_id (str): Google Calendar event ID
            **kwargs: Override any default values

        Returns:
            dict: Form data with google_event_id included
        """
        form_data = FormDataFactory.create_sessao_form_data(**kwargs)
        form_data["google_event_id"] = google_event_id
        return form_data

    @staticmethod
    def create_manual_session_form_data(**kwargs):
        """
        Create form data for manual session creation (no google_event_id).

        Args:
            **kwargs: Override any default values

        Returns:
            dict: Form data without google_event_id
        """
        form_data = FormDataFactory.create_sessao_form_data(**kwargs)
        # Ensure google_event_id is not in the form data
        form_data.pop("google_event_id", None)
        return form_data


# Convenience functions for common test scenarios
def create_test_session_with_google(db_session, google_event_id="TEST_GOOGLE_ID"):
    """
    Create and persist a test session with google_event_id.

    Args:
        db_session: Database session
        google_event_id (str): Google Calendar event ID

    Returns:
        Sessao: Created session object
    """
    try:
        from db.base import Client, Sessao, User

        # Create client and artist if they don't exist
        client = Client(**ClientFactory.create_client_data())
        artist = User(**UserFactory.create_artist_data())

        db_session.add(client)
        db_session.add(artist)
        db_session.flush()  # Get IDs without committing

        # Create session
        session_data = SessaoFactory.create_with_google_event_id(
            google_event_id=google_event_id, cliente_id=client.id, artista_id=artist.id
        )

        session = Sessao(**session_data)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        return session

    except ImportError:
        # Return mock if models can't be imported
        return SessaoFactory.create_mock_sessao(google_event_id=google_event_id)


def create_test_manual_session(db_session):
    """
    Create and persist a test session without google_event_id.

    Args:
        db_session: Database session

    Returns:
        Sessao: Created session object
    """
    try:
        from db.base import Client, Sessao, User

        # Create client and artist if they don't exist
        client = Client(**ClientFactory.create_client_data(name="Manual Client"))
        artist = User(**UserFactory.create_artist_data(name="Manual Artist"))

        db_session.add(client)
        db_session.add(artist)
        db_session.flush()  # Get IDs without committing

        # Create session
        session_data = SessaoFactory.create_manual_session(
            cliente_id=client.id, artista_id=artist.id
        )

        session = Sessao(**session_data)
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)

        return session

    except ImportError:
        # Return mock if models can't be imported
        return SessaoFactory.create_mock_sessao(google_event_id=None)
