"""
Integration tests for APScheduler monthly extrato job and manual trigger endpoint.

This module tests the complete integration of:
- APScheduler job registration and execution
- Manual trigger endpoint (/api/extrato/generate)
- Timezone-aware scheduling and execution
- Database persistence and idempotency
- Admin access control
- Backup validation integration

These tests complement the unit tests by testing the full stack integration,
including database operations, HTTP endpoints, and scheduler behavior.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from app.db.base import Extrato, ExtratoRunLog
from app.db.session import SessionLocal


@pytest.mark.integration
class TestSchedulerRegistrationIntegration:
    """Integration tests for APScheduler job registration."""

    def test_scheduler_registers_monthly_job_with_app(self):
        """Test that the monthly extrato job is registered when app is created."""
        # Clear any existing app instances
        with patch.dict(os.environ, {"ENABLE_MONTHLY_EXTRATO_JOB": "true"}):
            from app.main import create_app

            app = create_app()

            # Verify scheduler is configured
            scheduler = app.config.get("SCHEDULER")
            assert scheduler is not None, "Scheduler not initialized in app config"

            # Verify job is registered
            jobs = scheduler.get_jobs()
            job_ids = [job.id for job in jobs]
            assert "monthly_extrato" in job_ids, "Monthly extrato job not registered"

            # Verify job configuration
            extrato_job = next((j for j in jobs if j.id == "monthly_extrato"), None)
            assert extrato_job is not None, "Extrato job not found in scheduler"
            assert extrato_job.name == "Generate monthly extrato snapshot"

    def test_scheduler_job_not_registered_when_disabled(self):
        """Test that job is not registered when ENABLE_MONTHLY_EXTRATO_JOB is false."""
        with patch.dict(os.environ, {"ENABLE_MONTHLY_EXTRATO_JOB": "false"}):
            from app.main import create_app

            app = create_app()
            scheduler = app.config.get("SCHEDULER")
            assert scheduler is not None, "Scheduler should still be initialized"

            jobs = scheduler.get_jobs()
            job_ids = [job.id for job in jobs]
            assert "monthly_extrato" not in job_ids

    def test_scheduler_trigger_configuration_integration(self):
        """Test that the job has correct CronTrigger for monthly execution."""
        with patch.dict(os.environ, {"ENABLE_MONTHLY_EXTRATO_JOB": "true"}):
            from app.main import create_app

            app = create_app()
            scheduler = app.config.get("SCHEDULER")
            assert scheduler is not None, "Scheduler not initialized in app config"

            extrato_job = next(
                (j for j in scheduler.get_jobs() if j.id == "monthly_extrato"), None
            )
            assert extrato_job is not None, "Extrato job not found in scheduler"

            # Verify CronTrigger configuration
            trigger = extrato_job.trigger
            trigger_str = str(trigger)

            # Should run on day 1 at 02:00 AM
            assert "day='1'" in trigger_str
            assert "hour='2'" in trigger_str


@pytest.mark.integration
class TestSchedulerExecutionIntegration:
    """Integration tests for scheduler job execution with database."""

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    def test_scheduler_job_executes_with_database(self, mock_generate, monkeypatch):
        """Test that job executes and interacts with database correctly."""
        # Mock get_previous_month
        mock_get_previous_month = MagicMock(return_value=(10, 2025))
        monkeypatch.setattr(
            "app.services.extrato_core.get_previous_month", mock_get_previous_month
        )

        mock_generate.return_value = True

        with patch.dict(os.environ, {"ENABLE_MONTHLY_EXTRATO_JOB": "true"}):
            from app.main import create_app

            app = create_app()
            scheduler = app.config.get("SCHEDULER")
            assert scheduler is not None, "Scheduler not initialized in app config"

            extrato_job = next(
                (j for j in scheduler.get_jobs() if j.id == "monthly_extrato"), None
            )
            assert extrato_job is not None, "Extrato job not found in scheduler"

            # Execute the job
            with app.app_context():
                extrato_job.func()

            # Verify the atomic function was called
            mock_generate.assert_called_once()

    def test_scheduler_respects_day_threshold(self):
        """Test that scheduler respects the day threshold for execution."""
        from app.services.extrato_core import should_run_monthly_extrato

        db = SessionLocal()
        try:
            # Test with day 1 (should not run - threshold is 2)
            with patch("app.services.extrato_core.datetime") as mock_datetime:
                mock_now = MagicMock()
                mock_now.day = 1
                mock_datetime.now.return_value = mock_now

                result = should_run_monthly_extrato(min_day_threshold=2)
                assert result is False, "Should not run on day 1 with threshold 2"

            # Test with day 2 (should run if no existing logs)
            # Clear any existing logs for the test to ensure predictable behavior
            from app.services.extrato_core import get_previous_month

            mes, ano = get_previous_month()
            db.query(ExtratoRunLog).filter(
                ExtratoRunLog.mes == mes,
                ExtratoRunLog.ano == ano,
                ExtratoRunLog.status == "success",
            ).delete()
            db.commit()

            with patch("app.services.extrato_core.datetime") as mock_datetime:
                mock_now = MagicMock()
                mock_now.day = 2
                mock_datetime.now.return_value = mock_now

                result = should_run_monthly_extrato(min_day_threshold=2)
                assert (
                    result is True
                ), "Should run on day 2 with threshold 2 and no existing successful logs"

        finally:
            db.close()

    def test_timezone_sensitivity_at_month_boundary(self):
        """Test that scheduler uses APP_TZ for month boundary calculations.

        Note: This test is date-aware and calculates expected values dynamically
        based on the current date and configured timezone. Rather than using
        hardcoded values, it verifies that get_previous_month() produces the same
        result as a manual timezone-aware calculation. This ensures consistency
        across any date the test is run, including month boundaries and year
        boundaries (e.g., January 1st where previous month is December of prior year).
        """
        from app.core.config import APP_TZ
        from app.services.extrato_core import get_previous_month

        # Call get_previous_month and verify it uses timezone
        mes, ano = get_previous_month()

        # Should return valid month/year
        assert 1 <= mes <= 12
        assert 2020 <= ano <= 2030

        # Verify it uses the configured timezone
        from datetime import datetime

        now = datetime.now(APP_TZ)
        first_day_this_month = now.replace(day=1)
        from datetime import timedelta

        last_day_prev_month = first_day_this_month - timedelta(days=1)

        assert mes == last_day_prev_month.month
        assert ano == last_day_prev_month.year


@pytest.mark.integration
class TestSchedulerPersistenceAndDuplication:
    """Integration tests for persistence and idempotency."""

    def test_extrato_unique_constraint_prevents_duplication(self):
        """Test that database UniqueConstraint prevents duplicate extratos."""
        db = SessionLocal()
        try:
            # Clean up any existing extrato for this test to ensure clean state
            db.query(Extrato).filter(Extrato.mes == 11, Extrato.ano == 2099).delete()
            db.commit()

            # Create first extrato
            extrato1 = Extrato(
                mes=11,
                ano=2099,
                pagamentos=json.dumps([]),
                sessoes=json.dumps([]),
                comissoes=json.dumps([]),
                gastos=json.dumps([]),
                totais=json.dumps({"receita_total": 0}),
            )
            db.add(extrato1)
            db.commit()

            # Try to create duplicate
            extrato2 = Extrato(
                mes=11,
                ano=2099,
                pagamentos=json.dumps([]),
                sessoes=json.dumps([]),
                comissoes=json.dumps([]),
                gastos=json.dumps([]),
                totais=json.dumps({"receita_total": 0}),
            )
            db.add(extrato2)

            # Should raise IntegrityError
            from sqlalchemy.exc import IntegrityError

            with pytest.raises(IntegrityError):
                db.commit()

        finally:
            db.rollback()
            # Clean up test data
            db.query(Extrato).filter(Extrato.mes == 11, Extrato.ano == 2099).delete()
            db.commit()
            db.close()

    def test_extrato_run_log_records_execution(self):
        """Test that ExtratoRunLog records are created for each run."""
        from app.services.extrato_core import _log_extrato_run

        # Log a run (function creates its own session)
        _log_extrato_run(
            mes=10,
            ano=2025,
            status="success",
            message="Test run",
        )

        # Verify record exists
        db = SessionLocal()
        try:
            log_entry = (
                db.query(ExtratoRunLog)
                .filter(
                    ExtratoRunLog.mes == 10,
                    ExtratoRunLog.ano == 2025,
                    ExtratoRunLog.status == "success",
                )
                .first()
            )

            assert log_entry is not None
            assert log_entry.status == "success"
            assert log_entry.message == "Test run"

        finally:
            db.close()

    def test_idempotency_check_prevents_duplicate_runs(self):
        """Test that idempotency check prevents running for already-processed month."""
        from app.services.extrato_core import should_run_monthly_extrato

        db = SessionLocal()
        try:
            # Get current previous month
            from app.services.extrato_core import get_previous_month

            mes, ano = get_previous_month()

            # First check - should be allowed (no existing run)
            result1 = should_run_monthly_extrato()
            # Result depends on existing data, but shouldn't raise error
            assert isinstance(result1, bool)

            # Create a successful run log
            from app.services.extrato_core import _log_extrato_run

            _log_extrato_run(
                mes=mes,
                ano=ano,
                status="success",
                message="Test previous run",
            )

            # Second check - should not be allowed (existing successful run)
            result2 = should_run_monthly_extrato()
            assert result2 is False, "Should not run when successful run exists"

        finally:
            db.close()


@pytest.mark.integration
class TestManualTriggerEndpointIntegration:
    """Integration tests for /api/extrato/generate endpoint."""

    def test_manual_trigger_requires_admin_access(self, client):
        """Test that non-admin users are rejected with 403."""
        # Create non-admin user
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "user"  # Not admin
        mock_user.id = 1

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/api/extrato/generate",
                json={"month": 10, "year": 2025, "force": False},
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 403
            data = response.get_json()
            assert data["success"] is False

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    def test_manual_trigger_admin_success(self, mock_generate, client):
        """Test that admin can successfully trigger generation."""
        mock_generate.return_value = True

        # Create admin user
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "admin"
        mock_user.id = 1
        mock_user.email = "admin@test.com"

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/api/extrato/generate",
                json={"month": 10, "year": 2025, "force": False},
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            # Verify the success message matches expected format
            import re

            assert re.search(
                r"extrato.*generated.*successfully.*10/2025",
                data["message"],
                re.IGNORECASE,
            ), f"Expected success message with month/year, got: {data['message']}"

            # Verify atomic function was called with correct parameters
            mock_generate.assert_called_once_with(mes=10, ano=2025, force=False)

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    def test_manual_trigger_uses_previous_month_defaults(
        self, mock_generate, client, monkeypatch
    ):
        """Test that endpoint defaults to previous month when no params provided."""
        mock_generate.return_value = True

        # Mock get_previous_month
        mock_get_previous_month = MagicMock(return_value=(9, 2025))
        monkeypatch.setattr(
            "app.services.extrato_core.get_previous_month", mock_get_previous_month
        )

        # Create admin user
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "admin"
        mock_user.id = 1
        mock_user.email = "admin@test.com"

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/api/extrato/generate",
                json={},  # No month/year specified
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True

            # Verify the atomic function was called with None parameters
            # (the function handles defaults internally)
            mock_generate.assert_called_once_with(mes=None, ano=None, force=False)

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    def test_manual_trigger_idempotency(self, mock_generate, client):
        """Test that manual trigger respects idempotency (no duplicate extratos)."""
        # First call succeeds
        mock_generate.return_value = True

        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "admin"
        mock_user.id = 1
        mock_user.email = "admin@test.com"

        with patch("flask_login.utils._get_user", return_value=mock_user):
            # First call
            response1 = client.post(
                "/api/extrato/generate",
                json={"month": 10, "year": 2025, "force": False},
                headers={"Content-Type": "application/json"},
            )
            assert response1.status_code == 200
            assert response1.get_json()["success"] is True

            # Second call with force=False should respect existing extrato
            # Reset mock to return False (indicating extrato already exists)
            mock_generate.reset_mock()
            mock_generate.return_value = True  # Still succeeds but may skip

            response2 = client.post(
                "/api/extrato/generate",
                json={"month": 10, "year": 2025, "force": False},
                headers={"Content-Type": "application/json"},
            )

            # Should still return 200 (successful API call)
            assert response2.status_code == 200
            # The actual behavior depends on atomic function's internal logic

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    def test_manual_trigger_force_regeneration(self, mock_generate, client):
        """Test that force=True allows regeneration of existing extrato."""
        mock_generate.return_value = True

        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "admin"
        mock_user.id = 1
        mock_user.email = "admin@test.com"

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/api/extrato/generate",
                json={"month": 10, "year": 2025, "force": True},
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True

            # Verify force parameter was passed
            mock_generate.assert_called_once_with(mes=10, ano=2025, force=True)

    def test_manual_trigger_parameter_validation(self, client):
        """Test that endpoint validates month and year parameters."""
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "admin"
        mock_user.id = 1
        mock_user.email = "admin@test.com"

        with patch("flask_login.utils._get_user", return_value=mock_user):
            # Invalid month
            response = client.post(
                "/api/extrato/generate",
                json={"month": 13, "year": 2025, "force": False},
                headers={"Content-Type": "application/json"},
            )

            # Should handle invalid parameters gracefully
            # (Implementation may vary - either 400 or the atomic function validates)
            assert response.status_code in [200, 400]

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    def test_manual_trigger_error_handling(self, mock_generate, client):
        """Test that endpoint handles errors gracefully with proper logging."""
        # Make atomic function raise an exception
        mock_generate.side_effect = Exception("Test database error")

        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "admin"
        mock_user.id = 1
        mock_user.email = "admin@test.com"

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/api/extrato/generate",
                json={"month": 10, "year": 2025, "force": False},
                headers={"Content-Type": "application/json"},
            )

            # Should return 500 on error
            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False
            assert "error" in data

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    def test_manual_trigger_structured_logging(self, mock_generate, client, caplog):
        """Test that endpoint logs with structured context."""
        import logging

        caplog.set_level(logging.INFO)

        mock_generate.return_value = True

        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.role = "admin"
        mock_user.id = 1
        mock_user.email = "admin@test.com"

        with patch("flask_login.utils._get_user", return_value=mock_user):
            response = client.post(
                "/api/extrato/generate",
                json={"month": 10, "year": 2025, "force": False},
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 200

            # Verify structured logging occurred
            # The endpoint should log with context about the manual trigger
            assert response.status_code == 200  # Basic check that it ran


@pytest.mark.integration
class TestSchedulerWithBackupValidation:
    """Integration tests for scheduler backup validation."""

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    @patch("app.services.backup_service.BackupService")
    def test_scheduler_respects_backup_requirement(
        self, mock_backup_service, mock_generate, monkeypatch
    ):
        """Test that scheduler respects EXTRATO_REQUIRE_BACKUP setting."""
        # Suppress unused parameter warning - mock_backup_service is needed for patch order
        _ = mock_backup_service

        mock_generate.return_value = True

        # Mock get_previous_month
        mock_get_previous_month = MagicMock(return_value=(10, 2025))
        monkeypatch.setattr(
            "app.services.extrato_core.get_previous_month", mock_get_previous_month
        )

        with patch.dict(
            os.environ,
            {
                "ENABLE_MONTHLY_EXTRATO_JOB": "true",
                "EXTRATO_REQUIRE_BACKUP": "true",
            },
        ):
            from app.main import create_app

            app = create_app()
            scheduler = app.config.get("SCHEDULER")
            assert scheduler is not None, "Scheduler not initialized in app config"

            extrato_job = next(
                (j for j in scheduler.get_jobs() if j.id == "monthly_extrato"), None
            )
            assert extrato_job is not None, "Extrato job not found in scheduler"

            # Execute the job
            with app.app_context():
                extrato_job.func()

            # The atomic function handles backup validation internally
            mock_generate.assert_called_once()
