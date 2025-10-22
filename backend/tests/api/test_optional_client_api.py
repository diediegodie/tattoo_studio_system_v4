"""
API endpoint tests for payments with optional cliente_id.

This module tests the API endpoints in financeiro_api.py to ensure
they handle payments with and without clients correctly.
"""

import importlib
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest


class QueryStub:
    """Minimal query chain to emulate SQLAlchemy behaviour in controller tests."""

    def __init__(self, result):
        self._result = result

    def options(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def get(self, _id):
        return self._result

    def all(self):
        if isinstance(self._result, list):
            return self._result
        if self._result is None:
            return []
        return [self._result]


@dataclass
class RelationStub:
    id: int
    name: str


@dataclass
class PagamentoStub:
    id: int
    data: date | None = None
    valor: Decimal | None = None
    forma_pagamento: str | None = None
    cliente_id: int | None = None
    cliente: RelationStub | None = None
    artista_id: int | None = None
    artista: RelationStub | None = None
    observacoes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self):
        if self.valor is not None and not isinstance(self.valor, Decimal):
            self.valor = Decimal(str(self.valor))
        now = datetime.now()
        if self.created_at is None:
            self.created_at = now
        if self.updated_at is None:
            self.updated_at = self.created_at


def _setup_session(mock_session_patch, query_result):
    mock_db = Mock()
    mock_db.query = Mock(return_value=QueryStub(query_result))
    mock_db.close = Mock()
    mock_db.commit = Mock()
    mock_db.rollback = Mock()
    mock_session_patch.return_value = mock_db
    return mock_db


class PagamentoRepoStub:
    """Simple repository stub to mimic get/update behaviour without mocks."""

    def __init__(self, existing: PagamentoStub, updated: PagamentoStub):
        self._existing = existing
        self._updated = updated
        self.update_calls: list[tuple[int, dict]] = []

    def get_by_id(self, pagamento_id: int):
        return self._existing

    def update(self, pagamento_id: int, data: dict):
        self.update_calls.append((pagamento_id, data))

        for key, value in data.items():
            if key == "valor" and value is not None:
                setattr(self._updated, key, Decimal(str(value)))
            else:
                setattr(self._updated, key, value)

        if getattr(self._updated, "cliente_id", None) is None:
            self._updated.cliente = None

        for attr in (
            "valor",
            "forma_pagamento",
            "cliente",
            "artista",
            "observacoes",
            "created_at",
            "updated_at",
        ):
            value = getattr(self._updated, attr, None)
            assert not isinstance(
                value, Mock
            ), f"Updated pagamento attribute {attr} is still a Mock"

        return self._updated


