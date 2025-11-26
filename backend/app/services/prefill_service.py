"""
Event Prefill Service - Phase 2 of Sessions Removal Refactoring
Single Responsibility: Parse Google Calendar event data and normalize for payment/session forms

Purpose:
    - Parse Google Calendar event parameters (google_event_id, title, date/time, client, artist, amount)
    - Normalize fields to match payment form expectations
    - Provide canonical prefill payload for both legacy session form and new payment form
    - Include duplicate detection helper (non-I/O utility for Phase 2)

Usage:
    - Called by calendar controller to route event data to payment form (Phase 3)
    - Called by payment controller GET to prefill form defaults (Phase 2)
    - Reusable by legacy session form for consistency (Phase 2)

SOLID Principles:
    - Single Responsibility: Event data parsing and normalization only
    - Open/Closed: Extensible for new event sources (e.g., iCal) without modifying existing code
    - Liskov Substitution: Can be swapped with mock implementations in tests
    - Interface Segregation: Focused on prefill operations, not calendar API calls
    - Dependency Inversion: Depends on abstractions (CalendarEvent entity, not concrete API)
"""

import logging
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class EventPrefillService:
    """
    Service to parse and normalize Google Calendar event data for form prefill.

    Phase 2 Note: This service prepares data but does NOT perform I/O in routing logic.
    The duplicate check helper is a utility function for use in controllers.
    """

    def __init__(self):
        """Initialize prefill service."""
        pass

    def parse_event_for_payment_form(
        self,
        google_event_id: Optional[str] = None,
        title: Optional[str] = None,
        start_datetime: Union[datetime, str, None] = None,
        description: Optional[str] = None,
        client_name: Optional[str] = None,
        artist_id: Union[int, str, None] = None,
        valor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Parse Google Calendar event data and produce a canonical prefill payload for payment form.

        Args:
            google_event_id: Unique Google Calendar event ID
            title: Event title (may contain client name or session description)
            start_datetime: Event start date/time (accepts datetime object or ISO string)
            description: Event description (may contain amount, client, artist details)
            client_name: Client name if already extracted
            artist_id: Artist ID if already known (accepts int or numeric string)
            valor: Amount/value if already extracted

        Returns:
            Dictionary with keys matching payment form field names:
            {
                "google_event_id": str or None,
                "data": str (YYYY-MM-DD format) or None,
                "cliente_nome": str or None,
                "artista_id": int or None,
                "valor": str (decimal) or None,
                "observacoes": str or None,
                "forma_pagamento": str or None (defaults to empty for user selection)
            }

        Example:
            >>> service = EventPrefillService()
            >>> payload = service.parse_event_for_payment_form(
            ...     google_event_id="abc123",
            ...     title="Tattoo - João Silva",
            ...     start_datetime=datetime(2025, 11, 25, 14, 0),
            ...     description="Valor: R$ 300,00 | Artista: Maria"
            ... )
            >>> print(payload["data"])  # "2025-11-25"
            >>> print(payload["valor"])  # "300.00"
        """
        prefill_data: Dict[str, Any] = {
            "google_event_id": None,
            "data": None,
            "cliente_nome": None,
            "artista_id": None,
            "valor": None,
            "observacoes": None,
            "forma_pagamento": None,  # User must select payment method
        }

        # 1. Google Event ID (required for duplicate prevention)
        if google_event_id and google_event_id.strip():
            prefill_data["google_event_id"] = google_event_id.strip()

        # 2. Date (convert datetime to YYYY-MM-DD string for HTML date input)
        if start_datetime and isinstance(start_datetime, datetime):
            try:
                prefill_data["data"] = start_datetime.strftime("%Y-%m-%d")
            except Exception as err:
                logger.warning("Failed to format start_datetime: %s", err)
        elif start_datetime and not isinstance(start_datetime, datetime):
            logger.warning("Invalid start_datetime type: %s", type(start_datetime))

        # 3. Client name (extract from title or use provided)
        extracted_client = client_name
        if not extracted_client and title:
            # Try to extract client name from title using common patterns
            keywords = [
                "tattoo",
                "sessão",
                "session",
                "agendamento",
                "piercing",
                "consulta",
            ]

            # Pattern 1: "Tattoo - João Silva" (keyword before dash → take after)
            # Pattern 2: "João Silva - Agendamento" (keyword after dash → take before)
            dash_match = re.search(r"^(.+?)\s*[-–]\s*(.+)$", title)
            if dash_match:
                before_dash = dash_match.group(1).strip()
                after_dash = dash_match.group(2).strip()

                # If the part before dash is a keyword, use what's after
                if any(keyword in before_dash.lower() for keyword in keywords):
                    extracted_client = after_dash
                # If the part after dash is a keyword, use what's before
                elif any(keyword in after_dash.lower() for keyword in keywords):
                    extracted_client = before_dash
                else:
                    # No keyword found, use the longer part (likely the name)
                    extracted_client = (
                        before_dash
                        if len(before_dash) > len(after_dash)
                        else after_dash
                    )

            # Pattern 3: "Ana Paula (tattoo)" (keyword in parens → take before)
            if not extracted_client:
                paren_match = re.search(r"^([A-Za-zÀ-ÿ\s]+)\s*\([^)]*\)", title)
                if paren_match:
                    extracted_client = paren_match.group(1).strip()

            # Pattern 4: No special pattern, assume entire title is client name if no keywords
            if not extracted_client and not any(
                keyword in title.lower() for keyword in keywords
            ):
                extracted_client = title.strip()

        if extracted_client and extracted_client.strip():
            prefill_data["cliente_nome"] = extracted_client.strip()

        # 4. Valor (extract from description or use provided)
        extracted_valor = valor
        if not extracted_valor and description:
            # Try to extract amount from description
            # Patterns: "R$ 300,00", "Valor: 300", "300.00", "R$300", "300 reais"
            valor_patterns = [
                r"R\$?\s*([\d.,]+)",  # R$ 300,00 or R$300
                r"[Vv]alor:\s*R?\$?\s*([\d.,]+)",  # Valor: R$ 300 or Valor: 300
                r"([\d.,]+)\s*reais",  # 300 reais
            ]
            for pattern in valor_patterns:
                match = re.search(pattern, description)
                if match:
                    extracted_valor = match.group(1)
                    break

        if extracted_valor:
            # Normalize valor format (accept "1.234,56" or "1234.56")
            normalized_valor = self._normalize_valor(extracted_valor)
            if normalized_valor:
                prefill_data["valor"] = normalized_valor

        # 5. Artist ID (use provided, no extraction from text in Phase 2)
        if artist_id is not None:
            try:
                # Handle both int and string types
                if isinstance(artist_id, int):
                    prefill_data["artista_id"] = artist_id
                else:
                    prefill_data["artista_id"] = int(artist_id)
            except (ValueError, TypeError):
                logger.warning("Invalid artist_id provided: %s (type: %s)", artist_id, type(artist_id))

        # 6. Observacoes (use description or title as fallback)
        observacoes_text = description or title or ""
        if observacoes_text and observacoes_text.strip():
            # Limit to first 500 characters to avoid textarea overflow
            prefill_data["observacoes"] = observacoes_text.strip()[:500]

        logger.info(
            "Event prefill parsed: google_event_id=%s, data=%s, cliente_nome=%s, valor=%s",
            prefill_data.get("google_event_id"),
            prefill_data.get("data"),
            prefill_data.get("cliente_nome"),
            prefill_data.get("valor"),
        )

        return prefill_data

    def parse_event_for_session_form(
        self,
        google_event_id: Optional[str] = None,
        title: Optional[str] = None,
        start_datetime: Union[datetime, str, None] = None,
        description: Optional[str] = None,
        client_name: Optional[str] = None,
        artist_id: Union[int, str, None] = None,
        valor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Parse Google Calendar event data for session form (legacy flow).

        This method provides the same field mapping as parse_event_for_payment_form
        to maintain parity between legacy session creation and new payment flow.

        Args:
            Same as parse_event_for_payment_form

        Returns:
            Dictionary with keys matching session form field names (identical to payment form)

        Note:
            In Phase 2, this method is provided for consistency. Both legacy session
            and new payment forms can use the same prefill service, reducing code duplication
            and easing eventual removal of session form in Phase 5.
        """
        # Reuse payment form parsing logic for consistency
        prefill_data = self.parse_event_for_payment_form(
            google_event_id=google_event_id,
            title=title,
            start_datetime=start_datetime,
            description=description,
            client_name=client_name,
            artist_id=artist_id,
            valor=valor,
        )

        # Session form uses "status" field (default: "active")
        prefill_data["status"] = "active"

        return prefill_data

    def _normalize_valor(self, valor_str: Optional[str]) -> Optional[str]:
        """
        Normalize valor string to decimal format (e.g., "300.00").

        Accepts formats:
            - "1.234,56" (Brazilian format with thousands separator)
            - "1 234,56" (spaces as thousands separator)
            - "1234.56" (US format)
            - "300" (integer)

        Returns:
            Normalized string in "XXXX.XX" format or None if invalid

        Example:
            >>> service = EventPrefillService()
            >>> service._normalize_valor("1.234,56")
            "1234.56"
            >>> service._normalize_valor("300")
            "300.00"
        """
        if not valor_str:
            return None

        try:
            # Remove whitespace
            cleaned = str(valor_str).strip().replace(" ", "")

            # Handle Brazilian format: "1.234,56" → "1234.56"
            if "," in cleaned and "." in cleaned:
                # Assume dot is thousands separator, comma is decimal
                cleaned = cleaned.replace(".", "").replace(",", ".")
            elif "," in cleaned:
                # Only comma present, assume decimal separator
                cleaned = cleaned.replace(",", ".")

            # Remove any remaining non-digit/non-decimal characters
            cleaned = re.sub(r"[^\d.]", "", cleaned)

            # Convert to Decimal for validation
            valor_decimal = Decimal(cleaned)

            # Format to 2 decimal places
            return f"{valor_decimal:.2f}"

        except (InvalidOperation, ValueError) as err:
            logger.warning("Failed to normalize valor '%s': %s", valor_str, err)
            return None

    @staticmethod
    def check_duplicate_payment_by_event_id(
        db_session: Any, google_event_id: str
    ) -> Tuple[bool, Optional[int]]:
        """
        Utility function to check if a payment already exists for a Google event ID.

        This is a helper for controllers, NOT called during routing in Phase 2.
        Phase 3 will use this in payment POST handler for duplicate prevention.

        Args:
            db_session: SQLAlchemy database session
            google_event_id: Google Calendar event ID to check

        Returns:
            Tuple of (exists: bool, payment_id: Optional[int])
            - exists: True if payment with this google_event_id exists
            - payment_id: ID of existing payment, or None if not found

        Example:
            >>> from app.db.session import SessionLocal
            >>> db = SessionLocal()
            >>> exists, payment_id = EventPrefillService.check_duplicate_payment_by_event_id(
            ...     db, "abc123"
            ... )
            >>> if exists:
            ...     print(f"Payment {payment_id} already exists for this event")

        Note:
            This function does NOT raise exceptions on duplicates. It returns status
            for the controller to decide how to handle (flash message, redirect, etc.)
        """
        if not google_event_id or not google_event_id.strip():
            return False, None

        try:
            from app.db.base import Pagamento

            existing_payment = (
                db_session.query(Pagamento)
                .filter(Pagamento.google_event_id == google_event_id)
                .first()
            )

            if existing_payment:
                logger.info(
                    "Duplicate payment detected: google_event_id=%s, payment_id=%s",
                    google_event_id,
                    existing_payment.id,
                )
                return True, existing_payment.id

            return False, None

        except Exception as err:
            logger.error(
                "Error checking duplicate payment for google_event_id=%s: %s",
                google_event_id,
                err,
            )
            # Return False to allow operation to proceed (fail open for safety)
            return False, None

    @staticmethod
    def check_duplicate_session_by_event_id(
        db_session: Any, google_event_id: str
    ) -> Tuple[bool, Optional[int]]:
        """
        Utility function to check if a session already exists for a Google event ID.

        This is used by the legacy session creation flow for backward compatibility.

        Args:
            db_session: SQLAlchemy database session
            google_event_id: Google Calendar event ID to check

        Returns:
            Tuple of (exists: bool, session_id: Optional[int])

        Note:
            In Phase 3, when unified flow is enabled, this check becomes redundant
            since payments are checked instead. Kept for Phase 2 compatibility.
        """
        if not google_event_id or not google_event_id.strip():
            return False, None

        try:
            from app.db.base import Sessao

            existing_session = (
                db_session.query(Sessao)
                .filter(Sessao.google_event_id == google_event_id)
                .first()
            )

            if existing_session:
                logger.info(
                    "Duplicate session detected: google_event_id=%s, session_id=%s",
                    google_event_id,
                    existing_session.id,
                )
                return True, existing_session.id

            return False, None

        except Exception as err:
            logger.error(
                "Error checking duplicate session for google_event_id=%s: %s",
                google_event_id,
                err,
            )
            return False, None
