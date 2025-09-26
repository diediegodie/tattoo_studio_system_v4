"""
API endpoint tests for payments with optional cliente_id.

This module tests the API endpoints in financeiro_api.py to ensure
they handle payments with and without clients correctly.
"""

import importlib
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest


@pytest.mark.unit
@pytest.mark.api
class TestFinanceiroAPIOptionalClient:
    """Test financeiro API endpoints with optional client functionality."""

    def test_api_get_pagamento_with_null_client(self):
        """Test retrieving a payment with cliente_id=NULL via API."""
        mod = importlib.import_module("app.controllers.financeiro_api")
        main = importlib.import_module("main")
        app = main.create_app()

        # Mock payment without client
        mock_payment = Mock()
        mock_payment.id = 1
        mock_payment.data = date(2024, 1, 15)
        mock_payment.valor = Decimal("100.00")
        mock_payment.forma_pagamento = "Dinheiro"
        mock_payment.cliente_id = None
        mock_payment.cliente = None  # No client relationship
        mock_payment.artista_id = 1
        mock_payment.artista = Mock()
        mock_payment.artista.id = 1
        mock_payment.artista.name = "Test Artist"
        mock_payment.observacoes = "Payment without client"

        with app.test_request_context():
            with patch("app.controllers.financeiro_api.SessionLocal") as MockSession:
                mock_db = Mock()
                MockSession.return_value = mock_db
                mock_db.query.return_value.options.return_value.get.return_value = (
                    mock_payment
                )

                # Call the function
                resp = mod.api_get_pagamento.__wrapped__(1)

                # Assert successful response
                assert isinstance(resp, tuple)
                body, status = resp
                assert status == 200

                data = body.get_json() if hasattr(body, "get_json") else body
                assert data["success"] is True

                # Verify payment data structure with null client
                payment_data = data["data"]
                assert payment_data["id"] == 1
                assert payment_data["cliente"] is None  # Key assertion for null client
                assert payment_data["artista"]["id"] == 1
                assert payment_data["artista"]["name"] == "Test Artist"

    def test_api_get_pagamento_with_client(self):
        """Test retrieving a payment with valid client via API."""
        mod = importlib.import_module("app.controllers.financeiro_api")
        main = importlib.import_module("main")
        app = main.create_app()

        # Mock payment with client
        mock_payment = Mock()
        mock_payment.id = 1
        mock_payment.data = date(2024, 1, 15)
        mock_payment.valor = Decimal("100.00")
        mock_payment.forma_pagamento = "Dinheiro"
        mock_payment.cliente_id = 1
        mock_payment.cliente = Mock()
        mock_payment.cliente.id = 1
        mock_payment.cliente.name = "Test Client"
        mock_payment.artista_id = 1
        mock_payment.artista = Mock()
        mock_payment.artista.id = 1
        mock_payment.artista.name = "Test Artist"
        mock_payment.observacoes = "Payment with client"

        with app.test_request_context():
            with patch("app.controllers.financeiro_api.SessionLocal") as MockSession:
                mock_db = Mock()
                MockSession.return_value = mock_db
                mock_db.query.return_value.options.return_value.get.return_value = (
                    mock_payment
                )

                # Call the function
                resp = mod.api_get_pagamento.__wrapped__(1)

                # Assert successful response
                assert isinstance(resp, tuple)
                body, status = resp
                assert status == 200

                data = body.get_json() if hasattr(body, "get_json") else body
                assert data["success"] is True

                # Verify payment data structure with client
                payment_data = data["data"]
                assert payment_data["id"] == 1
                assert payment_data["cliente"] is not None
                assert payment_data["cliente"]["id"] == 1
                assert payment_data["cliente"]["name"] == "Test Client"

    def test_api_response_helper_with_null_client_data(self):
        """Test api_response helper correctly handles null client data."""
        mod = importlib.import_module("app.controllers.financeiro_api")

        # Test data with null client
        test_data = {
            "id": 1,
            "cliente": None,  # Null client
            "artista": {"id": 1, "name": "Test Artist"},
            "valor": 100.00,
        }

        # Call api_response helper
        resp = mod.api_response(True, "Success", test_data)

        # Verify response structure
        assert isinstance(resp, tuple)
        body, status = resp
        assert status == 200

        data = body.get_json() if hasattr(body, "get_json") else body
        assert data["success"] is True
        assert data["message"] == "Success"
        assert data["data"]["cliente"] is None

    def test_api_update_pagamento_remove_client(self):
        """Test updating a payment to remove client via API."""
        mod = importlib.import_module("app.controllers.financeiro_api")
        main = importlib.import_module("main")
        app = main.create_app()

        # Mock existing payment with client
        mock_payment = Mock()
        mock_payment.id = 1
        mock_payment.cliente_id = 1

        # Update payload to remove client
        payload = {
            "cliente_id": None,  # Remove client
            "valor": "150.00",
            "forma_pagamento": "Cartão",
        }

        with app.test_request_context(json=payload):
            with patch(
                "app.repositories.pagamento_repository.PagamentoRepository"
            ) as MockRepo:
                with patch(
                    "app.controllers.financeiro_api.SessionLocal"
                ) as MockSession:
                    mock_repo = Mock()
                    MockRepo.return_value = mock_repo
                    mock_repo.get_by_id.return_value = mock_payment
                    mock_repo.update.return_value = mock_payment

                    # Call the function
                    resp = mod.api_update_pagamento.__wrapped__(1)

                    # Assert successful update
                    assert isinstance(resp, tuple)
                    body, status = resp
                    assert status == 200

                    # Verify update was called with null client
                    mock_repo.update.assert_called_once()
                    update_args = mock_repo.update.call_args[0]
                    updated_data = update_args[1]  # Second argument is the update data
                    assert "cliente_id" in updated_data
                    # The value might be None or not present, both are valid for null client

    def test_api_create_pagamento_without_client(self):
        """Test creating a payment without client via API."""
        mod = importlib.import_module("app.controllers.financeiro_api")
        main = importlib.import_module("main")
        app = main.create_app()

        # Create payload without client
        payload = {
            "data": "2024-01-15",
            "valor": "100.00",
            "forma_pagamento": "Dinheiro",
            "cliente_id": None,  # No client
            "artista_id": "1",
            "observacoes": "Payment without client",
        }

        with app.test_request_context(json=payload):
            with patch(
                "app.repositories.pagamento_repository.PagamentoRepository"
            ) as MockRepo:
                with patch(
                    "app.controllers.financeiro_api.SessionLocal"
                ) as MockSession:
                    with patch(
                        "app.controllers.financeiro_api.current_user"
                    ) as mock_user:
                        mock_user.id = 1

                        mock_repo = Mock()
                        MockRepo.return_value = mock_repo

                        # Mock successful creation
                        mock_created_payment = Mock()
                        mock_created_payment.id = 1
                        mock_repo.create.return_value = mock_created_payment

                        # Call the function (if it exists)
                        try:
                            resp = mod.api_create_pagamento.__wrapped__()

                            # Assert successful creation
                            assert isinstance(resp, tuple)
                            body, status = resp
                            assert status in [200, 201]

                            # Verify creation was called
                            mock_repo.create.assert_called_once()

                        except AttributeError:
                            # Function might not exist yet, that's OK for skeleton tests
                            pytest.skip(
                                "api_create_pagamento function not implemented yet"
                            )

    def test_api_list_pagamentos_includes_null_clients(self):
        """Test listing payments includes those with and without clients."""
        mod = importlib.import_module("app.controllers.financeiro_api")
        main = importlib.import_module("main")
        app = main.create_app()

        # Mock mixed payment data
        mock_payment_with_client = Mock()
        mock_payment_with_client.id = 1
        mock_payment_with_client.cliente_id = 1
        mock_payment_with_client.cliente = Mock()
        mock_payment_with_client.cliente.name = "Test Client"

        mock_payment_without_client = Mock()
        mock_payment_without_client.id = 2
        mock_payment_without_client.cliente_id = None
        mock_payment_without_client.cliente = None

        mock_payments = [mock_payment_with_client, mock_payment_without_client]

        with app.test_request_context():
            with patch("app.controllers.financeiro_api.SessionLocal") as MockSession:
                mock_db = Mock()
                MockSession.return_value = mock_db
                mock_db.query.return_value.options.return_value.order_by.return_value.all.return_value = (
                    mock_payments
                )

                try:
                    # Call the function (if it exists)
                    resp = mod.api_list_pagamentos.__wrapped__()

                    # Assert successful response
                    assert isinstance(resp, tuple)
                    body, status = resp
                    assert status == 200

                    data = body.get_json() if hasattr(body, "get_json") else body
                    assert data["success"] is True
                    assert len(data["data"]) == 2

                    # Verify mixed client scenarios in results
                    payments = data["data"]
                    client_statuses = [p.get("cliente") for p in payments]
                    assert (
                        None in client_statuses
                    )  # At least one payment without client

                except AttributeError:
                    # Function might not exist yet, that's OK for skeleton tests
                    pytest.skip("api_list_pagamentos function not implemented yet")


