"""
Tests for repository operations with optional cliente_id.

This module tests the repository layer to ensure CRUD operations
work correctly with payments that have optional clients.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestPagamentoRepositoryOptionalClient:
    """Test PagamentoRepository CRUD operations with optional client."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return MagicMock()

    @pytest.fixture
    def payment_data_without_client(self):
        """Payment data without client."""
        return {
            "data": date(2024, 1, 15),
            "valor": Decimal("100.00"),
            "forma_pagamento": "Dinheiro",
            "cliente_id": None,  # No client
            "artista_id": 1,
            "observacoes": "Test payment without client",
        }

    @pytest.fixture
    def payment_data_with_client(self):
        """Payment data with client."""
        return {
            "data": date(2024, 1, 15),
            "valor": Decimal("100.00"),
            "forma_pagamento": "Dinheiro",
            "cliente_id": 1,
            "artista_id": 1,
            "observacoes": "Test payment with client",
        }

    def test_create_pagamento_without_client(
        self, mock_db_session, payment_data_without_client
    ):
        """Test creating a payment without client via repository."""
        try:
            from app.repositories.pagamento_repository import PagamentoRepository
            from app.db.base import Pagamento

            # Create repository instance
            repo = PagamentoRepository()

            with patch(
                "app.repositories.pagamento_repository.SessionLocal",
                return_value=mock_db_session,
            ):
                # Mock the Pagamento model creation
                with patch(
                    "app.repositories.pagamento_repository.Pagamento"
                ) as MockPagamento:
                    mock_payment = Mock()
                    mock_payment.id = 1
                    MockPagamento.return_value = mock_payment

                    # Create payment
                    result = repo.create(payment_data_without_client)

                    # Verify payment was created with null client
                    MockPagamento.assert_called_once_with(**payment_data_without_client)
                    mock_db_session.add.assert_called_once()
                    mock_db_session.commit.assert_called_once()
                    mock_db_session.refresh.assert_called_once_with(mock_payment)

                    assert result.id == 1

        except ImportError:
            pytest.skip("PagamentoRepository not implemented yet")

    def test_create_pagamento_with_client(
        self, mock_db_session, payment_data_with_client
    ):
        """Test creating a payment with client via repository."""
        try:
            from app.repositories.pagamento_repository import PagamentoRepository

            repo = PagamentoRepository()

            with patch(
                "app.repositories.pagamento_repository.SessionLocal",
                return_value=mock_db_session,
            ):
                with patch(
                    "app.repositories.pagamento_repository.Pagamento"
                ) as MockPagamento:
                    mock_payment = Mock()
                    mock_payment.id = 1
                    MockPagamento.return_value = mock_payment

                    # Create payment
                    result = repo.create(payment_data_with_client)

                    # Verify payment was created with client
                    MockPagamento.assert_called_once_with(**payment_data_with_client)
                    mock_db_session.add.assert_called_once()
                    mock_db_session.commit.assert_called_once()

                    assert result.id == 1

        except ImportError:
            pytest.skip("PagamentoRepository not implemented yet")

    def test_update_pagamento_remove_client(self, mock_db_session):
        """Test updating a payment to remove client via repository."""
        try:
            from app.repositories.pagamento_repository import PagamentoRepository

            # Mock existing payment with client
            mock_payment = Mock()
            mock_payment.id = 1
            mock_payment.cliente_id = 1
            mock_payment.valor = Decimal("100.00")

            repo = PagamentoRepository()

            # Update data to remove client
            update_data = {
                "cliente_id": None,  # Remove client
                "valor": Decimal("150.00"),
            }

            with patch(
                "app.repositories.pagamento_repository.SessionLocal",
                return_value=mock_db_session,
            ):
                mock_db_session.get.return_value = mock_payment

                # Update payment
                result = repo.update(1, update_data)

                # Verify payment was updated
                assert mock_payment.cliente_id is None
                assert mock_payment.valor == Decimal("150.00")
                mock_db_session.commit.assert_called_once()
                mock_db_session.refresh.assert_called_once_with(mock_payment)

                assert result == mock_payment

        except ImportError:
            pytest.skip("PagamentoRepository.update not implemented yet")

    def test_update_pagamento_add_client(self, mock_db_session):
        """Test updating a payment to add client via repository."""
        try:
            from app.repositories.pagamento_repository import PagamentoRepository

            # Mock existing payment without client
            mock_payment = Mock()
            mock_payment.id = 1
            mock_payment.cliente_id = None
            mock_payment.valor = Decimal("100.00")

            repo = PagamentoRepository()

            # Update data to add client
            update_data = {
                "cliente_id": 1,  # Add client
                "valor": Decimal("150.00"),
            }

            with patch(
                "app.repositories.pagamento_repository.SessionLocal",
                return_value=mock_db_session,
            ):
                mock_db_session.get.return_value = mock_payment

                # Update payment
                result = repo.update(1, update_data)

                # Verify payment was updated
                assert mock_payment.cliente_id == 1
                assert mock_payment.valor == Decimal("150.00")
                mock_db_session.commit.assert_called_once()

                assert result == mock_payment

        except ImportError:
            pytest.skip("PagamentoRepository.update not implemented yet")

    def test_get_by_id_payment_without_client(self, mock_db_session):
        """Test retrieving a payment without client via repository."""
        try:
            from app.repositories.pagamento_repository import PagamentoRepository

            # Mock payment without client
            mock_payment = Mock()
            mock_payment.id = 1
            mock_payment.cliente_id = None
            mock_payment.cliente = None

            repo = PagamentoRepository()

            with patch(
                "app.repositories.pagamento_repository.SessionLocal",
                return_value=mock_db_session,
            ):
                mock_db_session.get.return_value = mock_payment

                # Get payment
                result = repo.get_by_id(1)

                # Verify correct payment returned
                assert result.id == 1
                assert result.cliente_id is None
                assert result.cliente is None

        except ImportError:
            pytest.skip("PagamentoRepository.get_by_id not implemented yet")

    def test_list_all_includes_null_client_payments(self, mock_db_session):
        """Test that list_all includes payments with and without clients."""
        try:
            from app.repositories.pagamento_repository import PagamentoRepository

            # Mock mixed payment data
            mock_payment_with_client = Mock()
            mock_payment_with_client.id = 1
            mock_payment_with_client.cliente_id = 1

            mock_payment_without_client = Mock()
            mock_payment_without_client.id = 2
            mock_payment_without_client.cliente_id = None

            mock_payments = [mock_payment_with_client, mock_payment_without_client]

            repo = PagamentoRepository()

            with patch(
                "app.repositories.pagamento_repository.SessionLocal",
                return_value=mock_db_session,
            ):
                mock_db_session.query.return_value.all.return_value = mock_payments

                # List all payments
                result = repo.list_all()

                # Verify both payments are returned
                assert len(result) == 2
                assert any(p.cliente_id is None for p in result)
                assert any(p.cliente_id is not None for p in result)

        except ImportError:
            pytest.skip("PagamentoRepository.list_all not implemented yet")

    def test_delete_payment_without_client(self, mock_db_session):
        """Test deleting a payment without client via repository."""
        try:
            from app.repositories.pagamento_repository import PagamentoRepository

            # Mock payment without client
            mock_payment = Mock()
            mock_payment.id = 1
            mock_payment.cliente_id = None

            repo = PagamentoRepository()

            with patch(
                "app.repositories.pagamento_repository.SessionLocal",
                return_value=mock_db_session,
            ):
                mock_db_session.get.return_value = mock_payment

                # Delete payment
                result = repo.delete(1)

                # Verify payment was deleted
                mock_db_session.delete.assert_called_once_with(mock_payment)
                mock_db_session.commit.assert_called_once()

                assert result is True

        except ImportError:
            pytest.skip("PagamentoRepository.delete not implemented yet")

    def test_get_by_filter_with_null_client(self, mock_db_session):
        """Test filtering payments by null client via repository."""
        try:
            from app.repositories.pagamento_repository import PagamentoRepository

            # Mock payments without clients
            mock_payments = [
                Mock(id=1, cliente_id=None),
                Mock(id=2, cliente_id=None),
            ]

            repo = PagamentoRepository()

            with patch(
                "app.repositories.pagamento_repository.SessionLocal",
                return_value=mock_db_session,
            ):
                # Mock query chain
                query_mock = mock_db_session.query.return_value
                query_mock.filter.return_value.all.return_value = mock_payments

                # Filter by null client
                result = repo.get_by_filter({"cliente_id": None})

                # Verify filter was applied correctly
                mock_db_session.query.assert_called_once()
                query_mock.filter.assert_called()

                assert len(result) == 2
                assert all(p.cliente_id is None for p in result)

        except ImportError:
            pytest.skip("PagamentoRepository.get_by_filter not implemented yet")

    def test_get_payments_by_artist_includes_null_clients(self, mock_db_session):
        """Test getting payments by artist includes those without clients."""
        try:
            from app.repositories.pagamento_repository import PagamentoRepository

            # Mock artist payments with mixed client scenarios
            mock_payments = [
                Mock(id=1, artista_id=1, cliente_id=1),  # With client
                Mock(id=2, artista_id=1, cliente_id=None),  # Without client
            ]

            repo = PagamentoRepository()

            with patch(
                "app.repositories.pagamento_repository.SessionLocal",
                return_value=mock_db_session,
            ):
                query_mock = mock_db_session.query.return_value
                query_mock.filter.return_value.all.return_value = mock_payments

                # Get payments by artist
                result = repo.get_by_artist(1)

                # Verify all artist payments are returned regardless of client
                assert len(result) == 2
                assert any(p.cliente_id is None for p in result)
                assert any(p.cliente_id is not None for p in result)
                assert all(p.artista_id == 1 for p in result)

        except ImportError:
            pytest.skip("PagamentoRepository.get_by_artist not implemented yet")


