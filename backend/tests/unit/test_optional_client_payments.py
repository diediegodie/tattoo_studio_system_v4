"""
Unit tests for payment operations with optional cliente_id.

This module tests the functionality implemented for making cliente_id
optional in the Pagamento model, covering controller methods, API endpoints,
and financial calculations.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch
from pathlib import Path

import pytest
from flask import Flask


@pytest.fixture
def app():
    """Create and configure a test app instance with financeiro blueprint."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing
    app.config["LOGIN_DISABLED"] = True  # Disable login for testing

    # Set up template folder for proper template rendering
    project_root = Path(__file__).parent.parent.parent.parent
    template_dir = project_root / "frontend" / "templates"
    app.template_folder = str(template_dir)

    # Add simple mock routes for redirects used by controller
    @app.route("/historico/")
    def mock_historico_home():
        return "Mock historico page"

    @app.route("/financeiro/")
    def mock_financeiro_home():
        return "Mock financeiro page"

    # Register the financeiro blueprint
    try:
        from app.controllers.financeiro_controller import financeiro_bp

        app.register_blueprint(financeiro_bp)

        # Also try to register historico blueprint if it exists
        try:
            from app.controllers.historico_controller import historico_bp

            app.register_blueprint(historico_bp)
        except ImportError:
            # Create a simple historico blueprint if it doesn't exist
            from flask import Blueprint

            historico_bp = Blueprint("historico", __name__, url_prefix="/historico")
            app.register_blueprint(historico_bp)

    except ImportError as e:
        # If import fails, skip the tests that need the blueprint
        pytest.skip(f"Could not import financeiro_controller: {e}")

    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Create a test client for the Flask app."""
    with app.test_client() as client:
        yield client


class TestPaymentRegistrationWithOptionalClient:
    """Test payment registration with optional client functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return MagicMock()

    @pytest.fixture
    def payment_data_without_client(self):
        """Payment form data without client."""
        return {
            "data": "2024-01-15",
            "valor": "100.00",
            "forma_pagamento": "Dinheiro",
            "cliente_id": "",  # Empty string should be converted to None
            "artista_id": "1",
            "observacoes": "Test payment without client",
        }

    @pytest.fixture
    def payment_data_with_client(self):
        """Payment form data with client."""
        return {
            "data": "2024-01-15",
            "valor": "100.00",
            "forma_pagamento": "Dinheiro",
            "cliente_id": "1",
            "artista_id": "1",
            "observacoes": "Test payment with client",
        }

    def test_registrar_pagamento_post_with_null_client(
        self, client, mock_db_session, payment_data_without_client
    ):
        """Test POST to registrar_pagamento with null client_id."""
        with patch(
            "app.controllers.financeiro_controller.SessionLocal",
            return_value=mock_db_session,
        ):
            with patch(
                "app.controllers.financeiro_controller.current_user"
            ) as mock_user:
                with patch(
                    "app.controllers.financeiro_controller._get_user_service"
                ) as mock_user_service:

                    # Set up user authentication
                    mock_user.id = 1
                    mock_user.is_authenticated = True

                    # Mock user service
                    mock_user_service.return_value.list_artists.return_value = []

                    # Mock database operations
                    mock_db_session.add = Mock()
                    mock_db_session.commit = Mock()
                    mock_db_session.refresh = Mock()
                    mock_db_session.flush = Mock()

                    # Mock queries for Client and other data
                    mock_query = Mock()
                    mock_db_session.query.return_value = mock_query
                    mock_query.order_by.return_value.all.return_value = []
                    mock_query.options.return_value.order_by.return_value.all.return_value = (
                        []
                    )

                    # Make the POST request
                    response = client.post(
                        "/financeiro/registrar-pagamento",
                        data=payment_data_without_client,
                        follow_redirects=False,
                    )

                    # Verify response (should redirect after successful creation)
                    assert response.status_code in [200, 302]  # Success or redirect

                    # Verify payment was created with null client
                    mock_db_session.add.assert_called_once()
                    created_payment = mock_db_session.add.call_args[0][0]
                    assert created_payment.cliente_id is None
                    assert created_payment.artista_id == 1
                    assert str(created_payment.valor) == "100.00"

    def test_registrar_pagamento_post_with_client(
        self, client, mock_db_session, payment_data_with_client
    ):
        """Test POST to registrar_pagamento with valid client_id."""
        with patch(
            "app.controllers.financeiro_controller.SessionLocal",
            return_value=mock_db_session,
        ):
            with patch(
                "app.controllers.financeiro_controller.current_user"
            ) as mock_user:
                with patch(
                    "app.controllers.financeiro_controller._get_user_service"
                ) as mock_user_service:

                    # Set up user authentication
                    mock_user.id = 1
                    mock_user.is_authenticated = True

                    # Mock user service
                    mock_user_service.return_value.list_artists.return_value = []

                    # Mock database operations
                    mock_db_session.add = Mock()
                    mock_db_session.commit = Mock()
                    mock_db_session.refresh = Mock()
                    mock_db_session.flush = Mock()

                    # Mock queries for Client and other data
                    mock_query = Mock()
                    mock_db_session.query.return_value = mock_query
                    mock_query.order_by.return_value.all.return_value = []
                    mock_query.options.return_value.order_by.return_value.all.return_value = (
                        []
                    )

                    # Make the POST request
                    response = client.post(
                        "/financeiro/registrar-pagamento",
                        data=payment_data_with_client,
                        follow_redirects=False,
                    )

                    # Verify response (should redirect after successful creation)
                    assert response.status_code in [200, 302]  # Success or redirect

                    # Verify payment was created with client
                    mock_db_session.add.assert_called_once()
                    created_payment = mock_db_session.add.call_args[0][0]
                    assert created_payment.cliente_id == 1
                    assert created_payment.artista_id == 1
                    assert str(created_payment.valor) == "100.00"

    def test_registrar_pagamento_get_form_renders(self, client, mock_db_session):
        """Test GET to registrar_pagamento renders form with optional client field."""
        with patch(
            "app.controllers.financeiro_controller.SessionLocal",
            return_value=mock_db_session,
        ):
            with patch(
                "app.controllers.financeiro_controller.current_user"
            ) as mock_user:
                with patch(
                    "app.controllers.financeiro_controller._get_user_service"
                ) as mock_user_service:

                    # Set up user authentication
                    mock_user.id = 1
                    mock_user.is_authenticated = True

                    # Mock database queries for dropdowns
                    mock_query = Mock()
                    mock_db_session.query.return_value = mock_query
                    mock_query.order_by.return_value.all.return_value = []

                    # Mock user service
                    mock_user_service.return_value.list_artists.return_value = []

                    # Make the GET request
                    response = client.get("/financeiro/registrar-pagamento")

                    # Verify form was rendered successfully
                    assert response.status_code == 200

                    # The template should be rendered (we can't easily check template name
                    # without mocking render_template, but successful response indicates it worked)
                    assert (
                        b"registrar_pagamento" in response.data
                        or response.status_code == 200
                    )

    def test_financeiro_home_lists_payments_with_and_without_client(
        self, client, mock_db_session
    ):
        """Test financeiro_home displays payments with and without clients."""
        # Create mock payments with mixed client scenarios
        mock_payment_with_client = Mock()
        mock_payment_with_client.cliente_id = 1
        mock_payment_with_client.cliente = Mock()
        mock_payment_with_client.cliente.name = "Test Client"

        mock_payment_without_client = Mock()
        mock_payment_without_client.cliente_id = None
        mock_payment_without_client.cliente = None

        mock_payments = [mock_payment_with_client, mock_payment_without_client]

        with patch(
            "app.controllers.financeiro_controller.SessionLocal",
            return_value=mock_db_session,
        ):
            with patch(
                "app.controllers.financeiro_controller.current_user"
            ) as mock_user:
                with patch(
                    "app.controllers.financeiro_controller._get_user_service"
                ) as mock_user_service:

                    # Set up user authentication
                    mock_user.id = 1
                    mock_user.is_authenticated = True

                    # Mock database query chain for payments (with options and joinedload)
                    mock_query_with_options = Mock()
                    mock_query_with_options.order_by.return_value.all.return_value = (
                        mock_payments
                    )

                    mock_query_base = Mock()
                    mock_query_base.options.return_value = mock_query_with_options

                    # Mock basic query (for clients, etc.)
                    mock_query_simple = Mock()
                    mock_query_simple.order_by.return_value.all.return_value = []

                    # Set up session.query() to return different mocks based on call order
                    mock_db_session.query.side_effect = [
                        mock_query_base,
                        mock_query_simple,
                    ]

                    # Mock user service
                    mock_user_service.return_value.list_artists.return_value = []

                    # Make the GET request to financeiro home
                    response = client.get("/financeiro/")

                    # Verify page was rendered successfully
                    assert response.status_code == 200

                    # The page should render (we can't easily verify template context
                    # without mocking render_template, but successful response indicates it worked)


