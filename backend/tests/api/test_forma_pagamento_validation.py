import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch


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
    def test_financeiro_update_missing_forma_pagamento_returns_400(self, client, app):
        """Test PUT /financeiro/api/<id> returns 400 when forma_pagamento is missing."""
        app.config["LOGIN_DISABLED"] = True

        payload = {}

        mock_pagamento = Mock()
        mock_pagamento.id = 1
        mock_pagamento.valor = Decimal("100.00")

        with patch(
            "app.controllers.financeiro_api.PagamentoRepository"
        ) as MockRepo, patch("flask_login.login_required", lambda f: f):
            mock_repo = Mock()
            MockRepo.return_value = mock_repo
            mock_repo.get_by_id.return_value = mock_pagamento

            resp = client.put("/financeiro/api/1", json=payload)

            assert resp.status_code == 400
            data = resp.get_json()
            assert data["success"] is False
            assert "Forma de pagamento" in data["message"]

    def test_financeiro_update_empty_forma_pagamento_returns_400(self, client, app):
        """Test PUT /financeiro/api/<id> returns 400 when forma_pagamento is empty."""
        app.config["LOGIN_DISABLED"] = True

        payload = {"forma_pagamento": ""}

        mock_pagamento = Mock()
        mock_pagamento.id = 2
        mock_pagamento.valor = Decimal("100.00")

        with patch(
            "app.controllers.financeiro_api.PagamentoRepository"
        ) as MockRepo, patch("flask_login.login_required", lambda f: f):
            mock_repo = Mock()
            MockRepo.return_value = mock_repo
            mock_repo.get_by_id.return_value = mock_pagamento

            resp = client.put("/financeiro/api/2", json=payload)

            assert resp.status_code == 400
            data = resp.get_json()
            assert data["success"] is False
            assert "Forma de pagamento" in data["message"]

    def test_financeiro_update_valid_forma_pagamento_returns_200(self, client, app):
        """Test PUT /financeiro/api/<id> returns 200 with valid forma_pagamento."""
        app.config["LOGIN_DISABLED"] = True

        payload = {"forma_pagamento": "Pix", "valor": "100.00"}

        # Create mock objects with all required attributes
        mock_cliente = Mock()
        mock_cliente.id = 1
        mock_cliente.name = "Cliente Test"

        mock_artista = Mock()
        mock_artista.id = 1
        mock_artista.name = "Artista Test"

        mock_pagamento = Mock()
        mock_pagamento.id = 10
        mock_pagamento.forma_pagamento = "Pix"
        mock_pagamento.valor = Decimal("100.00")
        mock_pagamento.data = date.today()
        mock_pagamento.observacoes = ""
        mock_pagamento.cliente = mock_cliente
        mock_pagamento.artista = mock_artista
        mock_pagamento.created_at = datetime.now()

        with patch(
            "app.controllers.financeiro_api.PagamentoRepository"
        ) as MockRepo, patch("flask_login.login_required", lambda f: f):
            mock_repo = Mock()
            MockRepo.return_value = mock_repo
            mock_repo.get_by_id.return_value = mock_pagamento
            mock_repo.update.return_value = mock_pagamento

            resp = client.put("/financeiro/api/10", json=payload)

            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True
            assert data["data"]["forma_pagamento"] == "Pix"

    def test_sessoes_update_missing_forma_pagamento_returns_400(self, client, app):
        """Test PUT /sessoes/api/<id> returns 400 when required fields are missing."""
        app.config["LOGIN_DISABLED"] = True

        payload = {}

        sessao_stub = SessaoStub(5)

        with patch(
            "app.controllers.sessoes_api.SessionLocal"
        ) as mock_session_local, patch("flask_login.login_required", lambda f: f):
            _setup_session(mock_session_local, sessao_stub)

            resp = client.put("/sessoes/api/5", json=payload)

            assert resp.status_code == 400
            data = resp.get_json()
            assert data["success"] is False
            assert "obrigatório" in data["message"].lower()

    def test_sessoes_update_empty_forma_pagamento_returns_400(self, client, app):
        """Test PUT /sessoes/api/<id> returns 400 when required fields are missing/empty."""
        app.config["LOGIN_DISABLED"] = True

        # Empty forma_pagamento and missing other required fields
        payload = {"forma_pagamento": ""}

        sessao_stub = SessaoStub(6)

        with patch(
            "app.controllers.sessoes_api.SessionLocal"
        ) as mock_session_local, patch("flask_login.login_required", lambda f: f):
            _setup_session(mock_session_local, sessao_stub)

            resp = client.put("/sessoes/api/6", json=payload)

            assert resp.status_code == 400
            data = resp.get_json()
            assert data["success"] is False

    def test_sessoes_update_valid_forma_pagamento_allows_update(self, client, app):
        """Test PUT /sessoes/api/<id> returns 200 with all required fields."""
        app.config["LOGIN_DISABLED"] = True

        payload = {
            "forma_pagamento": "Dinheiro",
            "data": "2025-08-29",
            "cliente_id": 1,
            "artista_id": 1,
            "valor": "100.00",
        }

        sessao_stub = SessaoStub(7)
        sessao_stub.observacoes = ""

        with patch(
            "app.controllers.sessoes_api.SessionLocal"
        ) as mock_session_local, patch("flask_login.login_required", lambda f: f):
            mock_db = _setup_session(mock_session_local, sessao_stub)

            resp = client.put("/sessoes/api/7", json=payload)

            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True
            # Verify the mock was updated
            assert sessao_stub.valor == Decimal("100.00")
            assert sessao_stub.cliente_id == 1
            assert sessao_stub.artista_id == 1
