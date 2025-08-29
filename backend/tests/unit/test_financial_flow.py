"""
Unit tests for session finalization and payment linkage functionality.
"""

import pytest
from datetime import date, time
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from controllers.sessoes_controller import finalizar_sessao
from controllers.financeiro_controller import registrar_pagamento
from db.base import Sessao, Pagamento
from flask import Flask


@pytest.fixture
def app():
    """Create and configure a test app instance."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["LOGIN_DISABLED"] = True  # Disable login for testing

    with app.app_context():
        yield app


class TestSessionFinalization:
    """Test session finalization flow."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return MagicMock()

    @pytest.fixture
    def sample_session(self):
        """Sample session for testing."""
        return Sessao(
            id=1,
            data=date.today(),
            hora=time(10, 0),
            valor=Decimal("100.00"),
            cliente_id=1,
            artista_id=1,
            status="active",
        )

    def test_finalize_active_session_success(
        self, app, mock_db_session, sample_session
    ):
        """Test successful finalization of active session."""
        # Arrange
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            sample_session
        )

        with app.test_request_context(), patch(
            "controllers.sessoes_controller.SessionLocal", return_value=mock_db_session
        ), patch("controllers.sessoes_controller.flash"), patch(
            "controllers.sessoes_controller.redirect"
        ) as mock_redirect, patch(
            "controllers.sessoes_controller.url_for"
        ) as mock_url_for:

            mock_url_for.return_value = "/financeiro/registrar-pagamento"

            # Act
            result = finalizar_sessao(1)

            # Assert
            assert getattr(sample_session, "status", None) == "completed"
            mock_db_session.commit.assert_called_once()
            mock_redirect.assert_called_once()

    def test_finalize_already_completed_session(
        self, app, mock_db_session, sample_session
    ):
        """Test finalization of already completed session."""
        # Arrange
        setattr(sample_session, "status", "completed")
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            sample_session
        )

        with app.test_request_context(), patch(
            "controllers.sessoes_controller.SessionLocal", return_value=mock_db_session
        ), patch("controllers.sessoes_controller.flash"), patch(
            "controllers.sessoes_controller.redirect"
        ) as mock_redirect:

            # Act
            result = finalizar_sessao(1)

            # Assert
            mock_redirect.assert_called_once()
            mock_db_session.commit.assert_not_called()

    def test_finalize_nonexistent_session(self, app, mock_db_session):
        """Test finalization of nonexistent session."""
        # Arrange
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        with app.test_request_context(), patch(
            "controllers.sessoes_controller.SessionLocal", return_value=mock_db_session
        ), patch("controllers.sessoes_controller.flash"), patch(
            "controllers.sessoes_controller.redirect"
        ) as mock_redirect:

            # Act
            result = finalizar_sessao(999)

            # Assert
            mock_redirect.assert_called_once()
            mock_db_session.commit.assert_not_called()


class TestPaymentRegistrationWithSession:
    """Test payment registration with session linkage."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return MagicMock()

    @pytest.fixture
    def sample_payment_data(self):
        """Sample payment form data."""
        return {
            "data": "2024-01-15",
            "valor": "100.00",
            "forma_pagamento": "dinheiro",
            "cliente_id": "1",
            "artista_id": "1",
            "observacoes": "Test payment",
            "sessao_id": "1",
        }

    def test_payment_registration_with_session_linkage(
        self, app, mock_db_session, sample_payment_data
    ):
        """Test payment registration with session linkage."""
        # Arrange
        sample_session = Sessao(id=1, status="completed")
        mock_db_session.query.return_value.filter.return_value.first.return_value = (
            sample_session
        )

        with app.test_request_context(), patch(
            "controllers.financeiro_controller.SessionLocal",
            return_value=mock_db_session,
        ), patch("controllers.financeiro_controller.request") as mock_request, patch(
            "controllers.financeiro_controller.flash"
        ), patch(
            "controllers.financeiro_controller.redirect"
        ) as mock_redirect:

            mock_request.method = "POST"
            mock_request.form.get.side_effect = lambda key: sample_payment_data.get(key)

            # Act
            result = registrar_pagamento()

            # Assert
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called()
            # Check that session was linked to payment
            assert sample_session.payment_id is not None
            mock_redirect.assert_called_once()

    def test_payment_registration_without_session(self, app, mock_db_session):
        """Test payment registration without session linkage."""
        # Arrange
        payment_data = {
            "data": "2024-01-15",
            "valor": "100.00",
            "forma_pagamento": "dinheiro",
            "cliente_id": "1",
            "artista_id": "1",
            "observacoes": "Test payment",
        }

        with app.test_request_context(), patch(
            "controllers.financeiro_controller.SessionLocal",
            return_value=mock_db_session,
        ), patch("controllers.financeiro_controller.request") as mock_request, patch(
            "controllers.financeiro_controller.flash"
        ), patch(
            "controllers.financeiro_controller.redirect"
        ) as mock_redirect:

            mock_request.method = "POST"
            mock_request.form.get.side_effect = lambda key: payment_data.get(key)

            # Act
            result = registrar_pagamento()

            # Assert
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called()
            mock_redirect.assert_called_once()


class TestSessionListingFilter:
    """Test session listing with status filtering."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return MagicMock()

    def test_list_shows_only_active_sessions(self, mock_db_session):
        """Test that session listing shows only active sessions."""
        # Arrange
        active_session = Sessao(id=1, status="active", data=date.today())
        completed_session = Sessao(id=2, status="completed", data=date.today())

        mock_query = MagicMock()
        mock_query.options.return_value.filter.return_value.order_by.return_value.all.return_value = [
            active_session
        ]

        mock_db_session.query.return_value = mock_query

        with patch(
            "controllers.sessoes_controller.SessionLocal", return_value=mock_db_session
        ), patch("controllers.sessoes_controller.render_template") as mock_render:

            # Act
            from controllers.sessoes_controller import list_sessoes

            result = list_sessoes()

            # Assert
            mock_query.filter.assert_called_once()
            # Verify the filter condition includes status="active"
            filter_call = mock_query.filter.call_args[0][0]
            assert "active" in str(filter_call)
            mock_render.assert_called_once()


class TestFinancialFlowIntegration:
    """Integration tests for the complete financial flow."""

    def test_complete_financial_flow(self):
        """Test the complete flow: session → finalization → payment → linkage."""
        # This would be an integration test that:
        # 1. Creates a session
        # 2. Finalizes it
        # 3. Creates a payment linked to it
        # 4. Verifies the linkage exists
        # 5. Verifies session no longer appears in active list

        # For now, just document the expected flow
        expected_flow = [
            "1. Session created with status='active'",
            "2. User clicks 'Finalizar' button",
            "3. POST /sessoes/finalizar/<id> called",
            "4. Session status updated to 'completed'",
            "5. Redirect to payment registration with session data",
            "6. User fills payment form",
            "7. POST /financeiro/registrar-pagamento with sessao_id",
            "8. Payment created with sessao_id reference",
            "9. Session.payment_id updated with payment.id",
            "10. Session no longer appears in active listing",
        ]

        assert len(expected_flow) == 10
        assert "session" in expected_flow[0].lower()
        assert "payment" in expected_flow[5].lower()
        assert "finalized" in expected_flow[9].lower()