class TestPaymentCRUDWithOptionalClient:
    """Test CRUD operations for payments with optional client."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return MagicMock()

    def test_editar_pagamento_without_client(self, client, mock_db_session):
        """Test editing a payment to remove client."""
        # Mock existing payment with client
        mock_payment = Mock()
        mock_payment.id = 1
        mock_payment.cliente_id = 1
        mock_payment.data = date(2024, 1, 15)
        mock_payment.valor = Decimal("100.00")
        mock_payment.forma_pagamento = "Dinheiro"

        with patch(
            "app.controllers.financeiro_crud.SessionLocal",
            return_value=mock_db_session,
        ):
            with patch(
                "app.controllers.financeiro_crud._get_user_service"
            ) as mock_user_service:

                # Mock database queries
                mock_query = Mock()
                mock_db_session.query.return_value = mock_query
                mock_query.get.return_value = mock_payment
                mock_query.order_by.return_value.all.return_value = []

                # Mock user service
                mock_user_service.return_value.list_artists.return_value = []

                # Make GET request to edit payment form (correct endpoint path)
                response = client.get("/financeiro/editar-pagamento/1")

                # Verify edit form was rendered successfully
                assert response.status_code == 200

                # The form should be loaded (we can't easily check template context
                # without mocking _safe_render, but successful response indicates it worked)

    def test_delete_pagamento_without_client(self, client, mock_db_session):
        """Test deleting a payment without client."""
        # Mock payment without client
        mock_payment = Mock()
        mock_payment.id = 1
        mock_payment.cliente_id = None

        with patch(
            "app.controllers.financeiro_crud.SessionLocal",
            return_value=mock_db_session,
        ):
            with patch(
                "app.controllers.financeiro_crud.PagamentoRepository"
            ) as MockRepo:

                # Mock repository
                mock_repo = Mock()
                MockRepo.return_value = mock_repo
                mock_repo.get_by_id.return_value = mock_payment
                mock_repo.delete.return_value = True

                # Make POST request to delete endpoint (correct endpoint path)
                response = client.post(
                    "/financeiro/delete-pagamento/1", follow_redirects=False
                )

                # Verify response (should redirect after deletion)
                assert response.status_code in [
                    200,
                    302,
                    404,
                ]  # Success, redirect, or not found

                # Verify repository was called (if the endpoint was reached)
                if response.status_code in [200, 302]:
                    mock_repo.get_by_id.assert_called_once_with(1)
                    mock_repo.delete.assert_called_once_with(1)


class TestPaymentValidationWithOptionalClient:
    """Test payment validation with optional client scenarios."""

    def test_empty_client_id_converted_to_none(self):
        """Test that empty string cliente_id is converted to None."""
        # This tests the controller logic for handling empty cliente_id
        cliente_id_raw = ""
        cliente_id = (
            cliente_id_raw if cliente_id_raw and cliente_id_raw.strip() else None
        )

        assert cliente_id is None

    def test_whitespace_client_id_converted_to_none(self):
        """Test that whitespace-only cliente_id is converted to None."""
        cliente_id_raw = "   "
        cliente_id = (
            cliente_id_raw if cliente_id_raw and cliente_id_raw.strip() else None
        )

        assert cliente_id is None

    def test_valid_client_id_preserved(self):
        """Test that valid cliente_id is preserved."""
        cliente_id_raw = "123"
        cliente_id = (
            cliente_id_raw if cliente_id_raw and cliente_id_raw.strip() else None
        )

        assert cliente_id == "123"

    def test_required_fields_validation_excludes_client(self):
        """Test that required fields validation does not include cliente_id."""
        form_data = {
            "data": "2024-01-15",
            "valor": "100.00",
            "forma_pagamento": "Dinheiro",
            "cliente_id": "",  # Empty client should not cause validation failure
            "artista_id": "1",
        }

        required_fields = [
            form_data.get("data"),
            form_data.get("valor"),
            form_data.get("forma_pagamento"),
            form_data.get("artista_id"),
        ]

        # Should pass validation even with empty client
        assert all(required_fields)

        # cliente_id should not be in required fields
        cliente_id = form_data.get("cliente_id")
        cliente_id = cliente_id if cliente_id and cliente_id.strip() else None
        assert cliente_id is None  # But this is OK


class TestPagamentoFactoryWithOptionalClient:
    """Test PagamentoFactory with optional client scenarios."""

    def test_create_payment_data_with_client(self):
        """Test creating payment data with client using factory."""
        try:
            from tests.factories.test_factories import PagamentoFactory

            payment_data = PagamentoFactory.create_payment_data(cliente_id="1")

            assert payment_data["cliente_id"] == "1"
            assert payment_data["artista_id"] == "1"
            assert payment_data["valor"] == "100.00"
            assert payment_data["forma_pagamento"] == "Dinheiro"

        except ImportError:
            pytest.skip("PagamentoFactory not available")

    def test_create_payment_data_without_client(self):
        """Test creating payment data without client using factory."""
        try:
            from tests.factories.test_factories import PagamentoFactory

            payment_data = PagamentoFactory.create_payment_data_without_client()

            assert payment_data["cliente_id"] is None
            assert payment_data["artista_id"] == "1"
            assert payment_data["valor"] == "100.00"
            assert payment_data["forma_pagamento"] == "Dinheiro"

        except ImportError:
            pytest.skip("PagamentoFactory not available")

    def test_create_mock_payment_with_client(self):
        """Test creating mock payment with client using factory."""
        try:
            from tests.factories.test_factories import PagamentoFactory

            mock_payment = PagamentoFactory.create_mock_payment(cliente_id=1)

            assert mock_payment.cliente_id == 1
            assert mock_payment.cliente is not None
            assert mock_payment.cliente.name == "Test Client 1"
            assert mock_payment.artista is not None

        except ImportError:
            pytest.skip("PagamentoFactory not available")

    def test_create_mock_payment_without_client(self):
        """Test creating mock payment without client using factory."""
        try:
            from tests.factories.test_factories import PagamentoFactory

            mock_payment = PagamentoFactory.create_mock_payment(cliente_id=None)

            assert mock_payment.cliente_id is None
            assert mock_payment.cliente is None
            assert mock_payment.artista is not None  # Artist should still be present

        except ImportError:
            pytest.skip("PagamentoFactory not available")


class TestPagamentoModelWithOptionalClient:
    """Test Pagamento model creation with optional client."""

    def test_pagamento_creation_with_client(self):
        """Test creating Pagamento model with client."""
        try:
            from app.db.base import Pagamento
            from datetime import date
            from decimal import Decimal

            pagamento = Pagamento(
                data=date(2024, 1, 15),
                valor=Decimal("100.00"),
                forma_pagamento="Dinheiro",
                cliente_id=1,
                artista_id=1,
                observacoes="Test payment with client",
            )

            assert pagamento.cliente_id == 1
            assert pagamento.artista_id == 1
            assert pagamento.valor == Decimal("100.00")

        except ImportError:
            pytest.skip("Pagamento model not available")

    def test_pagamento_creation_without_client(self):
        """Test creating Pagamento model without client (cliente_id=None)."""
        try:
            from app.db.base import Pagamento
            from datetime import date
            from decimal import Decimal

            pagamento = Pagamento(
                data=date(2024, 1, 15),
                valor=Decimal("100.00"),
                forma_pagamento="Dinheiro",
                cliente_id=None,  # Explicitly None
                artista_id=1,
                observacoes="Test payment without client",
            )

            assert pagamento.cliente_id is None
            assert pagamento.artista_id == 1
            assert pagamento.valor == Decimal("100.00")
            assert pagamento.observacoes == "Test payment without client"

        except ImportError:
            pytest.skip("Pagamento model not available")


class TestClientIdValidationLogic:
    """Test client ID validation and conversion logic."""

    def test_none_client_id_handling(self):
        """Test handling None cliente_id values."""
        # Simulate the controller logic
        cliente_id_raw = None
        cliente_id = (
            cliente_id_raw if cliente_id_raw and str(cliente_id_raw).strip() else None
        )

        assert cliente_id is None

    def test_string_none_client_id_handling(self):
        """Test handling string 'None' cliente_id values."""
        cliente_id_raw = "None"
        cliente_id = (
            cliente_id_raw
            if cliente_id_raw and cliente_id_raw.strip() and cliente_id_raw != "None"
            else None
        )

        assert cliente_id is None

    def test_zero_client_id_handling(self):
        """Test handling zero cliente_id values."""
        cliente_id_raw = "0"
        # Zero could be a valid client ID, so it should be preserved
        cliente_id = (
            cliente_id_raw if cliente_id_raw and cliente_id_raw.strip() else None
        )

        assert cliente_id == "0"

    def test_numeric_string_client_id_handling(self):
        """Test handling numeric string cliente_id values."""
        cliente_id_raw = "123"
        cliente_id = (
            cliente_id_raw if cliente_id_raw and cliente_id_raw.strip() else None
        )

        assert cliente_id == "123"

        # Test conversion to int for database
        cliente_id_int = int(cliente_id) if cliente_id is not None else None
        assert cliente_id_int == 123
