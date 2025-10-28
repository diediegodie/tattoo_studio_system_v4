"""
Test for extrato service functionality.
"""

from datetime import datetime
from unittest.mock import patch

import pytest
from app.services.extrato_automation import should_run_monthly_extrato
from app.services.extrato_core import get_previous_month


class TestExtratoService:
    """Test cases for extrato service functionality."""

    def test_get_previous_month_current_date(self):
        """Test get_previous_month with current date logic."""
        with patch("app.services.extrato_core.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 9, 15)
            mes, ano = get_previous_month()
            assert mes == 8
            assert ano == 2024

    def test_get_previous_month_january(self):
        """Test get_previous_month when current month is January."""
        with patch("app.services.extrato_core.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 15)
            mes, ano = get_previous_month()
            assert mes == 12
            assert ano == 2023

    def test_should_run_monthly_extrato_on_first(self):
        """Test should_run_monthly_extrato returns True on the 1st of the month if not already run."""
        with patch("app.services.extrato_automation.datetime") as mock_datetime, patch(
            "app.services.extrato_automation.SessionLocal"
        ) as mock_session:
            mock_datetime.now.return_value = datetime(2024, 9, 1)
            mock_db = mock_session.return_value
            mock_query = mock_db.query.return_value
            mock_filter = mock_query.filter.return_value
            mock_filter.first.return_value = None  # No existing run

            result = should_run_monthly_extrato()
            assert result is True

    def test_should_run_monthly_extrato_already_run(self):
        """Test should_run_monthly_extrato returns False if already run this month."""
        with patch("app.services.extrato_automation.datetime") as mock_datetime, patch(
            "app.services.extrato_automation.SessionLocal"
        ) as mock_session:
            mock_datetime.now.return_value = datetime(2024, 9, 1)
            mock_db = mock_session.return_value
            mock_query = mock_db.query.return_value
            mock_filter = mock_query.filter.return_value
            mock_filter.first.return_value = True  # Already run

            result = should_run_monthly_extrato()
            assert result is False

    def test_should_run_monthly_extrato_after_first(self):
        """Test should_run_monthly_extrato returns True after the 1st of the month."""
        with patch("app.services.extrato_automation.datetime") as mock_datetime, patch(
            "app.services.extrato_automation.SessionLocal"
        ) as mock_session:
            mock_datetime.now.return_value = datetime(2024, 9, 5)
            mock_db = mock_session.return_value
            mock_query = mock_db.query.return_value
            mock_filter = mock_query.filter.return_value
            mock_filter.first.return_value = None  # No existing run
            result = should_run_monthly_extrato()
            assert result == True

    def test_should_run_monthly_extrato_with_threshold_2(self):
        """Test should_run_monthly_extrato with min_day_threshold=2 on day 2 (default)."""
        with patch("app.services.extrato_core.datetime") as mock_datetime, patch(
            "app.services.extrato_core.SessionLocal"
        ) as mock_session:
            mock_datetime.now.return_value = datetime(2025, 11, 2)
            mock_db = mock_session.return_value
            mock_query = mock_db.query.return_value
            mock_filter = mock_query.filter.return_value
            mock_filter.first.return_value = None  # No existing run

            from app.services.extrato_core import should_run_monthly_extrato

            # Default threshold is now 2 (Task 2)
            result = should_run_monthly_extrato()
            assert result is True

    def test_should_run_monthly_extrato_threshold_not_reached(self):
        """Test should_run_monthly_extrato returns False when threshold not reached."""
        with patch("app.services.extrato_core.datetime") as mock_datetime:
            # Simulating day < threshold
            mock_datetime.now.return_value = datetime(2025, 11, 1)

            from app.services.extrato_core import should_run_monthly_extrato

            # With threshold=2 (default), day 1 should not run
            result = should_run_monthly_extrato()
            assert result is False
