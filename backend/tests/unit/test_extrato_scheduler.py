"""
Tests for APScheduler monthly extrato job.

This module tests the scheduler integration for automated monthly
extrato snapshot generation.
"""

import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


class TestExtratoScheduler:
    """Test cases for monthly extrato scheduler job."""

    def test_scheduler_registers_monthly_job(self):
        """Test that the monthly extrato job is registered in the scheduler."""
        # Set environment variable to enable job
        with patch.dict(os.environ, {"ENABLE_MONTHLY_EXTRATO_JOB": "true"}):
            from app.main import create_app

            app = create_app()
            scheduler = app.config.get("SCHEDULER")

            assert scheduler is not None, "Scheduler not initialized"

            jobs = scheduler.get_jobs()
            job_ids = [job.id for job in jobs]

            assert "monthly_extrato" in job_ids, "Monthly extrato job not registered"

    def test_scheduler_job_disabled_by_env(self):
        """Test that the job is not registered when disabled by environment."""
        with patch.dict(os.environ, {"ENABLE_MONTHLY_EXTRATO_JOB": "false"}):
            from app.main import create_app

            app = create_app()
            scheduler = app.config.get("SCHEDULER")

            assert scheduler is not None, "Scheduler not initialized"

            jobs = scheduler.get_jobs()
            job_ids = [job.id for job in jobs]

            assert (
                "monthly_extrato" not in job_ids
            ), "Monthly extrato job should not be registered when disabled"

    def test_scheduler_job_trigger_configuration(self):
        """Test that the job has correct trigger configuration."""
        with patch.dict(os.environ, {"ENABLE_MONTHLY_EXTRATO_JOB": "true"}):
            from app.main import create_app

            app = create_app()
            scheduler = app.config.get("SCHEDULER")

            assert scheduler is not None, "Scheduler not initialized"

            extrato_job = next(
                (j for j in scheduler.get_jobs() if j.id == "monthly_extrato"), None
            )

            assert extrato_job is not None, "Monthly extrato job not found"
            assert extrato_job.name == "Generate monthly extrato snapshot"

            # Check trigger configuration (CronTrigger)
            trigger = extrato_job.trigger
            assert hasattr(trigger, "fields"), "Trigger should be CronTrigger"

            # Verify it runs on day 1 at 02:00
            # Note: APScheduler CronTrigger fields are complex, so we check string representation
            trigger_str = str(trigger)
            assert "day='1'" in trigger_str, "Job should run on day 1"
            assert "hour='2'" in trigger_str, "Job should run at hour 2"

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    def test_generate_monthly_extrato_job_execution(
        self, mock_check_and_generate, monkeypatch
    ):
        """Test that the job function executes correctly."""
        # Mock get_previous_month to return a known value
        mock_get_previous_month = MagicMock(return_value=(10, 2025))
        monkeypatch.setattr(
            "app.services.extrato_core.get_previous_month", mock_get_previous_month
        )

        with patch.dict(os.environ, {"ENABLE_MONTHLY_EXTRATO_JOB": "true"}):
            from app.main import create_app

            app = create_app()

            # Get the job function (it's defined inside create_app)
            # We'll trigger it manually by getting the job and calling its func
            scheduler = app.config.get("SCHEDULER")
            assert scheduler is not None, "Scheduler not initialized"

            extrato_job = next(
                (j for j in scheduler.get_jobs() if j.id == "monthly_extrato"), None
            )

            assert extrato_job is not None, "Job not found"

            # Execute the job function
            extrato_job.func()

            # Verify that check_and_generate_extrato was called
            mock_check_and_generate.assert_called_once()

    @patch("app.services.extrato_atomic.check_and_generate_extrato_with_transaction")
    def test_generate_monthly_extrato_job_handles_exception(
        self, mock_check_and_generate, monkeypatch, caplog
    ):
        """Test that the job handles exceptions gracefully."""
        # Make the function raise an exception
        mock_check_and_generate.side_effect = Exception("Test exception")

        # Mock get_previous_month
        mock_get_previous_month = MagicMock(return_value=(10, 2025))
        monkeypatch.setattr(
            "app.services.extrato_core.get_previous_month", mock_get_previous_month
        )

        with patch.dict(os.environ, {"ENABLE_MONTHLY_EXTRATO_JOB": "true"}):
            from app.main import create_app

            app = create_app()

            scheduler = app.config.get("SCHEDULER")
            assert scheduler is not None, "Scheduler not initialized"

            extrato_job = next(
                (j for j in scheduler.get_jobs() if j.id == "monthly_extrato"), None
            )

            assert extrato_job is not None, "Job not found"

            # Execute the job - it should catch the exception
            try:
                extrato_job.func()
            except Exception:
                pytest.fail("Job should handle exceptions gracefully")

            # Verify error was logged
            assert "Error in scheduled extrato generation" in caplog.text

    def test_job_idempotency(self, monkeypatch):
        """Test that the job can be called multiple times without duplication."""
        # This tests the integration with ExtratoRunLog checking
        from app.db.base import ExtratoRunLog
        from app.db.session import SessionLocal

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()

        # First call: no existing run
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        monkeypatch.setattr("app.services.extrato_core.SessionLocal", lambda: mock_db)

        from app.services.extrato_core import should_run_monthly_extrato

        result1 = should_run_monthly_extrato(min_day_threshold=1)
        assert result1 is True

        # Second call: existing successful run
        mock_existing = MagicMock()
        mock_existing.status = "success"
        mock_filter.first.return_value = mock_existing

        result2 = should_run_monthly_extrato(min_day_threshold=1)
        assert result2 is False

    def test_structured_logging_context(self, monkeypatch, caplog):
        """Test that the job logs include structured context."""
        import logging
        from unittest.mock import MagicMock

        # Mock get_previous_month
        mock_get_previous_month = MagicMock(return_value=(10, 2025))
        monkeypatch.setattr(
            "app.services.extrato_core.get_previous_month", mock_get_previous_month
        )

        # Mock check_and_generate_extrato_with_transaction to do nothing
        with patch(
            "app.services.extrato_atomic.check_and_generate_extrato_with_transaction"
        ):
            with patch.dict(os.environ, {"ENABLE_MONTHLY_EXTRATO_JOB": "true"}):
                from app.main import create_app

                app = create_app()

                scheduler = app.config.get("SCHEDULER")
                assert scheduler is not None, "Scheduler not initialized"

                extrato_job = next(
                    (j for j in scheduler.get_jobs() if j.id == "monthly_extrato"),
                    None,
                )

                assert extrato_job is not None, "Job not found"

                # Execute job
                extrato_job.func()

                # Check that logs contain structured information
                assert "monthly_extrato" in caplog.text
                assert "target_month" in caplog.text or "10" in caplog.text
                assert "target_year" in caplog.text or "2025" in caplog.text