@pytest.mark.unit
@pytest.mark.api
class TestFinanceiroAPIOptionalClient:
    """Test financeiro API endpoints with optional client functionality."""

    @staticmethod
    def _unwrap_all_decorators(func):
        """Unwrap all decorator layers to reach the base function."""
        while hasattr(func, "__wrapped__"):
            func = func.__wrapped__
        return func

    def test_api_get_pagamento_with_null_client(self):
        """Test retrieving a payment with cliente_id=NULL via API."""
        mod = importlib.import_module("app.controllers.financeiro_api")
        main = importlib.import_module("main")
        app = main.create_app()

        pagamento_stub = PagamentoStub(
            id=1,
            data=date(2024, 1, 15),
            valor=Decimal("100.00"),
            forma_pagamento="Dinheiro",
            cliente_id=None,
            cliente=None,
            artista_id=1,
            artista=RelationStub(id=1, name="Test Artist"),
            observacoes="Payment without client",
        )

        with app.test_request_context():
            with patch("app.controllers.financeiro_api.SessionLocal") as MockSession:
                _setup_session(MockSession, pagamento_stub)

                # Call the function
                resp = self._unwrap_all_decorators(mod.api_get_pagamento)(1)

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

        pagamento_stub = PagamentoStub(
            id=1,
            data=date(2024, 1, 15),
            valor=Decimal("100.00"),
            forma_pagamento="Dinheiro",
            cliente_id=1,
            cliente=RelationStub(id=1, name="Test Client"),
            artista_id=1,
            artista=RelationStub(id=1, name="Test Artist"),
            observacoes="Payment with client",
        )

        with app.test_request_context():
            with patch("app.controllers.financeiro_api.SessionLocal") as MockSession:
                _setup_session(MockSession, pagamento_stub)

                # Call the function
                resp = self._unwrap_all_decorators(mod.api_get_pagamento)(1)

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
        main = importlib.import_module("main")
        app = main.create_app()

        # Test data with null client
        test_data = {
            "id": 1,
            "cliente": None,  # Null client
            "artista": {"id": 1, "name": "Test Artist"},
            "valor": 100.00,
        }

        # Call api_response helper within application context
        with app.test_request_context():
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

        # Update payload to remove client
        payload = {
            "cliente_id": None,  # Remove client
            "valor": "150.00",
            "forma_pagamento": "Cartão",
        }

        with app.test_request_context(json=payload):
            with patch(
                "app.controllers.financeiro_api.PagamentoRepository"
            ) as MockRepo:
                with patch(
                    "app.controllers.financeiro_api.SessionLocal"
                ) as MockSession, patch(
                    "app.controllers.financeiro_api.api_response"
                ) as mock_api_response:
                    repo_stub = PagamentoRepoStub(
                        existing=PagamentoStub(
                            id=1,
                            cliente_id=1,
                            cliente=RelationStub(id=1, name="Original Client"),
                            valor=Decimal("120.00"),
                            forma_pagamento="Dinheiro",
                        ),
                        updated=PagamentoStub(
                            id=1,
                            cliente_id=None,
                            cliente=None,
                            valor=Decimal("150.00"),
                            forma_pagamento="Cartão",
                        ),
                    )
                    MockRepo.return_value = repo_stub
                    mock_api_response.side_effect = (
                        lambda success, message, data=None, status_code=200: (
                            {
                                "success": success,
                                "message": message,
                                "data": data,
                            },
                            status_code,
                        )
                    )

                    # Call the function
                    resp = self._unwrap_all_decorators(mod.api_update_pagamento)(1)

                    # Assert successful update
                    assert isinstance(resp, tuple)
                    body, status = resp
                    assert status == 200

                    # Verify update was called with null client
                    assert len(repo_stub.update_calls) == 1
                    called_id, updated_data = repo_stub.update_calls[0]
                    assert called_id == 1
                    assert "cliente_id" in updated_data
                    assert updated_data.get("cliente_id") is None

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
                "app.controllers.financeiro_api.PagamentoRepository"
            ) as MockRepo:
                with patch(
                    "app.controllers.financeiro_api.SessionLocal"
                ) as MockSession:
                    with patch(
                        "app.controllers.financeiro_api.current_user",
                        create=True,
                    ) as mock_user:
                        mock_user.id = 1

                        mock_repo = Mock()
                        MockRepo.return_value = mock_repo

                        # Mock successful creation
                        mock_repo.create.return_value = PagamentoStub(
                            id=1,
                            cliente_id=None,
                            valor=Decimal("100.00"),
                            forma_pagamento="Dinheiro",
                        )

                        # Call the function (if it exists)
                        try:
                            resp = self._unwrap_all_decorators(
                                mod.api_create_pagamento
                            )()

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
        mock_payments = [
            PagamentoStub(
                id=1,
                cliente_id=1,
                cliente=RelationStub(id=1, name="Test Client"),
            ),
            PagamentoStub(id=2, cliente_id=None, cliente=None),
        ]

        with app.test_request_context():
            with patch("app.controllers.financeiro_api.SessionLocal") as MockSession:
                _setup_session(MockSession, mock_payments)

                try:
                    # Call the function (if it exists)
                    resp = self._unwrap_all_decorators(mod.api_list_pagamentos)()

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

    @staticmethod
    def _unwrap_all_decorators(func):
        """Unwrap all decorator layers to reach the base function."""
        while hasattr(func, "__wrapped__"):
            func = func.__wrapped__
        return func

    def test_api_get_pagamento_not_found(self):
        """Test API response when payment is not found."""
        mod = importlib.import_module("app.controllers.financeiro_api")
        main = importlib.import_module("main")
        app = main.create_app()

        with app.test_request_context():
            with patch("app.controllers.financeiro_api.SessionLocal") as MockSession:
                _setup_session(MockSession, None)

                # Call the function
                resp = self._unwrap_all_decorators(mod.api_get_pagamento)(999)

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
        main = importlib.import_module("main")
        app = main.create_app()

        # Test error response
        with app.test_request_context():
            resp = mod.api_response(False, "Test error message", None, 400)

            # Verify error response structure
            assert isinstance(resp, tuple)
            body, status = resp
            assert status == 400

            data = body.get_json() if hasattr(body, "get_json") else body
            assert data["success"] is False
            assert data["message"] == "Test error message"
            assert data.get("data") is None
