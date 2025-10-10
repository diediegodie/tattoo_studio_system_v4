"""
Unit tests for template helper functions.
Tests consistent client display and currency formatting.
"""

import pytest
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from unittest.mock import Mock

from app.utils.template_helpers import (
    format_client_name,
    format_currency,
    format_date_br,
    safe_attr,
)


class TestFormatClientName:
    """Test client name formatting with various input scenarios."""

    def test_format_client_name_with_name_attribute(self):
        """Test client with 'name' attribute."""
        client = Mock()
        client.name = "João Silva"

        result = format_client_name(client)
        assert result == "João Silva"

    def test_format_client_name_with_nome_sobrenome(self):
        """Test client with 'nome' and 'sobrenome' attributes."""
        client = Mock()
        client.name = None
        client.nome = "Maria"
        client.sobrenome = "Santos"

        result = format_client_name(client)
        assert result == "Maria Santos"

    def test_format_client_name_with_nome_only(self):
        """Test client with 'nome' but no 'sobrenome' attribute."""

        # Create a simple object with only nome attribute
        class SimpleClient:
            def __init__(self):
                self.name = None
                self.nome = "Carlos"

        client = SimpleClient()

        result = format_client_name(client)
        assert result == "Carlos"

    def test_format_client_name_with_none_client(self):
        """Test with None client returns default fallback."""
        result = format_client_name(None)
        assert result == "Não informado"

    def test_format_client_name_with_custom_fallback(self):
        """Test with custom fallback text."""
        result = format_client_name(None, "Sem cliente")
        assert result == "Sem cliente"

    def test_format_client_name_with_empty_name(self):
        """Test client with empty name returns fallback."""

        # Create a simple object with only name attribute
        class SimpleClient:
            def __init__(self):
                self.name = ""

        client = SimpleClient()

        result = format_client_name(client)
        assert result == "Não informado"

    def test_format_client_name_with_whitespace_only_name(self):
        """Test client with whitespace-only name returns fallback."""
        client = Mock()
        client.name = "   "

        result = format_client_name(client)
        assert result == "Não informado"

    def test_format_client_name_strips_whitespace(self):
        """Test that whitespace is stripped from names."""
        client = Mock()
        client.name = "  João Silva  "

        result = format_client_name(client)
        assert result == "João Silva"

    def test_format_client_name_with_empty_nome(self):
        """Test client with empty nome returns fallback."""
        client = Mock()
        client.name = None
        client.nome = ""

        result = format_client_name(client)
        assert result == "Não informado"

    def test_format_client_name_with_none_nome(self):
        """Test client with None nome returns fallback."""
        client = Mock()
        client.name = None
        client.nome = None

        result = format_client_name(client)
        assert result == "Não informado"

    def test_format_client_name_nome_with_empty_sobrenome(self):
        """Test client with nome and empty sobrenome."""
        client = Mock()
        client.name = None
        client.nome = "Ana"
        client.sobrenome = ""

        result = format_client_name(client)
        assert result == "Ana"

    def test_format_client_name_nome_with_whitespace_sobrenome(self):
        """Test client with nome and whitespace-only sobrenome."""
        client = Mock()
        client.name = None
        client.nome = "Pedro"
        client.sobrenome = "   "

        result = format_client_name(client)
        assert result == "Pedro"


class TestFormatCurrency:
    """Test currency formatting in Brazilian format."""

    def test_format_currency_with_float(self):
        """Test formatting float values."""
        result = format_currency(100.50)
        assert result == "R$ 100,50"

    def test_format_currency_with_large_number(self):
        """Test formatting large numbers with thousands separator."""
        result = format_currency(1000.75)
        assert result == "R$ 1.000,75"

    def test_format_currency_with_very_large_number(self):
        """Test formatting very large numbers."""
        result = format_currency(1234567.89)
        assert result == "R$ 1.234.567,89"

    def test_format_currency_with_decimal(self):
        """Test formatting Decimal values."""
        result = format_currency(Decimal("150.25"))
        assert result == "R$ 150,25"

    def test_format_currency_with_none(self):
        """Test formatting None values."""
        result = format_currency(None)
        assert result == "R$ 0,00"

    def test_format_currency_with_string(self):
        """Test formatting string numeric values."""
        result = format_currency("250.80")
        assert result == "R$ 250,80"

    def test_format_currency_with_invalid_string(self):
        """Test formatting invalid string returns zero."""
        result = format_currency("invalid")
        assert result == "R$ 0,00"

    def test_format_currency_with_integer(self):
        """Test formatting integer values."""
        result = format_currency(500)
        assert result == "R$ 500,00"

    def test_format_currency_with_zero(self):
        """Test formatting zero value."""
        result = format_currency(0)
        assert result == "R$ 0,00"

    def test_format_currency_with_negative_value(self):
        """Test formatting negative values."""
        result = format_currency(-150.75)
        assert result == "R$ -150,75"

    def test_format_currency_with_small_decimal(self):
        """Test formatting small decimal values."""
        result = format_currency(0.05)
        assert result == "R$ 0,05"

    def test_format_currency_with_string_integer(self):
        """Test formatting string integer values."""
        result = format_currency("1000")
        assert result == "R$ 1.000,00"

    def test_format_currency_with_empty_string(self):
        """Test formatting empty string returns zero."""
        result = format_currency("")
        assert result == "R$ 0,00"


