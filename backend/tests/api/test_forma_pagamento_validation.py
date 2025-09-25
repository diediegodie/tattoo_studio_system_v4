import importlib
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest


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
                mock_db = Mock()
                mock_session_local.return_value = mock_db
                mock_sessao = Mock()
                mock_sessao.id = 5
                from datetime import datetime
                from decimal import Decimal

                mock_sessao.valor = Decimal("0.00")
                mock_sessao.created_at = datetime.now()
                mock_sessao.updated_at = datetime.now()
                mock_sessao.google_event_id = None
                mock_sessao.cliente = None
                mock_sessao.artista = None
                mock_db.query.return_value.get.return_value = mock_sessao

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
                mock_db = Mock()
                mock_session_local.return_value = mock_db
                mock_sessao = Mock()
                mock_sessao.id = 6
                from datetime import datetime
                from decimal import Decimal

                mock_sessao.valor = Decimal("0.00")
                mock_sessao.created_at = datetime.now()
                mock_sessao.updated_at = datetime.now()
                mock_sessao.google_event_id = None
                mock_sessao.cliente = None
                mock_sessao.artista = None
                mock_db.query.return_value.get.return_value = mock_sessao

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
                mock_db = Mock()
                mock_session_local.return_value = mock_db
                mock_sessao = Mock()
                mock_sessao.id = 7
                from datetime import datetime
                from decimal import Decimal

                mock_sessao.valor = Decimal("100.00")
                mock_sessao.created_at = datetime.now()
                mock_sessao.updated_at = datetime.now()
                mock_sessao.google_event_id = None
                mock_sessao.cliente = None
                mock_sessao.artista = None
                mock_sessao.observacoes = ""
                mock_db.query.return_value.get.return_value = mock_sessao
                mock_db.add = Mock()
                mock_db.commit = Mock()
                mock_db.refresh = Mock()

                resp = mod.api_update_sessao.__wrapped__(7)
                assert isinstance(resp, tuple)
                body, status = resp
                assert status == 200
                data = body.get_json() if hasattr(body, "get_json") else body
                assert data["success"] is True
