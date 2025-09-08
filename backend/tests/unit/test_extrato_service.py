"""
Test for extrato service functionality.
"""
import pytest
from datetime import datetime
from unittest.mock import patch
from app.services.extrato_service import get_previous_month, should_run_monthly_extrato


class TestExtratoService:
    """Test cases for extrato service functionality."""

    def test_get_previous_month_current_date(self):
        """Test get_previous_month with current date logic."""
        with patch('app.services.extrato_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 9, 15)
            mes, ano = get_previous_month()
            assert mes == 8
            assert ano == 2024

    def test_get_previous_month_january(self):
        """Test get_previous_month when current month is January."""
        with patch('app.services.extrato_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 15)
            mes, ano = get_previous_month()
            assert mes == 12
            assert ano == 2023

    def test_should_run_monthly_extrato_early_month(self):
        """Test should_run_monthly_extrato returns False when it's too early in the month."""
        with patch('app.services.extrato_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 9, 1)
            result = should_run_monthly_extrato()
            assert result is False

    def test_should_run_monthly_extrato_after_first(self):
        """Test should_run_monthly_extrato returns True after the 1st of the month."""
        with patch('app.services.extrato_service.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 9, 5)
            result = should_run_monthly_extrato()
            assert result is True</content>
<parameter name="filePath">/home/diego/documentos/github/projetos/tattoo_studio_system_v4/backend/tests/unit/test_extrato_service.py
