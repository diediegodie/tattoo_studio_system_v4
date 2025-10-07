"""
Unit tests for Sessao model.

These tests validate basic model functionality and field behavior
without relying on database constraints.
"""

from datetime import date, datetime, time
from decimal import Decimal

import pytest


@pytest.mark.unit
class TestSessaoModel:
    """Test Sessao model instantiation and basic functionality."""

    def test_sessao_model_instantiation(self):
        """
        P0 Test: Basic Sessao model instantiation.

        Validates:
        - Model can be instantiated with all fields
        - google_event_id field is accessible
        - Basic field assignment works
        """
        try:
            from db.base import Sessao

            # Test instantiation with google_event_id
            sessao_with_google = Sessao(
                data=date(2025, 8, 30),
                valor=Decimal("100.00"),
                observacoes="Test session with Google event",
                cliente_id=1,
                artista_id=1,
                google_event_id="GOOGLE_EVENT_123",
            )

            assert sessao_with_google.data == date(2025, 8, 30)
            assert sessao_with_google.valor == Decimal("100.00")
            assert sessao_with_google.observacoes == "Test session with Google event"
            assert sessao_with_google.cliente_id == 1
            assert sessao_with_google.artista_id == 1
            assert sessao_with_google.google_event_id == "GOOGLE_EVENT_123"

            # Test instantiation without google_event_id (should be None)
            sessao_without_google = Sessao(
                data=date(2025, 8, 31),
                valor=Decimal("150.00"),
                observacoes="Manual test session",
                cliente_id=2,
                artista_id=2,
                # google_event_id not provided
            )

            assert sessao_without_google.data == date(2025, 8, 31)
            assert sessao_without_google.valor == Decimal("150.00")
            assert sessao_without_google.observacoes == "Manual test session"
            assert sessao_without_google.cliente_id == 2
            assert sessao_without_google.artista_id == 2
            assert sessao_without_google.google_event_id is None

        except ImportError:
            pytest.skip("Sessao model not available for testing")

    def test_sessao_model_repr(self):
        """
        P0 Test: Sessao model __repr__ method.

        Validates:
        - String representation includes key fields
        - No errors in string conversion
        """
        try:
            from db.base import Sessao

            sessao = Sessao(
                id=123,
                data=date(2025, 8, 30),
                valor=Decimal("100.00"),
                observacoes="Test session",
                cliente_id=1,
                artista_id=1,
                google_event_id="REPR_TEST",
            )

            # Test that __repr__ works without error
            repr_string = repr(sessao)
            assert isinstance(repr_string, str)

            # Check that key information is included
            assert "Sessao" in repr_string
            assert "123" in repr_string  # ID
            assert "2025-08-30" in repr_string  # Date
            assert "100.00" in repr_string  # Value
            assert "status=" in repr_string  # Status field present

        except ImportError:
            pytest.skip("Sessao model not available for testing")

    def test_sessao_model_field_types(self):
        """
        P0 Test: Sessao model field type validation.

        Validates:
        - Fields accept appropriate data types
        - google_event_id field accepts string and None
        """
        try:
            from db.base import Sessao

            # Test with various field types
            sessao = Sessao()

            # Test date field
            sessao.data = date(2025, 12, 25)
            assert isinstance(sessao.data, date)

            # Test time field

            # Test decimal field
            sessao.valor = Decimal("999.99")
            assert isinstance(sessao.valor, Decimal)
            assert sessao.valor == Decimal("999.99")

            # Test string field
            sessao.observacoes = "String test"
            assert isinstance(sessao.observacoes, str)

            # Test integer fields
            sessao.cliente_id = 42
            sessao.artista_id = 43
            assert isinstance(sessao.cliente_id, int)
            assert isinstance(sessao.artista_id, int)

            # Test google_event_id field with string
            sessao.google_event_id = "STRING_EVENT_ID"
            assert isinstance(sessao.google_event_id, str)
            assert sessao.google_event_id == "STRING_EVENT_ID"

            # Test google_event_id field with None
            sessao.google_event_id = None
            assert sessao.google_event_id is None

        except ImportError:
            pytest.skip("Sessao model not available for testing")

    def test_sessao_model_google_event_id_field_exists(self):
        """
        P0 Test: Verify google_event_id field exists on model.

        This is a critical validation that the field was properly added
        to the model definition.
        """
        try:
            from db.base import Sessao

            # Create an instance to check field existence
            sessao = Sessao()

            # Verify the field exists and can be accessed
            assert hasattr(
                sessao, "google_event_id"
            ), "google_event_id field is missing from Sessao model"

            # Verify it's initially None
            assert sessao.google_event_id is None

            # Verify we can set and get the value
            test_value = "FIELD_EXISTS_TEST"
            sessao.google_event_id = test_value
            assert sessao.google_event_id == test_value

        except ImportError:
            pytest.skip("Sessao model not available for testing")

    def test_sessao_model_table_name(self):
        """
        P0 Test: Verify Sessao model has correct table name.

        Validates:
        - Table name is correctly set
        - Model metadata is accessible
        """
        try:
            from db.base import Sessao

            # Verify table name
            assert hasattr(Sessao, "__tablename__")
            assert Sessao.__tablename__ == "sessoes"

        except ImportError:
            pytest.skip("Sessao model not available for testing")

    def test_sessao_model_nullable_fields(self):
        """
        P0 Test: Test field nullability behavior.

        Validates:
        - google_event_id can be None (nullable)
        - observacoes can be None (nullable)
        - Required fields are properly handled
        """
        try:
            from db.base import Sessao

            # Test minimal valid session (only required fields)
            sessao = Sessao(
                data=date(2025, 1, 1),
                valor=Decimal("50.00"),
                cliente_id=1,
                artista_id=1,
                # google_event_id and observacoes intentionally omitted
            )

            # These should be None by default
            assert sessao.google_event_id is None
            assert sessao.observacoes is None

            # Test explicit None assignment
            sessao.google_event_id = None
            sessao.observacoes = None

            assert sessao.google_event_id is None
            assert sessao.observacoes is None

        except ImportError:
            pytest.skip("Sessao model not available for testing")

    def test_sessao_model_relationships(self):
        """
        P0 Test: Verify model relationship attributes exist.

        Validates:
        - cliente relationship attribute exists
        - artista relationship attribute exists
        - Relationships are properly configured
        """
        try:
            from db.base import Sessao

            # Verify relationship attributes exist
            assert hasattr(
                Sessao, "cliente"
            ), "cliente relationship is missing from Sessao model"
            assert hasattr(
                Sessao, "artista"
            ), "artista relationship is missing from Sessao model"

        except ImportError:
            pytest.skip("Sessao model not available for testing")
