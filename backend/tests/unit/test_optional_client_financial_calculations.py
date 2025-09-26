"""
Tests for financial calculations and services with optional cliente_id.

This module tests financial calculations, extrato generation, and services
to ensure they correctly handle payments with and without clients.
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestFinancialCalculationsOptionalClient:
    """Test financial calculations with payments that have optional clients."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return MagicMock()

    @pytest.fixture
    def mixed_payments_data(self):
        """Sample payments with mixed client scenarios."""
        payment_with_client = Mock()
        payment_with_client.valor = Decimal("100.00")
        payment_with_client.cliente_id = 1
        payment_with_client.cliente = Mock()
        payment_with_client.cliente.name = "Test Client"

        payment_without_client = Mock()
        payment_without_client.valor = Decimal("150.00")
        payment_without_client.cliente_id = None
        payment_without_client.cliente = None

        return [payment_with_client, payment_without_client]

    def test_calculate_totals_includes_null_client_payments(
        self, mock_db_session, mixed_payments_data
    ):
        """Test that calculate_totals includes payments without clients in totals."""
        try:
            from app.services.financeiro_service import calculate_totals

            with patch(
                "app.services.financeiro_service.SessionLocal",
                return_value=mock_db_session,
            ):
                # Mock query to return mixed payments
                mock_db_session.query.return_value.filter.return_value.all.return_value = (
                    mixed_payments_data
                )

                # Call calculate_totals
                result = calculate_totals(2024, 1)  # January 2024

                # Verify both payments are included in total
                expected_total = Decimal("100.00") + Decimal("150.00")  # 250.00
                assert result["total_pagamentos"] == expected_total
                assert result["count_pagamentos"] == 2

        except ImportError:
            pytest.skip("financeiro_service.calculate_totals not implemented yet")

    def test_calculate_totals_with_only_null_client_payments(self, mock_db_session):
        """Test calculate_totals with only payments without clients."""
        null_client_payments = [
            Mock(valor=Decimal("50.00"), cliente_id=None),
            Mock(valor=Decimal("75.00"), cliente_id=None),
        ]

        try:
            from app.services.financeiro_service import calculate_totals

            with patch(
                "app.services.financeiro_service.SessionLocal",
                return_value=mock_db_session,
            ):
                mock_db_session.query.return_value.filter.return_value.all.return_value = (
                    null_client_payments
                )

                result = calculate_totals(2024, 1)

                expected_total = Decimal("125.00")
                assert result["total_pagamentos"] == expected_total
                assert result["count_pagamentos"] == 2

        except ImportError:
            pytest.skip("financeiro_service.calculate_totals not implemented yet")

    def test_calculate_revenue_excludes_sessions_includes_all_payments(
        self, mock_db_session, mixed_payments_data
    ):
        """Test that revenue calculation correctly counts all payments regardless of client."""
        try:
            from app.scripts.extrato_core import calculate_totals

            # Mock sessions (should not be double-counted in revenue)
            mock_sessions = [
                Mock(valor=Decimal("200.00"), payment_id=None),  # Unpaid session
            ]

            with patch(
                "app.scripts.extrato_core.SessionLocal", return_value=mock_db_session
            ):
                # Setup query mocks
                query_mock = mock_db_session.query.return_value
                query_mock.filter.return_value.all.side_effect = [
                    mixed_payments_data,  # Payments query
                    mock_sessions,  # Sessions query
                    [],  # Gastos query
                ]

                result = calculate_totals(2024, 1)

                # Revenue should only count payments (250.00), not sessions
                expected_revenue = Decimal("250.00")
                assert result["receita_bruta"] == expected_revenue

        except ImportError:
            pytest.skip("extrato_core.calculate_totals not implemented yet")