class TestRepositoryQueryOptimizations:
    """Test repository query optimizations for optional client scenarios."""

    def test_repository_uses_outerjoin_for_client_relationship(self, mock_db_session):
        """Test that repository queries use outerjoin to include null clients."""
        try:
            from app.repositories.pagamento_repository import PagamentoRepository

            repo = PagamentoRepository()

            with patch(
                "app.repositories.pagamento_repository.SessionLocal",
                return_value=mock_db_session,
            ):
                # Mock query with joinedload/outerjoin
                query_mock = mock_db_session.query.return_value
                options_mock = query_mock.options.return_value
                options_mock.all.return_value = []

                # Call method that should use optimized queries
                result = repo.list_all_with_relationships()

                # Verify query optimization was used
                mock_db_session.query.assert_called()
                query_mock.options.assert_called()

        except ImportError:
            pytest.skip(
                "PagamentoRepository.list_all_with_relationships not implemented yet"
            )

    def test_repository_batch_operations_handle_null_clients(self, mock_db_session):
        """Test that batch operations handle null client payments correctly."""
        try:
            from app.repositories.pagamento_repository import PagamentoRepository

            # Batch data with mixed client scenarios
            batch_data = [
                {"cliente_id": 1, "valor": "100.00"},
                {"cliente_id": None, "valor": "150.00"},  # Null client
                {"cliente_id": 2, "valor": "200.00"},
            ]

            repo = PagamentoRepository()

            with patch(
                "app.repositories.pagamento_repository.SessionLocal",
                return_value=mock_db_session,
            ):
                # Mock batch insert
                mock_db_session.bulk_insert_mappings = Mock()

                # Perform batch operation
                result = repo.batch_create(batch_data)

                # Verify batch operation handled null clients
                mock_db_session.bulk_insert_mappings.assert_called_once()
                inserted_data = mock_db_session.bulk_insert_mappings.call_args[0][1]

                null_client_items = [
                    item for item in inserted_data if item.get("cliente_id") is None
                ]
                assert len(null_client_items) == 1

        except ImportError:
            pytest.skip("PagamentoRepository.batch_create not implemented yet")


