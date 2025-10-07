"""
Integration tests for Gastos controller endpoints.

Covers authentication flow, CRUD operations, and validation rules for:
- GET /gastos/
- POST /gastos/create
- GET/PUT/DELETE /gastos/api/<id>
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict
import uuid

import pytest
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()

try:
    from app.db.base import Gasto, User

    IMPORTS_AVAILABLE = True
except ImportError as exc:  # pragma: no cover - keep test discovery resilient
    print(f"Warning: Gastos controller dependencies unavailable: {exc}")
    Gasto = None
    User = None
    IMPORTS_AVAILABLE = False


@pytest.fixture
def gasto_payload() -> Dict[str, str]:
    return {
        "data": "2025-09-30",
        "valor": "199.90",
        "descricao": "Compra de materiais",
        "forma_pagamento": "Pix",
    }


@pytest.fixture
def admin_authenticated_client(authenticated_client):
    """Ensure authenticated client user exists in database and is linked to User model."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Gastos controller not available")

    authenticated_client.mock_user.role = "user"
    authenticated_client.mock_user.is_authenticated = True
    return authenticated_client


@pytest.mark.integration
@pytest.mark.controllers
@pytest.mark.gastos
class TestGastosAuthentication:
    def test_get_home_requires_login(self, client):
        if not IMPORTS_AVAILABLE:
            pytest.skip("Gastos controller not available")

        response = client.get("/gastos/")
        assert response.status_code in {302, 401}

    def test_api_endpoints_require_login(self, client):
        if not IMPORTS_AVAILABLE:
            pytest.skip("Gastos controller not available")

        assert client.get("/gastos/api/1").status_code in {302, 401}
        assert client.put("/gastos/api/1", json={}).status_code in {302, 401}
        assert client.delete("/gastos/api/1").status_code in {302, 401}


@pytest.mark.integration
@pytest.mark.controllers
@pytest.mark.gastos
class TestGastosCreate:
    def test_create_gasto_json_success(
        self, admin_authenticated_client, db_session, gasto_payload
    ):
        payload = dict(gasto_payload)

        response = admin_authenticated_client.authenticated_post(
            "/gastos/create", json=payload
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["gasto"]["descricao"] == payload["descricao"]

        created = (
            db_session.query(Gasto)
            .filter_by(
                descricao=payload["descricao"],
                created_by=admin_authenticated_client.user.id,
            )
            .one()
        )
        assert created.valor == Decimal(payload["valor"])
        assert created.forma_pagamento == payload["forma_pagamento"]

    def test_create_gasto_form_success(
        self, admin_authenticated_client, db_session, gasto_payload
    ):
        payload = dict(gasto_payload)
        response = admin_authenticated_client.authenticated_post(
            "/gastos/create", data=payload
        )

        assert response.status_code == 302
        assert "/gastos/" in response.location

    @pytest.mark.parametrize(
        "override,message",
        [
            ({"descricao": ""}, "Descrição é obrigatória"),
            ({"valor": "-10"}, "Valor deve ser maior que zero"),
            ({"data": "2025/09/30"}, "Data inválida"),
        ],
    )
    def test_create_gasto_validation_errors(
        self,
        admin_authenticated_client,
        db_session,
        gasto_payload,
        override,
        message,
    ):
        payload = {**gasto_payload, **override}
        response = admin_authenticated_client.authenticated_post(
            "/gastos/create", json=payload
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert message.split()[0] in data["message"]


@pytest.mark.integration
@pytest.mark.controllers
@pytest.mark.gastos
class TestGastosAPI:
    def _create_gasto(self, db_session, user_id, **kwargs) -> Gasto:
        gasto = Gasto(
            data=kwargs.get("data", date(2025, 9, 1)),
            valor=Decimal(kwargs.get("valor", "120.50")),
            descricao=kwargs.get("descricao", "Despesa de teste"),
            forma_pagamento=kwargs.get("forma_pagamento", "Cartão"),
            created_by=user_id,
        )
        db_session.add(gasto)
        db_session.commit()
        db_session.refresh(gasto)
        return gasto

    def test_get_gasto_success(
        self, admin_authenticated_client, db_session, gasto_payload
    ):
        gasto = self._create_gasto(db_session, admin_authenticated_client.user.id)

        response = admin_authenticated_client.authenticated_get(
            f"/gastos/api/{gasto.id}"
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["id"] == gasto.id
        assert data["data"]["descricao"] == gasto.descricao

    def test_get_gasto_not_found(self, admin_authenticated_client):
        response = admin_authenticated_client.authenticated_get("/gastos/api/99999")
        assert response.status_code == 404

    def test_get_gasto_forbidden_for_other_user(
        self, admin_authenticated_client, db_session
    ):
        other_user = User(
            name="Outro",
            email=f"outro-{uuid.uuid4()}@example.com",
            google_id=f"other-{uuid.uuid4()}",
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        gasto = self._create_gasto(
            db_session, other_user.id, descricao="Despesa secreta"
        )

        response = admin_authenticated_client.authenticated_get(
            f"/gastos/api/{gasto.id}"
        )

        assert response.status_code == 403

    def test_update_gasto_success(self, admin_authenticated_client, db_session):
        gasto = self._create_gasto(db_session, admin_authenticated_client.user.id)
        update_payload = {
            "descricao": "Despesa atualizada",
            "valor": "210.80",
            "forma_pagamento": "Dinheiro",
        }

        response = admin_authenticated_client.authenticated_put(
            f"/gastos/api/{gasto.id}", json=update_payload
        )

        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["descricao"] == "Despesa atualizada"
        assert data["valor"] == float(update_payload["valor"])

    def test_update_gasto_validation_error(
        self, admin_authenticated_client, db_session
    ):
        gasto = self._create_gasto(db_session, admin_authenticated_client.user.id)

        response = admin_authenticated_client.authenticated_put(
            f"/gastos/api/{gasto.id}", json={"valor": "-1"}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Valor deve ser maior" in data["message"]

    def test_update_gasto_forbidden(self, admin_authenticated_client, db_session):
        other_user = User(
            name="Outro",
            email=f"outro-{uuid.uuid4()}@example.com",
            google_id=f"other-{uuid.uuid4()}",
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        gasto = self._create_gasto(db_session, other_user.id)

        response = admin_authenticated_client.authenticated_put(
            f"/gastos/api/{gasto.id}", json={"descricao": "Tentativa"}
        )

        assert response.status_code == 403

    def test_delete_gasto_success(self, admin_authenticated_client, db_session):
        gasto = self._create_gasto(db_session, admin_authenticated_client.user.id)

        response = admin_authenticated_client.authenticated_delete(
            f"/gastos/api/{gasto.id}"
        )

        assert response.status_code == 200
        db_session.expunge_all()
        assert db_session.query(Gasto).filter_by(id=gasto.id).count() == 0

    def test_delete_gasto_forbidden(self, admin_authenticated_client, db_session):
        other_user = User(
            name="Outro",
            email=f"outro-{uuid.uuid4()}@example.com",
            google_id=f"other-{uuid.uuid4()}",
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        gasto = self._create_gasto(db_session, other_user.id)

        response = admin_authenticated_client.authenticated_delete(
            f"/gastos/api/{gasto.id}"
        )

        assert response.status_code == 403

    def test_delete_gasto_not_found(self, admin_authenticated_client):
        response = admin_authenticated_client.authenticated_delete("/gastos/api/43210")
        assert response.status_code == 404
