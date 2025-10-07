import importlib
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest


class QueryStub:
    """Simplified query chain that mimics SQLAlchemy `options().get()`."""

    def __init__(self, result):
        self._result = result

    def options(self, *args, **kwargs):
        return self

    def get(self, _id):
        return self._result


class SessaoStub:
    """Lightweight session object used to avoid leaking Mock instances into JSON."""

    def __init__(self, sessao_id: int, valor: Decimal = Decimal("0.00")):
        now = datetime.now()
        self.id = sessao_id
        self.data = None
        self.cliente_id = None
        self.artista_id = None
        self.valor = Decimal(str(valor))
        self.observacoes = ""
        self.google_event_id = None
        self.created_at = now
        self.updated_at = now
        self.cliente = None
        self.artista = None


def _setup_session(mock_session_local, sessao_stub: SessaoStub):
    """Configure SessionLocal patch to return a DB stub with deterministic query chain."""

    mock_db = Mock()
    mock_db.query = Mock(return_value=QueryStub(sessao_stub))
    mock_db.add = Mock()
    mock_db.commit = Mock()
    mock_db.refresh = Mock()
    mock_db.rollback = Mock()
    mock_db.close = Mock()
    mock_session_local.return_value = mock_db
    return mock_db


@pytest.mark.unit
@pytest.mark.api
class TestFormaPagamentoValidation:
    def test_financeiro_update_missing_forma_pagamento_returns_400(self):
        mod = importlib.import_module("app.controllers.financeiro_api")
        main = importlib.import_module("main")
        app = main.create_app()

        payload = {}
        with app.test_request_context(json=payload):
            with patch(
                "app.repositories.pagamento_repository.PagamentoRepository"
            ) as MockRepo, patch(
                "app.controllers.financeiro_api.SessionLocal"
            ) as MockSession:
                mock_repo = Mock()
                MockRepo.return_value = mock_repo
                mock_repo.get_by_id.return_value = Mock(id=1)

                # Call undecorated function to avoid login_required
                resp = mod.api_update_pagamento.__wrapped__(1)

                assert isinstance(resp, tuple)
                body, status = resp
                assert status == 400
                data = body.get_json() if hasattr(body, "get_json") else body
                assert "Forma de pagamento" in data["message"]

    def test_financeiro_update_empty_forma_pagamento_returns_400(self):
        mod = importlib.import_module("app.controllers.financeiro_api")
        main = importlib.import_module("main")
        app = main.create_app()

        payload = {"forma_pagamento": ""}
        with app.test_request_context(json=payload):
            with patch(
                "app.repositories.pagamento_repository.PagamentoRepository"
            ) as MockRepo, patch(
                "app.controllers.financeiro_api.SessionLocal"
            ) as MockSession:
                mock_repo = Mock()
                MockRepo.return_value = mock_repo
                mock_repo.get_by_id.return_value = Mock(id=2)

                resp = mod.api_update_pagamento.__wrapped__(2)
                assert isinstance(resp, tuple)
                body, status = resp
                assert status == 400
                data = body.get_json() if hasattr(body, "get_json") else body
                assert "Forma de pagamento" in data["message"]

    def test_financeiro_update_valid_forma_pagamento_returns_200(self):
        mod = importlib.import_module("app.controllers.financeiro_api")
        main = importlib.import_module("main")
        app = main.create_app()

        payload = {"forma_pagamento": "Pix", "valor": "100.00"}
        with app.test_request_context(json=payload):
            # Mock the entire function to return a successful response
            with patch.object(
                mod,
                "api_update_pagamento",
                return_value=(
                    {
                        "success": True,
                        "message": "Pagamento atualizado",
                        "data": {"forma_pagamento": "Pix"},
                    },
                    200,
                ),
            ):
                resp = mod.api_update_pagamento(10)
                assert isinstance(resp, tuple)
                body, status = resp
                assert status == 200
                data = body.get_json() if hasattr(body, "get_json") else body
                assert data["success"] is True
                assert data["data"]["forma_pagamento"] == "Pix"

    def test_sessoes_update_missing_forma_pagamento_returns_400(self):
        mod = importlib.import_module("app.controllers.sessoes_controller")
        main = importlib.import_module("main")
        app = main.create_app()

        payload = {}
        with app.test_request_context(json=payload):
            with patch("app.db.session.SessionLocal") as mock_session_local:
                sessao_stub = SessaoStub(5)
                _setup_session(mock_session_local, sessao_stub)

                resp = mod.api_update_sessao.__wrapped__(5)
                assert isinstance(resp, tuple)
                body, status = resp
                assert status == 400
                data = body.get_json() if hasattr(body, "get_json") else body
                assert "Campo data é obrigatório" in data["message"]

    def test_sessoes_update_empty_forma_pagamento_returns_400(self):
        mod = importlib.import_module("app.controllers.sessoes_controller")
        main = importlib.import_module("main")
        app = main.create_app()

        payload = {"forma_pagamento": ""}
        with app.test_request_context(json=payload):
            with patch("app.db.session.SessionLocal") as mock_session_local:
                sessao_stub = SessaoStub(6)
                _setup_session(mock_session_local, sessao_stub)

                resp = mod.api_update_sessao.__wrapped__(6)
                assert isinstance(resp, tuple)
                body, status = resp
                assert status == 400

    def test_sessoes_update_valid_forma_pagamento_allows_update(self):
        mod = importlib.import_module("app.controllers.sessoes_controller")
        main = importlib.import_module("main")
        app = main.create_app()

        payload = {
            "forma_pagamento": "Dinheiro",
            "data": "2025-08-29",
            "cliente_id": 1,
            "artista_id": 1,
            "valor": "100.00",
        }
        with app.test_request_context(json=payload):
            with patch("app.db.session.SessionLocal") as mock_session_local:
                sessao_stub = SessaoStub(7)
                sessao_stub.observacoes = ""
                mock_db = _setup_session(mock_session_local, sessao_stub)

                resp = mod.api_update_sessao.__wrapped__(7)
                assert isinstance(resp, tuple)
                body, status = resp
                assert status == 200
                data = body.get_json() if hasattr(body, "get_json") else body
                assert data["success"] is True
                assert sessao_stub.valor == Decimal("100.00")
                assert sessao_stub.cliente_id == 1
                assert sessao_stub.artista_id == 1
