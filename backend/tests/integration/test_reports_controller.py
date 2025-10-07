"""
Integration tests for reports controller endpoints.

Covers:
- /reports/extrato/comparison
- /reports/extrato/trends
- /reports/extrato/summary
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, List
from unittest.mock import MagicMock, patch

import pytest
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()

try:  # Guard imports so collection still works if module missing in certain envs
    from app.controllers.reports_controller import reports_bp

    IMPORTS_AVAILABLE = True
except ImportError as exc:  # pragma: no cover - fail gracefully during collection
    print(f"Warning: reports controller imports unavailable: {exc}")
    reports_bp = None
    IMPORTS_AVAILABLE = False


@dataclass
class StubExtrato:
    ano: int
    mes: int
    receita_total: float = 0.0
    comissoes_total: float = 0.0
    gastos_total: float = 0.0
    lucro_total: float = 0.0
    sessoes_count: int = 0
    pagamentos_count: int = 0
    created_at: datetime = datetime.now()


class QueryStub:
    def __init__(self, results: Iterable[StubExtrato]):
        self._results = list(results)

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self) -> List[StubExtrato]:
        return list(self._results)


@pytest.fixture
def admin_client(authenticated_client):
    """Authenticated client patched with admin privileges."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Reports controller not available")

    authenticated_client.mock_user.role = "admin"
    authenticated_client.mock_user.is_authenticated = True
    return authenticated_client


@pytest.fixture
def regular_client(authenticated_client):
    """Authenticated client without admin privileges."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Reports controller not available")

    authenticated_client.mock_user.role = "user"
    authenticated_client.mock_user.is_authenticated = True
    return authenticated_client


@pytest.mark.integration
@pytest.mark.controllers
@pytest.mark.reports
class TestExtratoComparison:
    def test_requires_login(self, client):
        if not IMPORTS_AVAILABLE:
            pytest.skip("Reports controller not available")

        response = client.get("/reports/extrato/comparison")

        # login_required redirects to login page when unauthenticated
        assert response.status_code in {302, 401}

    def test_requires_admin(self, regular_client):
        response = regular_client.authenticated_get("/reports/extrato/comparison")

        assert response.status_code == 403
        data = response.get_json()
        assert data["success"] is False
        assert "Acesso de administrador" in data["message"]

    def test_returns_summary_for_admin(self, admin_client):
        results = [
            StubExtrato(
                ano=2025,
                mes=7,
                receita_total=1000,
                comissoes_total=200,
                gastos_total=150,
                lucro_total=650,
                sessoes_count=12,
                pagamentos_count=9,
                created_at=datetime.now() - timedelta(days=60),
            ),
            StubExtrato(
                ano=2025,
                mes=8,
                receita_total=2000,
                comissoes_total=400,
                gastos_total=300,
                lucro_total=1300,
                sessoes_count=18,
                pagamentos_count=15,
                created_at=datetime.now() - timedelta(days=30),
            ),
        ]

        with patch("app.controllers.reports_controller.SessionLocal") as session_local:
            mock_session = MagicMock()
            mock_session.query.return_value = QueryStub(results)
            session_local.return_value = mock_session

            response = admin_client.authenticated_get("/reports/extrato/comparison")

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        comparison = payload["data"]["comparison"]
        summary = payload["data"]["summary"]

        assert len(comparison) == 2
        assert summary["total_receita"] == 3000
        assert summary["total_lucro"] == 1950
        assert summary["total_months"] == len(comparison)

    def test_include_charts_flag_adds_charts(self, admin_client):
        results = [
            StubExtrato(
                ano=2025,
                mes=8,
                receita_total=1200,
                gastos_total=400,
                lucro_total=800,
                created_at=datetime.now() - timedelta(days=20),
            ),
            StubExtrato(
                ano=2025,
                mes=9,
                receita_total=1500,
                gastos_total=500,
                lucro_total=1000,
                created_at=datetime.now() - timedelta(days=10),
            ),
        ]

        with patch("app.controllers.reports_controller.SessionLocal") as session_local:
            mock_session = MagicMock()
            mock_session.query.return_value = QueryStub(results)
            session_local.return_value = mock_session

            response = admin_client.authenticated_get(
                "/reports/extrato/comparison?include_charts=true"
            )

        assert response.status_code == 200
        data = response.get_json()["data"]
        assert "charts" in data
        assert set(data["charts"].keys()) == {"revenue_expenses", "profit_margin"}


@pytest.mark.integration
@pytest.mark.controllers
@pytest.mark.reports
class TestRevenueTrends:
    def test_requires_admin(self, regular_client):
        response = regular_client.authenticated_get("/reports/extrato/trends")

        assert response.status_code == 403

    def test_trend_calculation_returns_expected_fields(self, admin_client):
        results = [
            StubExtrato(
                ano=2025,
                mes=6,
                receita_total=1000,
                lucro_total=400,
                created_at=datetime.now() - timedelta(days=90),
            ),
            StubExtrato(
                ano=2025,
                mes=7,
                receita_total=1500,
                lucro_total=700,
                created_at=datetime.now() - timedelta(days=60),
            ),
            StubExtrato(
                ano=2025,
                mes=8,
                receita_total=1200,
                lucro_total=500,
                created_at=datetime.now() - timedelta(days=30),
            ),
        ]

        with patch("app.controllers.reports_controller.SessionLocal") as session_local:
            mock_session = MagicMock()
            mock_session.query.return_value = QueryStub(results)
            session_local.return_value = mock_session

            response = admin_client.authenticated_get(
                "/reports/extrato/trends?months=3"
            )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        trends = payload["data"]["trends"]

        assert len(trends) == 3
        assert trends[0]["trend"] == "baseline"
        assert trends[1]["trend"] == "up"
        assert trends[2]["trend"] in {"down", "stable"}
        assert "receita_change_pct" in trends[1]


@pytest.mark.integration
@pytest.mark.controllers
@pytest.mark.reports
class TestExtratoSummary:
    def test_requires_admin(self, regular_client):
        response = regular_client.authenticated_get("/reports/extrato/summary")

        assert response.status_code == 403

    def test_returns_summary_when_data_exists(self, admin_client):
        results = [
            StubExtrato(ano=2024, mes=1, receita_total=1000, lucro_total=500),
            StubExtrato(ano=2024, mes=2, receita_total=1500, lucro_total=600),
            StubExtrato(ano=2024, mes=3, receita_total=900, lucro_total=300),
        ]

        with patch("app.controllers.reports_controller.SessionLocal") as session_local:
            mock_session = MagicMock()
            mock_session.query.return_value = QueryStub(results)
            session_local.return_value = mock_session

            response = admin_client.authenticated_get(
                "/reports/extrato/summary?year=2024"
            )

        assert response.status_code == 200
        payload = response.get_json()
        summary = payload["data"]["summary"]

        assert summary["total_receita"] == 3400
        assert summary["best_month"].endswith("02")
        assert summary["worst_month"].endswith("03")
        assert summary["total_months"] == 3

    def test_returns_message_when_no_data(self, admin_client):
        with patch("app.controllers.reports_controller.SessionLocal") as session_local:
            mock_session = MagicMock()
            mock_session.query.return_value = QueryStub([])
            session_local.return_value = mock_session

            response = admin_client.authenticated_get(
                "/reports/extrato/summary?year=2030"
            )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["data"]["summary"]["total_receita"] == 0
        assert "No extrato data" in payload["data"]["message"]
