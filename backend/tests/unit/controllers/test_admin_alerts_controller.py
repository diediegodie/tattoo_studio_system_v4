import pytest


@pytest.mark.unit
@pytest.mark.controllers
class TestAdminAlertsController:
    def test_admin_alerts_dashboard_renders_summary(
        self, authenticated_client, monkeypatch
    ):
        authenticated_client.mock_user.role = "admin"
        sample_alerts = [
            {
                "timestamp": "2025-10-07T12:00:00Z",
                "message": "Slow query detected",
                "alert_type": "slow_query",
                "severity": "critical",
                "details": {"request": {"route": "/api/v1/test"}},
            },
            {
                "timestamp": "2025-10-07T12:05:00Z",
                "message": "Slow query warning",
                "alert_type": "slow_query",
                "severity": "warning",
                "details": {"request": {"route": "/api/v1/test"}},
            },
            {
                "timestamp": "2025-10-07T12:06:00Z",
                "message": "Background job delay",
                "alert_type": "job_latency",
                "severity": "warning",
                "details": {"request": {"route": None}},
            },
        ]

        monkeypatch.setattr(
            "app.controllers.admin_alerts_controller.get_recent_alerts",
            lambda limit=50: sample_alerts,
        )

        response = authenticated_client.authenticated_get("/admin/alerts")

        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Total de alertas: 3" in html
        assert html.count("alert-summary-badge--warning") == 1
        assert "alert-summary-badge--critical" in html
        assert 'class="alert-summary-count">2<' in html
        assert html.count("alert-summary-count") == 2
        assert "Slow query detected" in html
        assert "Background job delay" in html

    def test_admin_alerts_dashboard_requires_admin(
        self, authenticated_client, monkeypatch
    ):
        authenticated_client.mock_user.role = "user"

        # Ensure service is not called when access is forbidden
        called = {"value": False}

        def fake_get_recent_alerts(limit=50):
            called["value"] = True
            return []

        monkeypatch.setattr(
            "app.controllers.admin_alerts_controller.get_recent_alerts",
            fake_get_recent_alerts,
        )

        response = authenticated_client.authenticated_get("/admin/alerts")

        assert response.status_code == 403
        assert called["value"] is False