class TestFormatDateBr:
    """Test Brazilian date formatting."""

    def test_format_date_br_with_date(self):
        """Test formatting date object."""
        test_date = date(2024, 1, 15)
        result = format_date_br(test_date)
        assert result == "15/01/2024"

    def test_format_date_br_with_datetime(self):
        """Test formatting datetime object."""
        test_datetime = datetime(2024, 12, 25, 14, 30)
        result = format_date_br(test_datetime)
        assert result == "25/12/2024"

    def test_format_date_br_with_none(self):
        """Test formatting None returns empty string."""
        result = format_date_br(None)
        assert result == ""

    def test_format_date_br_with_custom_format(self):
        """Test formatting with custom format string."""
        test_date = date(2024, 6, 10)
        result = format_date_br(test_date, "%m/%Y")
        assert result == "06/2024"

    def test_format_date_br_with_datetime_and_time_format(self):
        """Test formatting datetime with time format."""
        test_datetime = datetime(2024, 3, 8, 9, 15, 30)
        result = format_date_br(test_datetime, "%d/%m/%Y %H:%M")
        assert result == "08/03/2024 09:15"

    def test_format_date_br_with_invalid_object(self):
        """Test formatting invalid object returns empty string."""
        # Test with a string that doesn't have strftime method
        result = format_date_br("not a date")  # type: ignore
        assert result == ""

    def test_format_date_br_with_single_digit_day_month(self):
        """Test formatting date with single digit day and month."""
        test_date = date(2024, 1, 5)
        result = format_date_br(test_date)
        assert result == "05/01/2024"

    def test_format_date_br_with_include_time_true(self):
        """Test formatting datetime with include_time=True."""
        test_datetime = datetime(2024, 1, 15, 14, 30, 0)
        result = format_date_br(test_datetime, include_time=True)
        assert result == "15/01/2024 às 14:30"

    def test_format_date_br_with_include_time_and_date_object(self):
        """Test formatting date object with include_time=True (should ignore time)."""
        test_date = date(2024, 1, 15)
        result = format_date_br(test_date, include_time=True)
        assert result == "15/01/2024"


class TestSafeAttr:
    """Test safe attribute access helper."""

    def test_safe_attr_with_valid_object(self):
        """Test getting attribute from valid object."""
        obj = Mock()
        obj.name = "Test Name"

        result = safe_attr(obj, "name")
        assert result == "Test Name"

    def test_safe_attr_with_none_object(self):
        """Test getting attribute from None object."""
        result = safe_attr(None, "name")
        assert result == ""

    def test_safe_attr_with_missing_attribute(self):
        """Test getting missing attribute returns fallback."""

        # Create an object without the attribute
        class SimpleObj:
            def __init__(self):
                self.existing_attr = "exists"

        obj = SimpleObj()

        result = safe_attr(obj, "nonexistent")
        assert result == ""

    def test_safe_attr_with_custom_fallback(self):
        """Test getting attribute with custom fallback."""
        result = safe_attr(None, "name", "N/A")
        assert result == "N/A"

    def test_safe_attr_strips_whitespace(self):
        """Test that attribute values are stripped."""
        obj = Mock()
        obj.name = "  Test Name  "

        result = safe_attr(obj, "name")
        assert result == "Test Name"

    def test_safe_attr_with_none_attribute_value(self):
        """Test attribute with None value returns fallback."""
        obj = Mock()
        obj.name = None

        result = safe_attr(obj, "name", "Default")
        assert result == "Default"

    def test_safe_attr_with_numeric_attribute(self):
        """Test attribute with numeric value converts to string."""
        obj = Mock()
        obj.value = 123

        result = safe_attr(obj, "value")
        assert result == "123"

    def test_safe_attr_with_boolean_attribute(self):
        """Test attribute with boolean value converts to string."""
        obj = Mock()
        obj.active = True

        result = safe_attr(obj, "active")
        assert result == "True"

    def test_safe_attr_with_empty_string_attribute(self):
        """Test attribute with empty string value returns fallback."""
        obj = Mock()
        obj.name = ""

        result = safe_attr(obj, "name", "Empty")
        assert result == "Empty"  # Empty string should trigger fallback
