"""
Common validation utilities for Tattoo Studio controllers.

This module provides consistent validation patterns across all controllers
and API endpoints, ensuring data integrity and proper error handling.
"""

import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.field = field


class ValidationResult:
    """Container for validation results."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.is_valid: bool = True
        self.cleaned_data: Dict[str, Any] = {}

    def add_error(self, message: str, field: Optional[str] = None):
        """Add validation error."""
        error_msg = f"{field}: {message}" if field else message
        self.errors.append(error_msg)
        self.is_valid = False
        logger.warning(f"Validation error: {error_msg}")

    def add_warning(self, message: str, field: Optional[str] = None):
        """Add validation warning."""
        warning_msg = f"{field}: {message}" if field else message
        self.warnings.append(warning_msg)
        logger.info(f"Validation warning: {warning_msg}")


class BaseValidator:
    """Base validator with common validation methods."""

    def validate(
        self, data: Dict[str, Any]
    ) -> ValidationResult:  # pragma: no cover - interface definition
        """Validate data for a specific entity type."""
        raise NotImplementedError("Subclasses must implement validate")

    @staticmethod
    def validate_required_field(
        value: Any, field_name: str, result: ValidationResult
    ) -> bool:
        """Validate that a required field is present and not empty."""
        if (
            value is None
            or value == ""
            or (isinstance(value, str) and value.strip() == "")
        ):
            result.add_error(f"{field_name} é obrigatório", field_name)
            return False
        return True

    @staticmethod
    def validate_date(
        value: Any, field_name: str, result: ValidationResult
    ) -> Optional[date]:
        """Validate and convert date field."""
        if value is None or value == "":
            return None

        if isinstance(value, date):
            return value

        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                result.add_error(f"Data inválida. Use formato YYYY-MM-DD", field_name)
                return None

        result.add_error(f"Formato de data inválido", field_name)
        return None

    @staticmethod
    def validate_decimal(
        value: Any,
        field_name: str,
        result: ValidationResult,
        min_value: Optional[Decimal] = None,
        max_value: Optional[Decimal] = None,
    ) -> Optional[Decimal]:
        """Validate and convert decimal field."""
        if value is None or value == "":
            return None

        if isinstance(value, Decimal):
            decimal_value = value
        else:
            try:
                # Handle string input with normalization
                if isinstance(value, str):
                    # Remove spaces
                    value = value.strip().replace(" ", "")
                    # Handle Brazilian format (1.234,56 -> 1234.56)
                    if "," in value and "." in value:
                        # If both comma and dot, assume dot is thousand separator
                        value = value.replace(".", "").replace(",", ".")
                    elif "," in value:
                        # Only comma, assume it's decimal separator
                        value = value.replace(",", ".")

                decimal_value = Decimal(str(value))
            except (InvalidOperation, TypeError, ValueError):
                result.add_error(f"Valor inválido. Use formato numérico", field_name)
                return None

        # Range validation
        if min_value is not None and decimal_value < min_value:
            result.add_error(f"Valor deve ser maior que {min_value}", field_name)
            return None

        if max_value is not None and decimal_value > max_value:
            result.add_error(f"Valor deve ser menor que {max_value}", field_name)
            return None

        return decimal_value

    @staticmethod
    def validate_integer(
        value: Any,
        field_name: str,
        result: ValidationResult,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
    ) -> Optional[int]:
        """Validate and convert integer field."""
        if value is None or value == "":
            return None

        try:
            int_value = int(value)
        except (ValueError, TypeError):
            result.add_error(f"Valor deve ser um número inteiro", field_name)
            return None

        # Range validation
        if min_value is not None and int_value < min_value:
            result.add_error(f"Valor deve ser maior que {min_value}", field_name)
            return None

        if max_value is not None and int_value > max_value:
            result.add_error(f"Valor deve ser menor que {max_value}", field_name)
            return None

        return int_value

    @staticmethod
    def validate_string(
        value: Any,
        field_name: str,
        result: ValidationResult,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        allowed_values: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Validate string field."""
        if value is None:
            return None

        if not isinstance(value, str):
            value = str(value)

        # Strip whitespace
        value = value.strip()

        # Length validation
        if min_length is not None and len(value) < min_length:
            result.add_error(f"Deve ter pelo menos {min_length} caracteres", field_name)
            return None

        if max_length is not None and len(value) > max_length:
            result.add_error(f"Deve ter no máximo {max_length} caracteres", field_name)
            return None

        # Allowed values validation
        if allowed_values is not None and value not in allowed_values:
            result.add_error(
                f"Valor deve ser um dos: {', '.join(allowed_values)}", field_name
            )
            return None

        return value if value else None