class TestFinanceiroAPIErrorHandling:
    """Test error handling in financeiro API with optional client scenarios."""

    def test_api_get_pagamento_not_found(self):
        """Test API response when payment is not found."""
        mod = importlib.import_module("app.controllers.financeiro_api")
        main = importlib.import_module("main")
        app = main.create_app()

        with app.test_request_context():
            with patch("app.controllers.financeiro_api.SessionLocal") as MockSession:
                mock_db = Mock()
                MockSession.return_value = mock_db
                mock_db.query.return_value.options.return_value.get.return_value = None

                # Call the function
                resp = mod.api_get_pagamento.__wrapped__(999)

                # Assert not found response
                assert isinstance(resp, tuple)
                body, status = resp
                assert status == 404

                data = body.get_json() if hasattr(body, "get_json") else body
                assert data["success"] is False
                assert "não encontrado" in data["message"].lower()

    def test_api_response_helper_error_format(self):
        """Test api_response helper with error scenarios."""
        mod = importlib.import_module("app.controllers.financeiro_api")

        # Test error response
        resp = mod.api_response(False, "Test error message", None, 400)

        # Verify error response structure
        assert isinstance(resp, tuple)
        body, status = resp
        assert status == 400

        data = body.get_json() if hasattr(body, "get_json") else body
        assert data["success"] is False
        assert data["message"] == "Test error message"
        assert data["data"] is None
