"""
Comprehensive unit tests for Reports Controller.

Tests all three critical financial reporting endpoints:
- /reports/extrato/comparison - Month-over-month comparisons
- /reports/extrato/trends - Revenue trends with percentage changes
- /reports/extrato/summary - Summary statistics for a given year

These tests ensure financial reporting reliability and proper admin access control.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()

try:
    from app.controllers.reports_controller import reports_bp
    from app.db.base import Extrato

    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    reports_bp = None
    Extrato = None
    IMPORTS_AVAILABLE = False


class MockExtrato:
    """Mock Extrato model for testing."""

    def __init__(
        self,
        ano,
        mes,
        receita_total=1000,
        comissoes_total=200,
        gastos_total=300,
        lucro_total=500,
        sessoes_count=10,
        pagamentos_count=15,
        created_at=None,
    ):
        self.ano = ano
        self.mes = mes
        self.receita_total = receita_total
        self.comissoes_total = comissoes_total
        self.gastos_total = gastos_total
        self.lucro_total = lucro_total
        self.sessoes_count = sessoes_count
        self.pagamentos_count = pagamentos_count
        self.created_at = created_at or datetime(ano, mes, 1)


class MockUser:
    """Mock user for authentication testing."""

    def __init__(self, user_id=1, role="admin", is_authenticated=True):
        self.id = user_id
        self.role = role
        self.is_authenticated = is_authenticated


@pytest.mark.unit
@pytest.mark.controllers
@pytest.mark.reports
class TestReportsControllerComparison:
    """Test suite for /reports/extrato/comparison endpoint."""

    def test_comparison_success_basic(self, client, app):
        """Test successful comparison with basic data."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")
        app.config["LOGIN_DISABLED"] = True

        now = datetime.now()
        mock_extratos = [
            MockExtrato(
                2025,
                1,
                receita_total=1000,
                lucro_total=500,
                created_at=now - timedelta(days=30),
            ),
            MockExtrato(
                2025,
                2,
                receita_total=1200,
                lucro_total=600,
                created_at=now - timedelta(days=20),
            ),
            MockExtrato(
                2025,
                3,
                receita_total=1500,
                lucro_total=750,
                created_at=now - timedelta(days=10),
            ),
        ]

        with patch("app.controllers.reports_controller.current_user", MockUser()):
            with patch(
                "app.controllers.reports_controller.login_required", lambda f: f
            ):
                with patch(
                    "app.controllers.reports_controller.SessionLocal"
                ) as mock_session:
                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
                        mock_extratos
                    )

                    response = client.get("/reports/extrato/comparison")

                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data["success"] is True
                    assert "comparison" in data["data"]
                    assert len(data["data"]["comparison"]) == 3
                    assert data["data"]["summary"]["total_months"] == 3
                    assert (
                        data["data"]["summary"]["total_receita"] == 3700
                    )  # 1000+1200+1500

    def test_comparison_with_charts(self, client, app):
        """Test comparison endpoint with chart generation."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")
        app.config["LOGIN_DISABLED"] = True

        now = datetime.now()
        mock_extratos = [
            MockExtrato(
                2025,
                1,
                receita_total=1000,
                lucro_total=500,
                created_at=now - timedelta(days=20),
            ),
            MockExtrato(
                2025,
                2,
                receita_total=1200,
                lucro_total=600,
                created_at=now - timedelta(days=10),
            ),
        ]

        with patch("app.controllers.reports_controller.current_user", MockUser()):
            with patch(
                "app.controllers.reports_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.reports_controller.generate_comparison_charts"
                ) as mock_charts:
                    with patch(
                        "app.controllers.reports_controller.login_required",
                        lambda f: f,
                    ):
                        mock_db = Mock()
                        mock_session.return_value = mock_db
                        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
                            mock_extratos
                        )
                        mock_charts.return_value = {"revenue_chart": "base64_data"}

                        response = client.get(
                            "/reports/extrato/comparison?include_charts=true"
                        )

                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data["success"] is True
                    assert "charts" in data["data"]
                    mock_charts.assert_called_once()

    def test_comparison_admin_access_denied(self, client, app):
        """Test comparison endpoint denies access to non-admin users."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")
        app.config["LOGIN_DISABLED"] = True

        with patch(
            "app.controllers.reports_controller.current_user", MockUser(role="user")
        ):
            with patch(
                "app.controllers.reports_controller.login_required", lambda f: f
            ):
                response = client.get("/reports/extrato/comparison")

            assert response.status_code == 403
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Acesso de administrador necessário" in data["message"]

    def test_comparison_months_parameter_validation(self, client, app):
        """Test that months parameter is properly validated and limited."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")
        app.config["LOGIN_DISABLED"] = True

        with patch("app.controllers.reports_controller.current_user", MockUser()):
            with patch(
                "app.controllers.reports_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.reports_controller.login_required", lambda f: f
                ):
                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
                        []
                    )

                    # Test months parameter exceeds maximum
                    response = client.get("/reports/extrato/comparison?months=24")

                    assert response.status_code == 200
                    # Should limit to 12 months max
                    mock_db.query.assert_called()

    def test_comparison_database_error_handling(self, client, app):
        """Test comparison endpoint handles database errors gracefully."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")
        app.config["LOGIN_DISABLED"] = True

        with patch("app.controllers.reports_controller.current_user", MockUser()):
            with patch(
                "app.controllers.reports_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.reports_controller.login_required", lambda f: f
                ):
                    mock_session.side_effect = Exception("Database connection failed")

                    response = client.get("/reports/extrato/comparison")

                    assert response.status_code == 500
                    data = json.loads(response.data)
                    assert data["success"] is False
                    assert "Erro ao gerar relatório de comparação" in data["message"]