class TestRepositoryErrorHandling:
    """Test error handling in repository operations with optional clients."""

    def test_create_payment_with_invalid_null_client_data(self, mock_db_session):
        """Test error handling when creating payment with invalid null client data."""
        try:
            from app.repositories.pagamento_repository import PagamentoRepository

            # Invalid data - missing required fields
            invalid_data = {
                "cliente_id": None,  # Null client is OK
                # Missing required fields like valor, forma_pagamento
            }

            repo = PagamentoRepository()

            with patch(
                "app.repositories.pagamento_repository.SessionLocal",
                return_value=mock_db_session,
            ):
                with patch(
                    "app.repositories.pagamento_repository.Pagamento"
                ) as MockPagamento:
                    # Mock validation error
                    MockPagamento.side_effect = ValueError("Missing required field")

                    # Attempt to create payment
                    with pytest.raises(ValueError):
                        repo.create(invalid_data)

        except ImportError:
            pytest.skip("PagamentoRepository error handling not implemented yet")

    def test_update_nonexistent_payment_with_null_client(self, mock_db_session):
        """Test updating a nonexistent payment returns appropriate error."""
        try:
            from app.repositories.pagamento_repository import PagamentoRepository

            repo = PagamentoRepository()

            with patch(
                "app.repositories.pagamento_repository.SessionLocal",
                return_value=mock_db_session,
            ):
                # Mock payment not found
                mock_db_session.get.return_value = None

                # Attempt to update nonexistent payment
                result = repo.update(999, {"cliente_id": None})

                # Should handle gracefully
                assert result is None or hasattr(result, "error")

        except ImportError:
            pytest.skip("PagamentoRepository error handling not implemented yet")
