#!/usr/bin/env python3
"""
Test suite for atomic historical records deletion functionality.
"""

import pytest
import logging
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Add backend to path for testing
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.services.extrato_service import delete_historical_records_atomic
from app.db.base import Pagamento, Sessao, Comissao, Gasto


class TestHistoricalRecordsDeletion:
    """Test cases for the delete_historical_records_atomic function."""

    def setup_method(self):
        """Setup test fixtures."""
        self.logger = logging.getLogger(__name__)

        # Create mock database session
        self.mock_db = Mock()

        # Create test month/year
        self.test_mes = 9
        self.test_ano = 2025

    def create_mock_records(self):
        """Create mock records for testing."""
        # Create mock payments
        pagamentos = []
        for i in range(3):
            mock_pagamento = Mock(spec=Pagamento)
            mock_pagamento.id = i + 1
            pagamentos.append(mock_pagamento)

        # Create mock sessions
        sessoes = []
        for i in range(2):
            mock_sessao = Mock(spec=Sessao)
            mock_sessao.id = i + 1
            sessoes.append(mock_sessao)

        # Create mock commissions
        comissoes = []
        for i in range(4):
            mock_comissao = Mock(spec=Comissao)
            mock_comissao.id = i + 1
            comissoes.append(mock_comissao)

        # Create mock expenses
        gastos = []
        for i in range(2):
            mock_gasto = Mock(spec=Gasto)
            mock_gasto.id = i + 1
            gastos.append(mock_gasto)

        return pagamentos, sessoes, comissoes, gastos

    @patch("app.services.extrato_service.logger")
    def test_successful_deletion_all_record_types(self, mock_logger):
        """Test successful deletion of all record types."""
        # Arrange
        pagamentos, sessoes, comissoes, gastos = self.create_mock_records()

        # Act
        result = delete_historical_records_atomic(
            db_session=self.mock_db,
            pagamentos=pagamentos,
            sessoes=sessoes,
            comissoes=comissoes,
            gastos=gastos,
            mes=self.test_mes,
            ano=self.test_ano,
        )

        # Assert
        assert result is True

        # Verify deletion calls in correct order
        # 1. Commissions deleted first
        assert self.mock_db.delete.call_count == 11  # 3 + 2 + 4 + 2 = 11

        # Verify logging calls
        mock_logger.info.assert_any_call(
            "Starting deletion of historical records for 09/2025"
        )
        mock_logger.info.assert_any_call(
            "Deleting 11 total records in dependency order"
        )
        mock_logger.info.assert_any_call("✓ Deleted 4 commissions")
        mock_logger.info.assert_any_call(
            "Breaking circular references between sessions and payments"
        )
        mock_logger.info.assert_any_call(
            "✓ Broke circular references between sessions and payments"
        )
        mock_logger.info.assert_any_call("✓ Deleted 3 payments")
        mock_logger.info.assert_any_call("✓ Deleted 2 sessions")
        mock_logger.info.assert_any_call("✓ Deleted 2 expenses")
        mock_logger.info.assert_any_call(
            "✓ Successfully deleted all 11 historical records for 09/2025"
        )

    @patch("app.services.extrato_service.logger")
    def test_successful_deletion_empty_lists(self, mock_logger):
        """Test successful deletion when no records exist."""
        # Arrange
        pagamentos, sessoes, comissoes, gastos = [], [], [], []

        # Act
        result = delete_historical_records_atomic(
            db_session=self.mock_db,
            pagamentos=pagamentos,
            sessoes=sessoes,
            comissoes=comissoes,
            gastos=gastos,
            mes=self.test_mes,
            ano=self.test_ano,
        )

        # Assert
        assert result is True

        # Verify no deletion calls
        self.mock_db.delete.assert_not_called()

        # Verify logging
        mock_logger.info.assert_any_call("No records to delete")

    @patch("app.services.extrato_service.logger")
    def test_deletion_failure_commission_error(self, mock_logger):
        """Test deletion failure when commission deletion fails."""
        # Arrange
        pagamentos, sessoes, comissoes, gastos = self.create_mock_records()

        # Make commission deletion fail
        self.mock_db.delete.side_effect = [
            Exception("Commission deletion failed"),
            None,
            None,
            None,
        ]

        # Act & Assert
        with pytest.raises(Exception, match="Commission deletion failed"):
            delete_historical_records_atomic(
                db_session=self.mock_db,
                pagamentos=pagamentos,
                sessoes=sessoes,
                comissoes=comissoes,
                gastos=gastos,
                mes=self.test_mes,
                ano=self.test_ano,
            )

        # Verify error logging
        mock_logger.error.assert_any_call(
            "Failed to delete commission 1: Commission deletion failed"
        )

    @patch("app.services.extrato_service.logger")
    def test_deletion_failure_payment_error(self, mock_logger):
        """Test deletion failure when payment deletion fails."""
        # Arrange
        pagamentos, sessoes, comissoes, gastos = self.create_mock_records()

        # Make payment deletion fail (after commissions succeed)
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 4:  # After commissions (4) and circular reference breaking
                raise Exception("Payment deletion failed")
            return None

        self.mock_db.delete.side_effect = side_effect

        # Act & Assert
        with pytest.raises(Exception, match="Payment deletion failed"):
            delete_historical_records_atomic(
                db_session=self.mock_db,
                pagamentos=pagamentos,
                sessoes=sessoes,
                comissoes=comissoes,
                gastos=gastos,
                mes=self.test_mes,
                ano=self.test_ano,
            )

        # Verify error logging
        mock_logger.error.assert_any_call(
            "Failed to delete payment 1: Payment deletion failed"
        )

    @patch("app.services.extrato_service.logger")
    def test_circular_reference_breaking(self, mock_logger):
        """Test that circular references are properly broken."""
        # Arrange
        pagamentos, sessoes, comissoes, gastos = self.create_mock_records()

        # Act
        result = delete_historical_records_atomic(
            db_session=self.mock_db,
            pagamentos=pagamentos,
            sessoes=sessoes,
            comissoes=comissoes,
            gastos=gastos,
            mes=self.test_mes,
            ano=self.test_ano,
        )

        # Assert
        assert result is True

        # Verify setattr was called for each session
        for sessao in sessoes:
            sessao.__setattr__.assert_called_with("payment_id", None)

        # Verify logging
        mock_logger.info.assert_any_call(
            "Breaking circular references between sessions and payments"
        )
        mock_logger.info.assert_any_call(
            "✓ Broke circular references between sessions and payments"
        )

    @patch("app.services.extrato_service.logger")
    def test_deletion_count_verification_success(self, mock_logger):
        """Test that deletion count verification works correctly."""
        # Arrange
        pagamentos, sessoes, comissoes, gastos = self.create_mock_records()

        # Act
        result = delete_historical_records_atomic(
            db_session=self.mock_db,
            pagamentos=pagamentos,
            sessoes=sessoes,
            comissoes=comissoes,
            gastos=gastos,
            mes=self.test_mes,
            ano=self.test_ano,
        )

        # Assert
        assert result is True

        # Verify success logging includes correct count
        mock_logger.info.assert_any_call(
            "✓ Successfully deleted all 11 historical records for 09/2025"
        )

    @patch("app.services.extrato_service.logger")
    def test_deletion_count_verification_failure(self, mock_logger):
        """Test that deletion count verification detects mismatches."""
        # Arrange
        pagamentos, sessoes, comissoes, gastos = self.create_mock_records()

        # Simulate deletion count mismatch by making delete calls fail silently
        # (This would happen if some records weren't actually deleted)
        original_delete = self.mock_db.delete
        delete_count = 0

        def counting_delete(*args, **kwargs):
            nonlocal delete_count
            delete_count += 1
            # Don't actually call delete to simulate silent failure
            return None

        self.mock_db.delete = counting_delete

        # Act & Assert
        with pytest.raises(ValueError, match="Deletion count mismatch"):
            delete_historical_records_atomic(
                db_session=self.mock_db,
                pagamentos=pagamentos,
                sessoes=sessoes,
                comissoes=comissoes,
                gastos=gastos,
                mes=self.test_mes,
                ano=self.test_ano,
            )

        # Verify error logging
        mock_logger.error.assert_any_call("Deletion count mismatch: expected 11, got 0")

    @patch("app.services.extrato_service.logger")
    def test_partial_success_logging(self, mock_logger):
        """Test that partial success is properly logged."""
        # Arrange
        pagamentos, sessoes, comissoes, gastos = self.create_mock_records()

        # Act
        result = delete_historical_records_atomic(
            db_session=self.mock_db,
            pagamentos=pagamentos,
            sessoes=sessoes,
            comissoes=comissoes,
            gastos=gastos,
            mes=self.test_mes,
            ano=self.test_ano,
        )

        # Assert
        assert result is True

        # Verify partial success logging
        mock_logger.info.assert_any_call("✓ Deleted 4 commissions")
        mock_logger.info.assert_any_call("✓ Deleted 3 payments")
        mock_logger.info.assert_any_call("✓ Deleted 2 sessions")
        mock_logger.info.assert_any_call("✓ Deleted 2 expenses")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