class PagamentoValidator(BaseValidator):
    """Validator for payment (Pagamento) entities."""

    ALLOWED_PAYMENT_METHODS = [
        "PIX",
        "Dinheiro",
        "Cartão de Crédito",
        "Cartão de Débito",
        "Transferência Bancária",
        "Outros",
    ]

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate payment data."""
        result = ValidationResult()

        # Required fields
        self.validate_required_field(data.get("data"), "data", result)
        self.validate_required_field(data.get("valor"), "valor", result)
        self.validate_required_field(
            data.get("forma_pagamento"), "forma_pagamento", result
        )
        self.validate_required_field(data.get("artista_id"), "artista_id", result)

        # Date validation
        data_value = self.validate_date(data.get("data"), "data", result)
        if data_value:
            result.cleaned_data["data"] = data_value

        # Valor validation (must be positive)
        valor = self.validate_decimal(
            data.get("valor"), "valor", result, min_value=Decimal("0.01")
        )
        if valor is not None:
            result.cleaned_data["valor"] = valor

        # Payment method validation
        forma_pagamento = self.validate_string(
            data.get("forma_pagamento"),
            "forma_pagamento",
            result,
            min_length=1,
            max_length=50,
            allowed_values=self.ALLOWED_PAYMENT_METHODS,
        )
        if forma_pagamento:
            result.cleaned_data["forma_pagamento"] = forma_pagamento

        # Artist ID validation
        artista_id = self.validate_integer(
            data.get("artista_id"), "artista_id", result, min_value=1
        )
        if artista_id is not None:
            result.cleaned_data["artista_id"] = artista_id

        # Optional client ID validation
        if data.get("cliente_id"):
            cliente_id = self.validate_integer(
                data.get("cliente_id"), "cliente_id", result, min_value=1
            )
            if cliente_id is not None:
                result.cleaned_data["cliente_id"] = cliente_id

        # Optional percentage validation (0-100)
        if data.get("porcentagem"):
            porcentagem = self.validate_decimal(
                data.get("porcentagem"),
                "porcentagem",
                result,
                min_value=Decimal("0"),
                max_value=Decimal("100"),
            )
            if porcentagem is not None:
                result.cleaned_data["porcentagem"] = porcentagem

        return result


class GastoValidator(BaseValidator):
    """Validator for expense (Gasto) entities."""

    ALLOWED_PAYMENT_METHODS = [
        "PIX",
        "Dinheiro",
        "Cartão de Crédito",
        "Cartão de Débito",
        "Transferência Bancária",
        "Outros",
    ]

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate expense data."""
        result = ValidationResult()

        # Required fields
        self.validate_required_field(data.get("data"), "data", result)
        self.validate_required_field(data.get("valor"), "valor", result)
        self.validate_required_field(data.get("descricao"), "descricao", result)
        self.validate_required_field(
            data.get("forma_pagamento"), "forma_pagamento", result
        )

        # Date validation
        data_value = self.validate_date(data.get("data"), "data", result)
        if data_value:
            result.cleaned_data["data"] = data_value

        # Valor validation (must be positive)
        valor = self.validate_decimal(
            data.get("valor"), "valor", result, min_value=Decimal("0.01")
        )
        if valor is not None:
            result.cleaned_data["valor"] = valor

        # Description validation
        descricao = self.validate_string(
            data.get("descricao"), "descricao", result, min_length=1, max_length=255
        )
        if descricao:
            result.cleaned_data["descricao"] = descricao

        # Payment method validation
        forma_pagamento = self.validate_string(
            data.get("forma_pagamento"),
            "forma_pagamento",
            result,
            min_length=1,
            max_length=50,
            allowed_values=self.ALLOWED_PAYMENT_METHODS,
        )
        if forma_pagamento:
            result.cleaned_data["forma_pagamento"] = forma_pagamento

        return result


