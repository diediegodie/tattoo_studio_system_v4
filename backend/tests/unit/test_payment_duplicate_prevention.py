"""
Tests for payment duplicate prevention.

These tests verify that the duplicate prevention mechanisms work correctly:
- Frontend: button disable + debounce
- Backend: get-or-create logic using composite key
"""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app.db.base import Pagamento, User
from app.db.session import SessionLocal


class TestPaymentDuplicatePrevention:
    """Test suite for payment duplicate prevention."""

    @pytest.fixture
    def sample_payment_data(self):
        """Sample payment data for testing."""
        return {
            "data": "2024-01-15",
            "valor": "100.50",
            "forma_pagamento": "Pix",
            "artista_id": "1",
            "cliente_id": "1",
            "comissao_percent": "50",
            "observacoes": "Test payment",
        }

    @pytest.fixture
    def mock_artist(self, mock_db_session):
        """Create a mock artist user."""
        artist = User(id=1, name="Test Artist", email="artist@test.com", role="artist")
        mock_db_session.add(artist)
        mock_db_session.flush()
        return artist

    def test_duplicate_payment_blocked_by_composite_key(
        self, app, mock_db_session, sample_payment_data, mock_artist
    ):
        """Test that duplicate payments are blocked by composite key check."""
        # Blueprint already registered in app fixture, no need to register again

        # Enable LOGIN_DISABLED to bypass authentication in tests
        app.config["LOGIN_DISABLED"] = True

        # Create first payment
        with app.test_client() as client:
            # Mock authentication
            with patch("flask_login.utils._get_user") as mock_user, patch(
                "app.controllers.financeiro_helpers._get_user_service"
            ) as mock_user_service:
                mock_current_user = MagicMock()
                mock_current_user.id = 1
                mock_current_user.is_authenticated = True
                mock_user.return_value = mock_current_user

                mock_service = MagicMock()
                mock_service.list_artists.return_value = [mock_artist]
                mock_user_service.return_value = mock_service

                # First submission - should succeed
                response1 = client.post(
                    "/financeiro/registrar-pagamento",
                    data=sample_payment_data,
                    follow_redirects=False,
                )

                # Verify first payment was created
                assert response1.status_code in (302, 200)

                # Second submission with identical data - should be blocked
                response2 = client.post(
                    "/financeiro/registrar-pagamento",
                    data=sample_payment_data,
                    follow_redirects=True,
                )

                # Verify redirect to historico (duplicate was blocked)
                assert response2.status_code == 200
                # Response should be historico page
                assert b"Hist" in response2.data or b"historico" in response2.data

                # Verify only one payment exists in database
                db = SessionLocal()
                try:
                    payments = (
                        db.query(Pagamento)
                        .filter(
                            Pagamento.data == date(2024, 1, 15),
                            Pagamento.valor == Decimal("100.50"),
                        )
                        .all()
                    )
                    assert len(payments) == 1
                finally:
                    db.close()

    def test_different_amounts_create_separate_payments(
        self, app, mock_db_session, sample_payment_data, mock_artist
    ):
        """Test that payments with different amounts are treated as separate."""
        # Blueprint already registered in app fixture, no need to register again

        # Enable LOGIN_DISABLED to bypass authentication in tests
        app.config["LOGIN_DISABLED"] = True

        with app.test_client() as client:
            with patch("flask_login.utils._get_user") as mock_user, patch(
                "app.controllers.financeiro_helpers._get_user_service"
            ) as mock_user_service:
                mock_current_user = MagicMock()
                mock_current_user.id = 1
                mock_current_user.is_authenticated = True
                mock_user.return_value = mock_current_user

                mock_service = MagicMock()
                mock_service.list_artists.return_value = [mock_artist]
                mock_user_service.return_value = mock_service

                # First payment
                response1 = client.post(
                    "/financeiro/registrar-pagamento",
                    data=sample_payment_data,
                    follow_redirects=False,
                )
                assert response1.status_code in (302, 200)

                # Second payment with different amount
                data2 = sample_payment_data.copy()
                data2["valor"] = "200.00"
                response2 = client.post(
                    "/financeiro/registrar-pagamento",
                    data=data2,
                    follow_redirects=False,
                )
                assert response2.status_code in (302, 200)

                # Verify two separate payments exist
                db = SessionLocal()
                try:
                    payments = (
                        db.query(Pagamento)
                        .filter(Pagamento.data == date(2024, 1, 15))
                        .all()
                    )
                    assert len(payments) == 2
                finally:
                    db.close()

    def test_different_dates_create_separate_payments(
        self, app, mock_db_session, sample_payment_data, mock_artist
    ):
        """Test that payments on different dates are treated as separate."""
        # Blueprint already registered in app fixture, no need to register again

        # Enable LOGIN_DISABLED to bypass authentication in tests
        app.config["LOGIN_DISABLED"] = True

        with app.test_client() as client:
            with patch("flask_login.utils._get_user") as mock_user, patch(
                "app.controllers.financeiro_helpers._get_user_service"
            ) as mock_user_service:
                mock_current_user = MagicMock()
                mock_current_user.id = 1
                mock_current_user.is_authenticated = True
                mock_user.return_value = mock_current_user

                mock_service = MagicMock()
                mock_service.list_artists.return_value = [mock_artist]
                mock_user_service.return_value = mock_service

                # First payment
                response1 = client.post(
                    "/financeiro/registrar-pagamento",
                    data=sample_payment_data,
                    follow_redirects=False,
                )
                assert response1.status_code in (302, 200)

                # Second payment on different date
                data2 = sample_payment_data.copy()
                data2["data"] = "2024-01-16"
                response2 = client.post(
                    "/financeiro/registrar-pagamento",
                    data=data2,
                    follow_redirects=False,
                )
                assert response2.status_code in (302, 200)

                # Verify two separate payments exist
                db = SessionLocal()
                try:
                    payments = (
                        db.query(Pagamento)
                        .filter(Pagamento.valor == Decimal("100.50"))
                        .all()
                    )
                    assert len(payments) == 2
                finally:
                    db.close()

    def test_duplicate_with_null_cliente_blocked(
        self, app, mock_db_session, mock_artist
    ):
        """Test that duplicate payments without client are also blocked."""
        # Blueprint already registered in app fixture, no need to register again

        # Enable LOGIN_DISABLED to bypass authentication in tests
        app.config["LOGIN_DISABLED"] = True

        payment_data = {
            "data": "2024-01-15",
            "valor": "100.50",
            "forma_pagamento": "Pix",
            "artista_id": "1",
            "cliente_id": "",  # No client
            "comissao_percent": "50",
            "observacoes": "Payment without client",
        }

        with app.test_client() as client:
            with patch("flask_login.utils._get_user") as mock_user, patch(
                "app.controllers.financeiro_helpers._get_user_service"
            ) as mock_user_service:
                mock_current_user = MagicMock()
                mock_current_user.id = 1
                mock_current_user.is_authenticated = True
                mock_user.return_value = mock_current_user

                mock_service = MagicMock()
                mock_service.list_artists.return_value = [mock_artist]
                mock_user_service.return_value = mock_service

                # First submission - should succeed
                response1 = client.post(
                    "/financeiro/registrar-pagamento",
                    data=payment_data,
                    follow_redirects=False,
                )
                assert response1.status_code in (302, 200)

                # Second submission - should be blocked
                response2 = client.post(
                    "/financeiro/registrar-pagamento",
                    data=payment_data,
                    follow_redirects=True,
                )
                assert response2.status_code == 200

                # Verify only one payment exists for THIS test's date + value + forma_pagamento
                db = SessionLocal()
                try:
                    payments = (
                        db.query(Pagamento)
                        .filter(
                            Pagamento.cliente_id.is_(None),
                            Pagamento.data == date(2024, 1, 15),
                            Pagamento.valor == Decimal("100.50"),
                            Pagamento.forma_pagamento == "Pix",
                        )
                        .all()
                    )
                    assert len(payments) == 1
                finally:
                    db.close()
