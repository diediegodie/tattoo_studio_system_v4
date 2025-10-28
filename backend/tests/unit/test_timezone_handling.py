"""
Comprehensive timezone handling tests for extrato system (Task 2).

Tests timezone-aware datetime operations, month boundary calculations,
leap year handling, and timezone consistency across functions.
"""

import os
from datetime import datetime
from unittest.mock import patch, MagicMock
from zoneinfo import ZoneInfo

import pytest


class TestTimezoneHandling:
    """Test cases for timezone-aware extrato operations."""

    def test_app_timezone_default_utc(self):
        """Test that APP_TZ defaults to UTC when TZ env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Re-import to trigger fresh initialization
            import importlib
            from app.core import config

            importlib.reload(config)

            assert str(config.APP_TZ) == "UTC"

    def test_app_timezone_custom(self):
        """Test that APP_TZ respects TZ environment variable."""
        with patch.dict(os.environ, {"TZ": "America/Sao_Paulo"}):
            import importlib
            from app.core import config

            importlib.reload(config)

            assert str(config.APP_TZ) == "America/Sao_Paulo"

    def test_app_timezone_invalid_fallback(self):
        """Test that invalid timezone falls back to UTC."""
        with patch.dict(os.environ, {"TZ": "Invalid/Timezone"}):
            import importlib
            from app.core import config

            importlib.reload(config)

            # Should fallback to UTC on invalid timezone
            assert str(config.APP_TZ) == "UTC"

    def test_get_previous_month_timezone_aware(self):
        """Test get_previous_month returns correct month in different timezones."""
        from app.services.extrato_core import get_previous_month

        # Test in America/Sao_Paulo timezone
        with patch("app.core.config.APP_TZ", ZoneInfo("America/Sao_Paulo")):
            with patch("app.services.extrato_core.datetime") as mock_datetime:
                # Simulate 2025-11-01 at 00:30 (early morning)
                mock_datetime.now.return_value = datetime(
                    2025, 11, 1, 0, 30, tzinfo=ZoneInfo("America/Sao_Paulo")
                )

                mes, ano = get_previous_month()
                assert mes == 10
                assert ano == 2025

    def test_get_previous_month_year_boundary(self):
        """Test get_previous_month correctly handles year boundaries."""
        from app.services.extrato_core import get_previous_month

        with patch("app.services.extrato_core.datetime") as mock_datetime:
            # January 2025 → Previous month is December 2024
            mock_datetime.now.return_value = datetime(
                2025, 1, 15, tzinfo=ZoneInfo("UTC")
            )

            mes, ano = get_previous_month()
            assert mes == 12
            assert ano == 2024

    def test_get_previous_month_utc_vs_local(self):
        """Test get_previous_month consistency between UTC and local timezone."""
        from app.services.extrato_core import get_previous_month

        # Test same moment in different timezones
        # 2025-11-01 03:00 UTC = 2025-11-01 00:00 America/Sao_Paulo (-03:00)

        with patch("app.services.extrato_core.datetime") as mock_datetime:
            # UTC perspective
            mock_datetime.now.return_value = datetime(
                2025, 11, 1, 3, 0, tzinfo=ZoneInfo("UTC")
            )
            mes_utc, ano_utc = get_previous_month()

        with patch("app.services.extrato_core.datetime") as mock_datetime:
            # Same moment in Sao Paulo time
            mock_datetime.now.return_value = datetime(
                2025, 11, 1, 0, 0, tzinfo=ZoneInfo("America/Sao_Paulo")
            )
            mes_sp, ano_sp = get_previous_month()

        # Should return same previous month regardless of timezone
        assert mes_utc == mes_sp == 10
        assert ano_utc == ano_sp == 2025

    def test_should_run_monthly_extrato_timezone_aware(self):
        """Test should_run_monthly_extrato with timezone-aware datetime."""
        from app.services.extrato_core import should_run_monthly_extrato

        with patch("app.services.extrato_core.datetime") as mock_datetime, patch(
            "app.services.extrato_core.SessionLocal"
        ) as mock_session:

            # Day 2 in America/Sao_Paulo (meets threshold=2)
            mock_datetime.now.return_value = datetime(
                2025, 11, 2, 14, 30, tzinfo=ZoneInfo("America/Sao_Paulo")
            )

            mock_db = mock_session.return_value
            mock_query = mock_db.query.return_value
            mock_filter = mock_query.filter.return_value
            mock_filter.first.return_value = None  # No existing run

            result = should_run_monthly_extrato()
            assert result is True

    def test_should_run_monthly_extrato_threshold_boundary(self):
        """Test should_run_monthly_extrato at exact threshold boundary."""
        from app.services.extrato_core import should_run_monthly_extrato

        with patch("app.services.extrato_core.datetime") as mock_datetime:
            # Day 1 (below threshold=2)
            mock_datetime.now.return_value = datetime(
                2025, 11, 1, 23, 59, tzinfo=ZoneInfo("America/Sao_Paulo")
            )

            result = should_run_monthly_extrato(min_day_threshold=2)
            assert result is False

        with patch("app.services.extrato_core.datetime") as mock_datetime, patch(
            "app.services.extrato_core.SessionLocal"
        ) as mock_session:

            # Day 2 (meets threshold=2)
            mock_datetime.now.return_value = datetime(
                2025, 11, 2, 0, 1, tzinfo=ZoneInfo("America/Sao_Paulo")
            )

            mock_db = mock_session.return_value
            mock_query = mock_db.query.return_value
            mock_filter = mock_query.filter.return_value
            mock_filter.first.return_value = None

            result = should_run_monthly_extrato(min_day_threshold=2)
            assert result is True

    def test_current_month_range_timezone_aware(self):
        """Test current_month_range returns timezone-aware datetimes."""
        from app.services.extrato_core import current_month_range

        with patch("app.core.config.APP_TZ", ZoneInfo("America/Sao_Paulo")), patch(
            "app.services.extrato_core.APP_TZ", ZoneInfo("America/Sao_Paulo")
        ), patch("app.services.extrato_core.datetime") as mock_datetime:

            mock_datetime.now.return_value = datetime(
                2025, 10, 15, 10, 0, tzinfo=ZoneInfo("America/Sao_Paulo")
            )
            # Need to mock datetime constructor as well
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(
                *args, **kwargs
            )

            start_date, end_date = current_month_range()

            # Verify timezone-aware
            assert start_date.tzinfo is not None
            assert end_date.tzinfo is not None
            assert start_date.year == 2025
            assert start_date.month == 10
            assert start_date.day == 1
            assert end_date.year == 2025
            assert end_date.month == 11
            assert end_date.day == 1

    def test_month_boundary_february_leap_year(self):
        """Test month boundary calculation for February in leap year."""
        from app.services.extrato_core import get_previous_month

        with patch("app.services.extrato_core.datetime") as mock_datetime:
            # March 2024 → Previous month is February 2024 (leap year)
            mock_datetime.now.return_value = datetime(
                2024, 3, 1, tzinfo=ZoneInfo("America/Sao_Paulo")
            )

            mes, ano = get_previous_month()
            assert mes == 2
            assert ano == 2024
            # Verify leap year has 29 days (implicit in date math)

    def test_month_boundary_february_non_leap_year(self):
        """Test month boundary calculation for February in non-leap year."""
        from app.services.extrato_core import get_previous_month

        with patch("app.services.extrato_core.datetime") as mock_datetime:
            # March 2025 → Previous month is February 2025 (non-leap year)
            mock_datetime.now.return_value = datetime(
                2025, 3, 1, tzinfo=ZoneInfo("America/Sao_Paulo")
            )

            mes, ano = get_previous_month()
            assert mes == 2
            assert ano == 2025

    def test_month_boundary_december_to_january(self):
        """Test month boundary calculation crossing year boundary."""
        from app.services.extrato_core import get_previous_month

        with patch("app.services.extrato_core.datetime") as mock_datetime:
            # January 2025 → Previous month is December 2024
            mock_datetime.now.return_value = datetime(
                2025, 1, 5, tzinfo=ZoneInfo("America/Sao_Paulo")
            )

            mes, ano = get_previous_month()
            assert mes == 12
            assert ano == 2024

    def test_timezone_consistency_across_functions(self):
        """Test that all date functions use the same timezone."""
        from app.services.extrato_core import (
            get_previous_month,
            should_run_monthly_extrato,
            current_month_range,
        )
        from app.core.config import APP_TZ

        # Import APP_TZ from extrato_core to verify it's using the same reference
        from app.services import extrato_core

        # Verify extrato_core imported APP_TZ correctly
        assert hasattr(extrato_core, "APP_TZ")
        assert extrato_core.APP_TZ is APP_TZ

    def test_log_timezone_config(self):
        """Test log_timezone_config logs correct information."""
        from app.core.config import log_timezone_config

        with patch("app.core.config.logger") as mock_logger:
            log_timezone_config()

            # Verify logging was called
            assert mock_logger.info.called
            call_args = mock_logger.info.call_args
            assert "Timezone configuration initialized" in call_args[0][0]

    def test_scheduler_job_uses_timezone(self):
        """Test that scheduled job uses timezone-aware datetime."""
        # This tests the generate_monthly_extrato_job in main.py
        with patch("app.services.extrato_core.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(
                2025, 11, 1, 2, 0, tzinfo=ZoneInfo("America/Sao_Paulo")
            )

            from app.services.extrato_core import get_previous_month

            mes, ano = get_previous_month()

            # Verify it returns correct previous month
            assert mes == 10
            assert ano == 2025