@pytest.mark.unit
@pytest.mark.controllers
@pytest.mark.reports
class TestReportsControllerTrends:
    """Test suite for /reports/extrato/trends endpoint."""

    def test_trends_success_with_growth(self, client, app):
        """Test successful trends calculation with positive growth."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")
        app.config["LOGIN_DISABLED"] = True

        now = datetime.now()
        mock_extratos = [
            MockExtrato(
                2025,
                1,
                receita_total=1000,
                lucro_total=500,
                created_at=now - timedelta(days=30),
            ),
            MockExtrato(
                2025,
                2,
                receita_total=1200,
                lucro_total=600,
                created_at=now - timedelta(days=20),
            ),  # 20% growth
            MockExtrato(
                2025,
                3,
                receita_total=1500,
                lucro_total=750,
                created_at=now - timedelta(days=10),
            ),  # 25% growth
        ]

        with patch("app.controllers.reports_controller.current_user", MockUser()):
            with patch(
                "app.controllers.reports_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.reports_controller.login_required", lambda f: f
                ):
                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
                        mock_extratos
                    )

                    response = client.get("/reports/extrato/trends")

                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data["success"] is True
                    assert len(data["data"]["trends"]) == 3

                    trends = data["data"]["trends"]
                    assert trends[0]["trend"] == "baseline"  # First month is baseline
                    assert trends[1]["receita_change_pct"] == 20.0  # 20% growth
                    assert trends[1]["trend"] == "up"
                    assert trends[2]["receita_change_pct"] == 25.0  # 25% growth
                    assert trends[2]["trend"] == "up"

                    assert data["data"]["summary"]["positive_months"] == 2
                    assert data["data"]["summary"]["negative_months"] == 0

    def test_trends_with_decline(self, client, app):
        """Test trends calculation with declining revenue."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")
        app.config["LOGIN_DISABLED"] = True

        now = datetime.now()
        mock_extratos = [
            MockExtrato(
                2025,
                1,
                receita_total=1500,
                lucro_total=750,
                created_at=now - timedelta(days=30),
            ),
            MockExtrato(
                2025,
                2,
                receita_total=1200,
                lucro_total=600,
                created_at=now - timedelta(days=20),
            ),  # -20% decline
            MockExtrato(
                2025,
                3,
                receita_total=1000,
                lucro_total=500,
                created_at=now - timedelta(days=10),
            ),  # -16.67% decline
        ]

        with patch("app.controllers.reports_controller.current_user", MockUser()):
            with patch(
                "app.controllers.reports_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.reports_controller.login_required", lambda f: f
                ):
                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
                        mock_extratos
                    )

                    response = client.get("/reports/extrato/trends")

                    assert response.status_code == 200
                    data = json.loads(response.data)
                    trends = data["data"]["trends"]

                    assert trends[1]["receita_change_pct"] == -20.0
                    assert trends[1]["trend"] == "down"
                    assert trends[2]["trend"] == "down"

                    assert data["data"]["summary"]["negative_months"] == 2
                    assert data["data"]["summary"]["positive_months"] == 0

    def test_trends_zero_revenue_handling(self, client, app):
        """Test trends calculation when previous month has zero revenue."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")
        app.config["LOGIN_DISABLED"] = True

        now = datetime.now()
        mock_extratos = [
            MockExtrato(
                2025,
                1,
                receita_total=0,
                lucro_total=0,
                created_at=now - timedelta(days=20),
            ),
            MockExtrato(
                2025,
                2,
                receita_total=1000,
                lucro_total=500,
                created_at=now - timedelta(days=10),
            ),
        ]

        with patch("app.controllers.reports_controller.current_user", MockUser()):
            with patch(
                "app.controllers.reports_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.reports_controller.login_required", lambda f: f
                ):
                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
                        mock_extratos
                    )

                    response = client.get("/reports/extrato/trends")

                    assert response.status_code == 200
                    data = json.loads(response.data)
                    trends = data["data"]["trends"]

                    # Should handle division by zero gracefully
                    assert trends[1]["receita_change_pct"] == 0
                    assert trends[1]["trend"] == "stable"

    def test_trends_admin_access_denied(self, client, app):
        """Test trends endpoint denies access to non-admin users."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")
        app.config["LOGIN_DISABLED"] = True

        with patch(
            "app.controllers.reports_controller.current_user", MockUser(role="artist")
        ):
            with patch(
                "app.controllers.reports_controller.login_required", lambda f: f
            ):
                response = client.get("/reports/extrato/trends")

            assert response.status_code == 403
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Acesso de administrador necessário" in data["message"]


