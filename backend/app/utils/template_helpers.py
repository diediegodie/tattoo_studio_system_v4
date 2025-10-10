"""Template helper functions for consistent UI rendering.

This module provides Jinja2 template functions for:
- Client name formatting with fallbacks
- Currency formatting in Brazilian Real
- Date formatting consistency

Following the project's SOLID principles and guidelines.
"""

from typing import Optional, Union, Any
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


def format_client_name(client: Optional[Any], fallback: str = "Não informado") -> str:
    """Format client name with consistent fallback for missing clients.

    Args:
        client: Client object with 'name' or 'nome' attribute, or None
        fallback: Text to display when client is None/missing

    Returns:
        Formatted client name or fallback text

    Examples:
        format_client_name(client)  # "João Silva"
        format_client_name(None)    # "Não informado"
        format_client_name(None, "Sem cliente")  # "Sem cliente"
    """
    if not client:
        return fallback

    # Handle different client object structures
    if hasattr(client, "name") and client.name:
        name = str(client.name).strip()
        if name:  # Only return if not empty after stripping
            return name
    elif hasattr(client, "nome") and client.nome:
        # For domain entities that use 'nome' instead of 'name'
        nome = str(client.nome).strip()
        if nome:  # Only proceed if nome is not empty
            if hasattr(client, "sobrenome") and client.sobrenome:
                sobrenome = str(client.sobrenome).strip()
                full_name = f"{nome} {sobrenome}".strip()
                if full_name:
                    return full_name
            return nome

    return fallback


def format_currency(
    value: Union[float, Decimal, int, str, None], currency: str = "BRL"
) -> str:
    """Format currency value in Brazilian Real format.

    Args:
        value: Numeric value to format
        currency: Currency code (default: BRL)

    Returns:
        Formatted currency string

    Examples:
        format_currency(100.50)    # "R$ 100,50"
        format_currency(1000)      # "R$ 1.000,00"
        format_currency(None)      # "R$ 0,00"
        format_currency("150.75")  # "R$ 150,75"
    """
    if value is None:
        value = 0

    try:
        # Convert to Decimal for precise formatting
        if isinstance(value, str):
            decimal_value = Decimal(value)
        else:
            decimal_value = Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation):
        logger.warning(f"Invalid currency value: {value}, using 0")
        decimal_value = Decimal("0")

    # Format using Brazilian locale pattern
    # Convert to float for formatting, then replace separators
    float_value = float(decimal_value)
    formatted = f"{float_value:,.2f}"

    # Brazilian format: thousands separator = ".", decimal separator = ","
    # Python default: thousands separator = ",", decimal separator = "."
    # So we need to swap them
    formatted = formatted.replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")

    return f"R$ {formatted}"


def format_date_br(
    date_value: Union[datetime, date, None],
    format_str: str = "%d/%m/%Y",
    include_time: bool = False,
) -> str:
    """Format date in Brazilian format.

    Args:
        date_value: Date/datetime object to format
        format_str: strftime format string (ignored if include_time is True)
        include_time: If True, includes time in format

    Returns:
        Formatted date string or empty string if None

    Examples:
        format_date_br(date(2024, 1, 15))  # "15/01/2024"
        format_date_br(datetime(2024, 1, 15, 14, 30), include_time=True)  # "15/01/2024 às 14:30"
        format_date_br(None)               # ""
    """
    if not date_value:
        return ""

    try:
        if include_time and isinstance(date_value, datetime):
            return date_value.strftime("%d/%m/%Y às %H:%M")
        else:
            return date_value.strftime(format_str)
    except (AttributeError, ValueError) as e:
        logger.warning(f"Invalid date value: {date_value}, error: {e}")
        return ""


def safe_attr(obj: Optional[Any], attr_name: str, fallback: str = "") -> str:
    """Safely get attribute from object with fallback.

    Args:
        obj: Object to get attribute from
        attr_name: Attribute name to retrieve
        fallback: Value to return if object is None or attribute missing

    Returns:
        Attribute value or fallback

    Examples:
        safe_attr(artista, 'name')        # "Artist Name" or ""
        safe_attr(None, 'name', 'N/A')   # "N/A"
    """
    if not obj:
        return fallback

    try:
        if not hasattr(obj, attr_name):
            return fallback

        value = getattr(obj, attr_name, None)
        if value is None:
            return fallback

        str_value = str(value).strip()
        return str_value if str_value else fallback
    except (AttributeError, TypeError):
        return fallback


def format_currency_dot(value: Union[float, Decimal, int, str, None]) -> str:
    """Format currency with dot as decimal separator and no thousands separator.

    This is used in specific parts of the UI (e.g., Historico totals) where tests
    assert dot-decimal formatting like "R$ 500.00" instead of Brazilian locale
    formatting.

    Args:
        value: Numeric value to format

    Returns:
        String like "R$ 500.00" (dot decimal, no thousands grouping)
    """
    if value is None:
        value = 0

    try:
        if isinstance(value, str):
            decimal_value = Decimal(value or "0")
        else:
            decimal_value = Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation):
        logger.warning(f"Invalid currency value: {value}, using 0")
        decimal_value = Decimal("0")

    # Dot decimal, no thousands grouping
    return f"R$ {float(decimal_value):.2f}"