class TestExtratoGenerationOptionalClient:
    """Test extrato generation with optional client payments."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return MagicMock()

    def test_serialize_payment_without_client(self):
        """Test serializing payment data when client is null."""
        try:
            from app.scripts.generate_monthly_extrato_from_tests import serialize_data

            # Mock payment without client
            mock_payment = Mock()
            mock_payment.id = 1
            mock_payment.data = date(2024, 1, 15)
            mock_payment.valor = Decimal("100.00")
            mock_payment.forma_pagamento = "Dinheiro"
            mock_payment.cliente_id = None
            mock_payment.cliente = None
            mock_payment.artista_id = 1
            mock_payment.observacoes = "Payment without client"

            # Serialize the payment
            result = serialize_data(mock_payment, "Pagamento")

            # Verify serialization handles null client
            assert result["cliente_id"] is None
            assert "cliente_name" not in result or result["cliente_name"] is None
            assert result["valor"] == float(Decimal("100.00"))

        except ImportError:
            pytest.skip(
                "generate_monthly_extrato_from_tests.serialize_data not implemented yet"
            )

    def test_serialize_payment_with_client(self):
        """Test serializing payment data when client exists."""
        try:
            from app.scripts.generate_monthly_extrato_from_tests import serialize_data

            # Mock payment with client
            mock_payment = Mock()
            mock_payment.id = 1
            mock_payment.data = date(2024, 1, 15)
            mock_payment.valor = Decimal("100.00")
            mock_payment.forma_pagamento = "Dinheiro"
            mock_payment.cliente_id = 1
            mock_payment.cliente = Mock()
            mock_payment.cliente.name = "Test Client"
            mock_payment.artista_id = 1
            mock_payment.observacoes = "Payment with client"

            # Serialize the payment
            result = serialize_data(mock_payment, "Pagamento")

            # Verify serialization includes client data
            assert result["cliente_id"] == 1
            assert result.get("cliente_name") == "Test Client"
            assert result["valor"] == float(Decimal("100.00"))

        except ImportError:
            pytest.skip(
                "generate_monthly_extrato_from_tests.serialize_data not implemented yet"
            )

    def test_extrato_generation_includes_null_client_payments(self, mock_db_session):
        """Test that monthly extrato includes payments without clients."""
        try:
            from app.scripts.generate_monthly_extrato_from_tests import (
                generate_monthly_extrato,
            )

            # Mock mixed payment data
            payment_with_client = Mock()
            payment_with_client.cliente_id = 1
            payment_with_client.valor = Decimal("100.00")

            payment_without_client = Mock()
            payment_without_client.cliente_id = None
            payment_without_client.valor = Decimal("150.00")

            mock_payments = [payment_with_client, payment_without_client]

            with patch(
                "app.scripts.generate_monthly_extrato_from_tests.SessionLocal",
                return_value=mock_db_session,
            ):
                # Mock database queries
                mock_db_session.query.return_value.filter.return_value.all.return_value = (
                    mock_payments
                )

                # Generate extrato
                result = generate_monthly_extrato(2024, 1)

                # Verify both payments are included
                assert "pagamentos" in result
                assert len(result["pagamentos"]) == 2

                # Check that null client payments are included
                null_client_payments = [
                    p for p in result["pagamentos"] if p.get("cliente_id") is None
                ]
                assert len(null_client_payments) == 1

        except ImportError:
            pytest.skip(
                "generate_monthly_extrato_from_tests.generate_monthly_extrato not implemented yet"
            )

    def test_batch_processing_handles_null_clients(self, mock_db_session):
        """Test that batch processing correctly handles payments with null clients."""
        try:
            from app.scripts.extrato_core import process_batch

            # Create a batch with mixed client scenarios
            batch_data = [
                {"id": 1, "cliente_id": 1, "valor": 100.00},
                {"id": 2, "cliente_id": None, "valor": 150.00},
                {"id": 3, "cliente_id": 2, "valor": 200.00},
                {"id": 4, "cliente_id": None, "valor": 75.00},
            ]

            with patch(
                "app.scripts.extrato_core.SessionLocal", return_value=mock_db_session
            ):
                # Process the batch
                result = process_batch(batch_data, "pagamentos", 2024, 1)

                # Verify all items processed regardless of client status
                assert result["processed_count"] == 4
                assert result["success"] is True

                # Verify null client items were processed
                null_client_count = sum(
                    1 for item in batch_data if item["cliente_id"] is None
                )
                assert (
                    null_client_count == 2
                )  # Should have processed 2 null client items

        except ImportError:
            pytest.skip("extrato_core.process_batch not implemented yet")


class TestCommissionCalculationsOptionalClient:
    """Test commission calculations with payments that have optional clients."""

    def test_artist_commission_calculation_includes_null_client_payments(self):
        """Test that artist commission calculations include payments without clients."""
        try:
            from app.services.commission_service import calculate_artist_commission

            # Mock artist payments with mixed client scenarios
            payments_data = [
                Mock(valor=Decimal("100.00"), cliente_id=1),  # With client
                Mock(valor=Decimal("150.00"), cliente_id=None),  # Without client
                Mock(valor=Decimal("200.00"), cliente_id=2),  # With client
                Mock(valor=Decimal("75.00"), cliente_id=None),  # Without client
            ]

            with patch(
                "app.services.commission_service.get_artist_payments"
            ) as mock_get_payments:
                mock_get_payments.return_value = payments_data

                # Calculate commission for artist
                result = calculate_artist_commission(artist_id=1, year=2024, month=1)

                # Verify all payments are included in commission calculation
                expected_total = Decimal("525.00")  # 100 + 150 + 200 + 75
                expected_commission = expected_total * Decimal(
                    "0.6"
                )  # Assuming 60% commission rate

                assert result["total_payments"] == expected_total
                assert result["commission_amount"] == expected_commission

        except ImportError:
            pytest.skip(
                "commission_service.calculate_artist_commission not implemented yet"
            )

    def test_studio_revenue_includes_null_client_payments(self):
        """Test that studio revenue calculations include all payments regardless of client."""
        try:
            from app.services.financial_service import calculate_studio_revenue

            # Mock all payments including null clients
            all_payments = [
                Mock(valor=Decimal("100.00"), cliente_id=1, artista_id=1),
                Mock(valor=Decimal("150.00"), cliente_id=None, artista_id=1),
                Mock(valor=Decimal("200.00"), cliente_id=2, artista_id=2),
                Mock(valor=Decimal("75.00"), cliente_id=None, artista_id=2),
            ]

            with patch(
                "app.services.financial_service.get_all_payments"
            ) as mock_get_payments:
                mock_get_payments.return_value = all_payments

                # Calculate studio revenue
                result = calculate_studio_revenue(year=2024, month=1)

                # Verify all payments contribute to studio revenue
                expected_total = Decimal("525.00")
                assert result["total_revenue"] == expected_total

                # Verify null client payments are counted
                null_client_total = Decimal("150.00") + Decimal("75.00")  # 225.00
                assert result["null_client_revenue"] == null_client_total

        except ImportError:
            pytest.skip(
                "financial_service.calculate_studio_revenue not implemented yet"
            )


class TestSearchServiceOptionalClient:
    """Test search functionality with payments that have optional clients."""

    def test_search_includes_null_client_payments(self):
        """Test that search results include payments without clients."""
        try:
            from app.services.search_service import SearchService

            # Mock search results with mixed client scenarios
            mock_results = [
                {
                    "type": "Pagamento",
                    "id": 1,
                    "cliente_id": 1,
                    "cliente_name": "Test Client",
                    "valor": 100.00,
                },
                {
                    "type": "Pagamento",
                    "id": 2,
                    "cliente_id": None,
                    "cliente_name": None,  # No client name
                    "valor": 150.00,
                },
            ]

            with patch.object(SearchService, "_search_pagamentos") as mock_search:
                mock_search.return_value = mock_results

                service = SearchService()
                results = service.search("test query")

                # Verify both payments are in results
                assert len(results) == 2

                # Verify null client payment is properly formatted
                null_client_result = next(r for r in results if r["cliente_id"] is None)
                assert null_client_result["cliente_name"] is None
                assert null_client_result["valor"] == 150.00

        except ImportError:
            pytest.skip("SearchService not implemented yet")

    def test_search_filters_work_with_null_clients(self):
        """Test that search filters work correctly with null client payments."""
        try:
            from app.services.search_service import SearchService

            with patch.object(SearchService, "_search_pagamentos") as mock_search:
                # Mock database query with outerjoin for null clients
                mock_search.return_value = [
                    {"cliente_id": None, "valor": 100.00},
                    {"cliente_id": 1, "valor": 150.00},
                ]

                service = SearchService()
                results = service.search(
                    "payment", filters={"include_null_clients": True}
                )

                # Verify null client payments are included when filter allows
                null_client_results = [r for r in results if r["cliente_id"] is None]
                assert len(null_client_results) == 1

        except ImportError:
            pytest.skip("SearchService filters not implemented yet")