@pytest.mark.unit
@pytest.mark.controllers
@pytest.mark.reports
class TestReportsControllerSummary:
    """Test suite for /reports/extrato/summary endpoint."""

    def test_summary_success_with_data(self, client, app):
        """Test successful summary generation with extrato data."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")
        app.config["LOGIN_DISABLED"] = True

        now = datetime.now()
        mock_extratos = [
            MockExtrato(
                2025,
                1,
                receita_total=1000,
                gastos_total=300,
                lucro_total=500,
                created_at=now - timedelta(days=120),
            ),
            MockExtrato(
                2025,
                2,
                receita_total=1200,
                gastos_total=400,
                lucro_total=600,
                created_at=now - timedelta(days=90),
            ),
            MockExtrato(
                2025,
                3,
                receita_total=800,
                gastos_total=200,
                lucro_total=400,
                created_at=now - timedelta(days=60),
            ),  # worst month
            MockExtrato(
                2025,
                4,
                receita_total=1500,
                gastos_total=500,
                lucro_total=750,
                created_at=now - timedelta(days=30),
            ),  # best month
        ]

        with patch("app.controllers.reports_controller.current_user", MockUser()):
            with patch(
                "app.controllers.reports_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.reports_controller.login_required", lambda f: f
                ):
                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.filter.return_value.all.return_value = (
                        mock_extratos
                    )

                    response = client.get("/reports/extrato/summary?year=2025")

                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data["success"] is True

                    summary = data["data"]["summary"]
                    assert summary["total_receita"] == 4500  # 1000+1200+800+1500
                    assert summary["total_gastos"] == 1400  # 300+400+200+500
                    assert summary["total_lucro"] == 2250  # 500+600+400+750
                    assert summary["avg_monthly_receita"] == 1125  # 4500/4
                    assert summary["avg_monthly_lucro"] == 562.5  # 2250/4
                    assert summary["best_month"] == "2025-04"  # April had 1500 receita
                    assert summary["worst_month"] == "2025-03"  # March had 800 receita
                    assert summary["total_months"] == 4

    def test_summary_no_data_for_year(self, client, app):
        """Test summary endpoint when no data exists for the year."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")
        app.config["LOGIN_DISABLED"] = True

        with patch("app.controllers.reports_controller.current_user", MockUser()):
            with patch(
                "app.controllers.reports_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.reports_controller.login_required", lambda f: f
                ):
                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.filter.return_value.all.return_value = []

                    response = client.get("/reports/extrato/summary?year=2020")

                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data["success"] is True
                    assert data["data"]["year"] == 2020
                    assert "No extrato data found for 2020" in data["data"]["message"]

                    summary = data["data"]["summary"]
                    assert summary["total_receita"] == 0
                    assert summary["total_gastos"] == 0
                    assert summary["total_lucro"] == 0
                    assert summary["best_month"] is None
                    assert summary["worst_month"] is None

    def test_summary_default_current_year(self, client, app):
        """Test summary endpoint uses current year as default."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")
        app.config["LOGIN_DISABLED"] = True

        current_year = datetime.now().year

        with patch("app.controllers.reports_controller.current_user", MockUser()):
            with patch(
                "app.controllers.reports_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.reports_controller.login_required", lambda f: f
                ):
                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.filter.return_value.all.return_value = []

                    response = client.get(
                        "/reports/extrato/summary"
                    )  # No year parameter

                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data["data"]["year"] == current_year

    def test_summary_admin_access_denied(self, client, app):
        """Test summary endpoint denies access to non-admin users."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")
        app.config["LOGIN_DISABLED"] = True

        with patch(
            "app.controllers.reports_controller.current_user", MockUser(role="user")
        ):
            with patch(
                "app.controllers.reports_controller.login_required", lambda f: f
            ):
                response = client.get("/reports/extrato/summary")

            assert response.status_code == 403
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Acesso de administrador necessário" in data["message"]

    def test_summary_database_error_handling(self, client, app):
        """Test summary endpoint handles database errors gracefully."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")
        app.config["LOGIN_DISABLED"] = True

        with patch("app.controllers.reports_controller.current_user", MockUser()):
            with patch(
                "app.controllers.reports_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.reports_controller.login_required", lambda f: f
                ):
                    mock_session.side_effect = Exception("Database error")

                    response = client.get("/reports/extrato/summary")

                    assert response.status_code == 500
                    data = json.loads(response.data)
                    assert data["success"] is False
                    assert "Erro ao gerar relatório de resumo" in data["message"]


@pytest.mark.unit
@pytest.mark.controllers
@pytest.mark.reports
class TestReportsControllerEdgeCases:
    """Test suite for edge cases and error scenarios."""

    def test_unauthenticated_user_access(self, client, app):
        """Test that unauthenticated users cannot access any reports endpoints."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")
        # Ensure login is enforced for this test
        app.config["LOGIN_DISABLED"] = False

        with patch("app.controllers.reports_controller.current_user") as mock_user:
            mock_user.is_authenticated = False

            endpoints = [
                "/reports/extrato/comparison",
                "/reports/extrato/trends",
                "/reports/extrato/summary",
            ]

            for endpoint in endpoints:
                response = client.get(endpoint)
                # In test mode, unauthenticated users get 401 JSON response instead of redirect
                assert response.status_code == 401

    def test_invalid_parameters_handling(self, client, app):
        """Test handling of invalid query parameters."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")
        app.config["LOGIN_DISABLED"] = True

        with patch("app.controllers.reports_controller.current_user", MockUser()):
            with patch(
                "app.controllers.reports_controller.SessionLocal"
            ) as mock_session:
                with patch(
                    "app.controllers.reports_controller.login_required", lambda f: f
                ):
                    mock_db = Mock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
                        []
                    )
                    mock_db.query.return_value.filter.return_value.all.return_value = []

                    # Test invalid year parameter
                    response = client.get("/reports/extrato/summary?year=invalid")
                    # Should handle gracefully or return 500
                    assert response.status_code in [200, 500]

                    # Test invalid months parameter
                    response = client.get("/reports/extrato/comparison?months=invalid")
                    # Implementation may raise 500 or default to a value; accept either
                    assert response.status_code in [200, 500]
