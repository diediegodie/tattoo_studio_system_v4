"""
Unit tests for EventPrefillService (Phase 2)
Tests event data parsing, field normalization, and duplicate detection helpers
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from app.services.prefill_service import EventPrefillService


class TestEventPrefillServiceParsing:
    """Test event data parsing and normalization"""

    def setup_method(self):
        """Set up test fixtures"""
        self.service = EventPrefillService()

    def test_parse_event_basic_fields(self):
        """Test basic field extraction from event data"""
        result = self.service.parse_event_for_payment_form(
            google_event_id="test_event_123",
            title="Tattoo - João Silva",
            start_datetime=datetime(2025, 11, 25, 14, 0),
            description="Valor: R$ 300,00",
        )

        assert result["google_event_id"] == "test_event_123"
        assert result["data"] == "2025-11-25"
        assert result["cliente_nome"] == "João Silva"
        assert result["valor"] == "300.00"
        assert result["forma_pagamento"] is None  # User must select

    def test_parse_event_with_client_name_extraction(self):
        """Test client name extraction from various title formats"""
        test_cases = [
            ("Tattoo - Maria Santos", "Maria Santos"),
            ("Sessão - Pedro Costa", "Pedro Costa"),
            ("Ana Paula (tattoo)", "Ana Paula"),
            ("Carlos Eduardo - Agendamento", "Carlos Eduardo"),
            (
                "Juliana Ferreira",
                "Juliana Ferreira",
            ),  # No keywords, assume entire title
        ]

        for title, expected_client in test_cases:
            result = self.service.parse_event_for_payment_form(
                google_event_id="test",
                title=title,
            )
            assert (
                result["cliente_nome"] == expected_client
            ), f"Failed for title: {title}"

    def test_parse_event_valor_from_description(self):
        """Test valor extraction from various description formats"""
        test_cases = [
            ("R$ 300,00", "300.00"),
            ("Valor: R$ 450", "450.00"),
            ("Valor: 250.50", "250.50"),
            ("500 reais", "500.00"),
            ("R$150", "150.00"),
        ]

        for description, expected_valor in test_cases:
            result = self.service.parse_event_for_payment_form(
                google_event_id="test",
                description=description,
            )
            assert (
                result["valor"] == expected_valor
            ), f"Failed for description: {description}"

    def test_normalize_valor_brazilian_format(self):
        """Test valor normalization for Brazilian currency format"""
        assert self.service._normalize_valor("1.234,56") == "1234.56"
        assert self.service._normalize_valor("1 234,56") == "1234.56"
        assert self.service._normalize_valor("300") == "300.00"
        assert self.service._normalize_valor("300,50") == "300.50"

    def test_normalize_valor_us_format(self):
        """Test valor normalization for US currency format"""
        assert self.service._normalize_valor("1234.56") == "1234.56"
        assert self.service._normalize_valor("300.00") == "300.00"

    def test_normalize_valor_invalid(self):
        """Test valor normalization with invalid input"""
        assert self.service._normalize_valor("") is None
        assert self.service._normalize_valor(None) is None
        assert self.service._normalize_valor("abc") is None

    def test_parse_event_observacoes_from_description(self):
        """Test observacoes field populated from description or title"""
        result = self.service.parse_event_for_payment_form(
            google_event_id="test",
            description="Cliente solicitou tatuagem de dragão no braço esquerdo",
        )
        assert "dragão" in result["observacoes"]
        assert len(result["observacoes"]) <= 500  # Truncation test

    def test_parse_event_for_session_form_compatibility(self):
        """Test session form parsing maintains compatibility"""
        result = self.service.parse_event_for_session_form(
            google_event_id="test",
            title="Tattoo - João",
            start_datetime=datetime(2025, 11, 25, 14, 0),
        )

        # Should have all payment form fields
        assert "google_event_id" in result
        assert "data" in result
        # Should also have session-specific status field
        assert result["status"] == "active"

    def test_parse_event_missing_google_event_id(self):
        """Test handling of missing google_event_id"""
        result = self.service.parse_event_for_payment_form(
            google_event_id=None,
            title="Tattoo",
        )
        assert result["google_event_id"] is None

    def test_parse_event_date_parsing_error(self):
        """Test handling of invalid start_datetime"""
        result = self.service.parse_event_for_payment_form(
            google_event_id="test",
            start_datetime="invalid",  # Invalid type
        )
        assert result["data"] is None


class TestEventPrefillServiceDuplicateChecks:
    """Test duplicate detection helper functions"""

    def test_check_duplicate_payment_exists(self):
        """Test duplicate payment detection when payment exists"""
        # Mock database session
        mock_db = Mock()
        mock_payment = Mock()
        mock_payment.id = 123
        mock_db.query().filter().first.return_value = mock_payment

        exists, payment_id = EventPrefillService.check_duplicate_payment_by_event_id(
            mock_db, "test_event_123"
        )

        assert exists is True
        assert payment_id == 123

    def test_check_duplicate_payment_not_exists(self):
        """Test duplicate payment detection when payment does not exist"""
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None

        exists, payment_id = EventPrefillService.check_duplicate_payment_by_event_id(
            mock_db, "test_event_123"
        )

        assert exists is False
        assert payment_id is None

    def test_check_duplicate_payment_empty_event_id(self):
        """Test duplicate check with empty google_event_id"""
        mock_db = Mock()

        exists, payment_id = EventPrefillService.check_duplicate_payment_by_event_id(
            mock_db, ""
        )

        assert exists is False
        assert payment_id is None

    def test_check_duplicate_payment_db_error(self):
        """Test duplicate check handles database errors gracefully"""
        mock_db = Mock()
        mock_db.query.side_effect = Exception("Database error")

        exists, payment_id = EventPrefillService.check_duplicate_payment_by_event_id(
            mock_db, "test_event_123"
        )

        # Should fail open (return False to allow operation)
        assert exists is False
        assert payment_id is None

    def test_check_duplicate_session_exists(self):
        """Test duplicate session detection for legacy flow"""
        mock_db = Mock()
        mock_session = Mock()
        mock_session.id = 456
        mock_db.query().filter().first.return_value = mock_session

        exists, session_id = EventPrefillService.check_duplicate_session_by_event_id(
            mock_db, "test_event_123"
        )

        assert exists is True
        assert session_id == 456

    def test_check_duplicate_session_not_exists(self):
        """Test duplicate session detection when session does not exist"""
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None

        exists, session_id = EventPrefillService.check_duplicate_session_by_event_id(
            mock_db, "test_event_123"
        )

        assert exists is False
        assert session_id is None


class TestEventPrefillServiceEdgeCases:
    """Test edge cases and error handling"""

    def setup_method(self):
        """Set up test fixtures"""
        self.service = EventPrefillService()

    def test_parse_event_with_all_none_values(self):
        """Test parsing with all None input values"""
        result = self.service.parse_event_for_payment_form()

        assert result["google_event_id"] is None
        assert result["data"] is None
        assert result["cliente_nome"] is None
        assert result["valor"] is None
        assert result["observacoes"] is None

    def test_parse_event_with_empty_strings(self):
        """Test parsing with empty string inputs"""
        result = self.service.parse_event_for_payment_form(
            google_event_id="",
            title="",
            description="",
        )

        assert result["google_event_id"] is None  # Empty stripped to None
        assert result["cliente_nome"] is None
        assert result["observacoes"] is None

    def test_parse_event_long_observacoes_truncation(self):
        """Test observacoes field truncation to 500 characters"""
        long_text = "A" * 1000  # 1000 characters
        result = self.service.parse_event_for_payment_form(
            google_event_id="test",
            description=long_text,
        )

        assert len(result["observacoes"]) == 500

    def test_parse_event_special_characters_in_client_name(self):
        """Test client name extraction with special characters"""
        result = self.service.parse_event_for_payment_form(
            google_event_id="test",
            title="Tattoo - José María Àçénto",
        )

        assert result["cliente_nome"] == "José María Àçénto"

    def test_parse_event_artista_id_type_conversion(self):
        """Test artist ID type conversion from string to int"""
        result = self.service.parse_event_for_payment_form(
            google_event_id="test",
            artist_id="42",  # String input
        )

        assert result["artista_id"] == 42  # Converted to int
        assert isinstance(result["artista_id"], int)

    def test_parse_event_artista_id_invalid(self):
        """Test artist ID with invalid input"""
        result = self.service.parse_event_for_payment_form(
            google_event_id="test",
            artist_id="invalid",
        )

        assert result["artista_id"] is None