class SessaoValidator(BaseValidator):
    """Validator for session (Sessao) entities."""

    ALLOWED_STATUSES = ["scheduled", "active", "completed", "paid", "cancelled"]

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate session data."""
        result = ValidationResult()

        # Required fields
        self.validate_required_field(data.get("data"), "data", result)
        self.validate_required_field(data.get("cliente_id"), "cliente_id", result)
        self.validate_required_field(data.get("artista_id"), "artista_id", result)
        self.validate_required_field(data.get("valor"), "valor", result)

        # Date validation
        data_value = self.validate_date(data.get("data"), "data", result)
        if data_value:
            result.cleaned_data["data"] = data_value

        # Valor validation (must be positive)
        valor = self.validate_decimal(
            data.get("valor"), "valor", result, min_value=Decimal("0.01")
        )
        if valor is not None:
            result.cleaned_data["valor"] = valor

        # Client ID validation
        cliente_id = self.validate_integer(
            data.get("cliente_id"), "cliente_id", result, min_value=1
        )
        if cliente_id is not None:
            result.cleaned_data["cliente_id"] = cliente_id

        # Artist ID validation
        artista_id = self.validate_integer(
            data.get("artista_id"), "artista_id", result, min_value=1
        )
        if artista_id is not None:
            result.cleaned_data["artista_id"] = artista_id

        # Optional status validation
        if data.get("status"):
            status_value = self.validate_string(
                data.get("status"),
                "status",
                result,
                allowed_values=self.ALLOWED_STATUSES,
            )
            if status_value:
                result.cleaned_data["status"] = status_value

        # Optional description validation
        if data.get("descricao"):
            descricao = self.validate_string(
                data.get("descricao"), "descricao", result, max_length=500
            )
            if descricao:
                result.cleaned_data["descricao"] = descricao

        # Optional observations validation
        if data.get("observacoes"):
            observacoes = self.validate_string(
                data.get("observacoes"), "observacoes", result, max_length=1000
            )
            if observacoes:
                result.cleaned_data["observacoes"] = observacoes

        return result


class ComissaoValidator(BaseValidator):
    """Validator for commission (Comissao) entities."""

    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate commission data."""
        result = ValidationResult()

        # Required fields
        self.validate_required_field(data.get("valor"), "valor", result)
        self.validate_required_field(data.get("porcentagem"), "porcentagem", result)
        self.validate_required_field(data.get("pagamento_id"), "pagamento_id", result)
        self.validate_required_field(data.get("artista_id"), "artista_id", result)

        # Valor validation (must be positive)
        valor = self.validate_decimal(
            data.get("valor"), "valor", result, min_value=Decimal("0.01")
        )
        if valor is not None:
            result.cleaned_data["valor"] = valor

        # Percentage validation (0-100)
        porcentagem = self.validate_decimal(
            data.get("porcentagem"),
            "porcentagem",
            result,
            min_value=Decimal("0"),
            max_value=Decimal("100"),
        )
        if porcentagem is not None:
            result.cleaned_data["porcentagem"] = porcentagem

        # Payment ID validation
        pagamento_id = self.validate_integer(
            data.get("pagamento_id"), "pagamento_id", result, min_value=1
        )
        if pagamento_id is not None:
            result.cleaned_data["pagamento_id"] = pagamento_id

        # Artist ID validation
        artista_id = self.validate_integer(
            data.get("artista_id"), "artista_id", result, min_value=1
        )
        if artista_id is not None:
            result.cleaned_data["artista_id"] = artista_id

        return result


# Factory function to get appropriate validator
def get_validator(entity_type: str) -> BaseValidator:
    """Get validator instance for entity type."""
    validators = {
        "pagamento": PagamentoValidator(),
        "gasto": GastoValidator(),
        "sessao": SessaoValidator(),
        "comissao": ComissaoValidator(),
    }

    validator = validators.get(entity_type.lower())
    if not validator:
        raise ValueError(f"No validator found for entity type: {entity_type}")

    return validator


# Convenience functions for common validations
def validate_pagamento(data: Dict[str, Any]) -> ValidationResult:
    """Validate payment data."""
    return get_validator("pagamento").validate(data)


def validate_gasto(data: Dict[str, Any]) -> ValidationResult:
    """Validate expense data."""
    return get_validator("gasto").validate(data)


def validate_sessao(data: Dict[str, Any]) -> ValidationResult:
    """Validate session data."""
    return get_validator("sessao").validate(data)


def validate_comissao(data: Dict[str, Any]) -> ValidationResult:
    """Validate commission data."""
    return get_validator("comissao").validate(data)
